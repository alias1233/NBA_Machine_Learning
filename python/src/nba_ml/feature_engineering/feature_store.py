"""Saves and loads feature builds, the precomputed past-game features used for predictions."""

import json
import os
import shutil
import threading
from dataclasses import dataclass, replace
from datetime import date, datetime
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

from nba_ml import paths, season
from nba_ml.feature_engineering.samples import GameHistory

SEQUENCES_FILE = "sequences.npz"
DESCRIPTION_FILE = "build.json"
POINTER_FILE = "current"
WORKING_PREFIX = "incomplete-"

VERSION_FORMAT = "%Y%m%d-%H%M%S"
"""Timestamp format used for version directory names. Sorting by name sorts by date."""

KEPT_VERSIONS = 2
"""Number of builds kept on disk."""

@dataclass(frozen=True)
class SubjectSequences():
    """The past games of one subject (a player or team): dates, feature values and opponents."""

    game_dates: np.ndarray
    """Shape: (games,). Sorted oldest first."""

    sequence_values: np.ndarray
    """Shape: (games, columns)."""

    opponent_team_ids: np.ndarray
    """Shape: (games,)."""

    @property
    def game_count(self) -> int:
        return len(self.game_dates)

    def before(self, day: date) -> "SubjectSequences":
        """Returns only the games played before the given date."""

        end = int(np.searchsorted(self.game_dates, np.datetime64(day, 'ns'), side='left'))

        return SubjectSequences(
            self.game_dates[:end],
            self.sequence_values[:end],
            self.opponent_team_ids[:end]
        )

    def with_columns(self, positions: np.ndarray) -> "SubjectSequences":
        """Returns the same games with only the columns at the given positions."""

        return replace(self, sequence_values=self.sequence_values[:, positions])

def sequences_in(history: GameHistory) -> SubjectSequences:
    """Extracts the dates, sequence values and opponents from a GameHistory."""

    return SubjectSequences(
        history.game_dates,
        history.sequence_values,
        history.opponent_team_ids
    )

def no_games(columns: int) -> SubjectSequences:
    """Returns an empty SubjectSequences with the given number of columns."""

    return SubjectSequences(
        np.empty(0, dtype='datetime64[ns]'),
        np.empty((0, columns), dtype=np.float32),
        np.empty(0, dtype=np.int64)
    )

@dataclass(frozen=True)
class FeatureBuild():
    """A feature build: the past games of every subject, plus metadata."""

    version: str
    """Name of the directory the build is saved in."""

    built_at: datetime
    window_start_date: date | None
    """Earliest game date included in the build. None if it used every stored game."""

    sequence_columns: tuple[str, ...]
    """Names of the columns in each subject's sequence_values, in order."""

    subjects: Mapping[int, SubjectSequences]
    """Each subject's games, keyed by subject ID."""

    @property
    def game_count(self) -> int:
        return sum(subject.game_count for subject in self.subjects.values())

    def column_positions(self, wanted: Sequence[str]) -> np.ndarray:
        """Returns the index of each given column in this build."""

        held = {column: position for position, column in enumerate(self.sequence_columns)}
        missing = [column for column in wanted if column not in held]

        if missing:
            raise ValueError(
                f"The {self.version} feature build does not hold {', '.join(missing)}. "
                "It was made before the feature set moved, so rebuild it."
            )

        return np.array([held[column] for column in wanted], dtype=np.int64)

def from_histories(
    histories: Mapping[int, GameHistory],
    sequence_columns: Sequence[str],
    window_start_date: date | None
    ) -> FeatureBuild:
    """Creates a FeatureBuild from the given histories, keeping only what predictions need."""

    built_at = datetime.now()

    return FeatureBuild(
        version=built_at.strftime(VERSION_FORMAT),
        built_at=built_at,
        window_start_date=window_start_date,
        sequence_columns=tuple(sequence_columns),
        subjects={
            subject_id: sequences_in(history)
            for subject_id, history in histories.items()
        }
    )

# WRITING: #
def _description(build: FeatureBuild) -> dict:
    return {
        "built_at": build.built_at.isoformat(timespec="seconds"),
        "window_start_date": None if build.window_start_date is None else season.to_date_string(build.window_start_date),
        "subjects": len(build.subjects),
        "games": build.game_count,
        "sequence_columns": list(build.sequence_columns)
    }

