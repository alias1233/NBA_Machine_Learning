"""
A finished whole-league feature build, written once by a job and read by every prediction.

Building the league's features is the expensive half of a prediction and comes out the same for every
request, because every rolling column leaves its own row out and so a game not yet played cannot
change a row in front of it. So a job builds it and the service reads what that produced, rather than
each request building the league for itself.

A build holds one entry per subject: the games they have played, already reduced to the numbers a
model reads. It holds nothing about a game that has not been played, which is assembled per request
from the state these games leave behind.

Publishing is atomic. The job writes a new version under a working name, moves it into place whole,
and then rewrites the pointer naming it. A reader resolves the newest complete version every time it
is asked, so a build published while the service is running is picked up without a restart, and the
previous version is kept so a failed job never takes the service down.
"""

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
"""How a version directory is named. Sorting these names sorts the builds by age."""

KEPT_VERSIONS = 2
"""
How many builds are left on disk.

Two, so that the one being served survives the next job whether it succeeds or fails.
"""

@dataclass(frozen=True)
class SubjectSequences():
    """One subject's past games: when each was played, what it holds, and who it was against."""

    game_dates: np.ndarray
    """Shaped (games,), oldest first."""

    sequence_values: np.ndarray
    """Shaped (games, columns)."""

    opponent_team_ids: np.ndarray
    """Shaped (games,)."""

    @property
    def game_count(self) -> int:
        return len(self.game_dates)

    def before(self, day: date) -> "SubjectSequences":
        """
        Only the games played before the given day, which is all a prediction about it may read.

        A game played on that day counts as after it, so a prediction never reads a game it is being
        asked to predict alongside.
        """

        end = int(np.searchsorted(self.game_dates, np.datetime64(day, 'ns'), side='left'))

        return SubjectSequences(
            self.game_dates[:end],
            self.sequence_values[:end],
            self.opponent_team_ids[:end]
        )

    def with_columns(self, positions: np.ndarray) -> "SubjectSequences":
        """The same games holding only the columns at the given positions, in that order."""

        return replace(self, sequence_values=self.sequence_values[:, positions])

def sequences_in(history: GameHistory) -> SubjectSequences:
    """
    The half of a finished history a prediction reads.

    Everything left behind is either what a finished game is fit against or what is read off the game
    being predicted, and the game being predicted is not in a build at all.
    """

    return SubjectSequences(
        history.game_dates,
        history.sequence_values,
        history.opponent_team_ids
    )

def no_games(columns: int) -> SubjectSequences:
    """What a subject a build found no games at all for reads as."""

    return SubjectSequences(
        np.empty(0, dtype='datetime64[ns]'),
        np.empty((0, columns), dtype=np.float32),
        np.empty(0, dtype=np.int64)
    )

@dataclass(frozen=True)
class FeatureBuild():
    """Every subject's past games as one build produced them, plus what that build read."""

    version: str
    """Names the directory this was written to, and is what tells two builds apart."""

    built_at: datetime
    window_start_date: date | None
    """The oldest game the build read, or None where it read everything stored."""

    sequence_columns: tuple[str, ...]
    """What each column of every subject's games holds, in that order."""

    subjects: Mapping[int, SubjectSequences]
    """Each subject's games, keyed by their id. A subject the build found none for is simply absent."""

    @property
    def game_count(self) -> int:
        return sum(subject.game_count for subject in self.subjects.values())

    def column_positions(self, wanted: Sequence[str]) -> np.ndarray:
        """
        Where each of the named columns sits in this build, so a model can read its own columns out
        of a build made for every model at once.

        Raises:
            ValueError naming the columns this build does not hold, which is what a build made before
            a column was added looks like. Rebuilding is the fix.
        """

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
    """Keeps the half of a finished build a prediction reads. See sequences_in."""

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
        """Every subject's games in one array, which the offsets beside it cut back apart."""

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
    """
    Writes a build and makes it the one every reader resolves.

    The version is written under a working name and moved into place whole, so a reader never meets a
    half written one, and the pointer is rewritten last. Older versions past KEPT_VERSIONS then go.

    Returns:
        The directory the build was written to.
    """

    directory = paths.feature_build_directory(name)
    working = directory / (WORKING_PREFIX + build.version)
    version = directory / build.version

    shutil.rmtree(working, ignore_errors=True)
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

# READING: #
def _complete_versions(name: str) -> list[Path]:
    """
    Every finished build on disk, oldest first. A version is named after when it was built, so
    sorting the names sorts them by age.

    A directory still under its working name is left out however finished it looks, because a job
    that died between writing it and moving it into place is exactly what that name means.
    """

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
    """
    Which build a reader should use: the one the pointer names, or the newest complete one.

    The pointer is what the last successful job left behind. Falling back to the newest complete
    version covers a pointer that was never written or names a build that has since been removed.
    """

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
    """One build off disk. Every subject's games are views into one array rather than copies."""

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

def current(name: str) -> FeatureBuild | None:
    """
    The build every prediction reads, or None while none has been published.

    Which version is newest is resolved on every call, which is a small file read, so a build
    published while the service is running is picked up without a restart. The build itself is read
    once and shared by every request after that.
    """

    version = _newest_version(name)

    if version is None:
        return None

    with _reading:
        held = _held.get(name)

        if held is None or held.version != version.name:
            held = _read(version)
            _held[name] = held

        return held