def _write(directory: Path, build: FeatureBuild):
    subjects = list(build.subjects.values())
    counts = np.array([subject.game_count for subject in subjects], dtype=np.int64)

    def joined(arrays: list[np.ndarray], empty_shape: tuple[int, ...]) -> np.ndarray:
        """Concatenates every subject's array into one. The saved offsets are used to split it again."""

        return np.concatenate(arrays) if arrays else np.empty(empty_shape, dtype=np.float32)

    directory.mkdir(parents=True)
    np.savez(
        directory / SEQUENCES_FILE,
        subject_ids=np.array(list(build.subjects), dtype=np.int64),
        offsets=np.concatenate(([0], np.cumsum(counts))),
        game_dates=joined([subject.game_dates for subject in subjects], (0,)),
        sequence_values=joined(
            [subject.sequence_values for subject in subjects],
            (0, len(build.sequence_columns))
        ),
        opponent_team_ids=joined([subject.opponent_team_ids for subject in subjects], (0,))
    )
    (directory / DESCRIPTION_FILE).write_text(
        json.dumps(_description(build), indent=2), encoding="utf-8"
    )

def publish(name: str, build: FeatureBuild) -> Path:
    """Writes the build to a temporary directory, renames it, then updates the pointer file."""

    directory = paths.feature_build_directory(name)
    working = directory / (WORKING_PREFIX + build.version)
    version = directory / build.version

    _remove_working_versions(name)
    _write(working, build)

    shutil.rmtree(version, ignore_errors=True)
    os.replace(working, version)

    pointer = directory / POINTER_FILE
    written_pointer = directory / (POINTER_FILE + ".new")
    written_pointer.write_text(build.version, encoding="utf-8")
    os.replace(written_pointer, pointer)

    _remove_old_versions(name)

    return version

def _remove_old_versions(name: str):
    for version in _complete_versions(name)[:-KEPT_VERSIONS]:
        shutil.rmtree(version, ignore_errors=True)

def _remove_working_versions(name: str):
    """Deletes temporary directories left behind by failed builds."""

    directory = paths.feature_build_directory(name)

    if not directory.is_dir():
        return

    for working in directory.glob(WORKING_PREFIX + "*"):
        shutil.rmtree(working, ignore_errors=True)

# READING: #
def _complete_versions(name: str) -> list[Path]:
    """Returns every complete build on disk, oldest first."""

    directory = paths.feature_build_directory(name)

    if not directory.is_dir():
        return []

    return sorted(
        (
            version for version in directory.iterdir()
            if not version.name.startswith(WORKING_PREFIX)
            and (version / SEQUENCES_FILE).is_file()
            and (version / DESCRIPTION_FILE).is_file()
        ),
        key=lambda version: version.name
    )

def _newest_version(name: str) -> Path | None:
    """Returns the build named in the pointer file, or the newest complete one if it is missing."""

    versions = _complete_versions(name)

    if not versions:
        return None

    pointer = paths.feature_build_directory(name) / POINTER_FILE
    pointed_at = pointer.read_text(encoding="utf-8").strip() if pointer.is_file() else ""

    return next(
        (version for version in versions if version.name == pointed_at),
        versions[-1]
    )

def _read(version: Path) -> FeatureBuild:
    """Loads a build from disk."""

    described = json.loads((version / DESCRIPTION_FILE).read_text(encoding="utf-8"))
    window_start_date = described["window_start_date"]

    with np.load(version / SEQUENCES_FILE) as values:
        subject_ids = values["subject_ids"]
        offsets = values["offsets"]
        game_dates = values["game_dates"]
        sequence_values = values["sequence_values"]
        opponent_team_ids = values["opponent_team_ids"]

    return FeatureBuild(
        version=version.name,
        built_at=datetime.fromisoformat(described["built_at"]),
        window_start_date=None if window_start_date is None else season.from_date_string(window_start_date).date(),
        sequence_columns=tuple(described["sequence_columns"]),
        subjects={
            int(subject_id): SubjectSequences(
                game_dates[start:end],
                sequence_values[start:end],
                opponent_team_ids[start:end]
            )
            for subject_id, start, end in zip(subject_ids, offsets[:-1], offsets[1:])
        }
    )

_held: dict[str, FeatureBuild] = {}
_reading = threading.Lock()

def is_published(name: str) -> bool:
    """Returns True if a build exists, without loading it."""

    return _newest_version(name) is not None

def current(name: str) -> FeatureBuild | None:
    """Returns the current build, or None if none has been published. The loaded build is cached."""

    version = _newest_version(name)

    if version is None:
        return None

    with _reading:
        held = _held.get(name)

        if held is None or held.version != version.name:
            held = _read(version)
            _held[name] = held

        return held
