"""Package the small, verified data release a prediction server needs."""

import argparse
import json
import os
import sqlite3
import tarfile
import tempfile
from contextlib import closing
from datetime import date
from pathlib import Path, PurePosixPath

from dateutil.relativedelta import relativedelta

from nba_ml import paths, season
from nba_ml.data_collection.source_identity import MARKER as SOURCE_MARKER
from nba_ml.models.player_stats import features
from nba_ml.stores import player_games, players, schedule, team_games, teams

DATABASES = "databases"
MODELS = "models"
MANIFEST = "serving-data.json"
FORMAT_VERSION = 1

DATABASE_TABLES = {
    player_games.FILEPATH.name: (player_games.NAME, player_games.GAME_DATE.category_name),
    team_games.FILEPATH.name: (team_games.NAME, team_games.GAME_DATE.category_name),
    players.FILEPATH.name: (players.NAME, None),
    teams.FILEPATH.name: (teams.NAME, None),
    schedule.FILEPATH.name: (schedule.NAME, None)
}

PLAYER_ID_COLUMNS = {
    player_games.FILEPATH.name: player_games.PLAYER_ID.category_name,
    players.FILEPATH.name: players.PLAYER_ID.category_name
}
"""What each table calls the player a row belongs to. The two tables do not agree on the name."""


def _integrity_check(database_file: Path):
    with closing(sqlite3.connect(database_file)) as database:
        result = database.execute("PRAGMA integrity_check").fetchone()
    if result != ("ok",):
        raise RuntimeError(f"{database_file.name} failed SQLite integrity_check: {result}.")


def _copy_database(source_file: Path, target_file: Path, cutoff: date) -> int:
    table, date_column = DATABASE_TABLES[source_file.name]
    with (
        closing(sqlite3.connect(source_file)) as source,
        closing(sqlite3.connect(target_file)) as target
    ):
        source.backup(target)
        if date_column is not None:
            target.execute(f"DELETE FROM {table} WHERE {date_column} < ?", (season.to_date_string(cutoff),))
            target.commit()
            target.execute("VACUUM")
        row_count = target.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    _integrity_check(target_file)
    return int(row_count)


def _player_ids(database_file: Path) -> set[int]:
    table, _ = DATABASE_TABLES[database_file.name]
    with closing(sqlite3.connect(database_file)) as database:
        rows = database.execute(
            f"SELECT DISTINCT {PLAYER_ID_COLUMNS[database_file.name]} FROM {table}"
        ).fetchall()

    return {int(row[0]) for row in rows}


def _narrow_to_players(database_file: Path, player_ids: set[int]) -> int:
    """
    Drops the players who have no game inside the packaged window.

    The archive a developer trains on reaches back decades further than the window a server serves,
    so without this a visitor could search up a player the server holds not one game of.
    """

    table, _ = DATABASE_TABLES[database_file.name]
    kept = ",".join(str(int(player_id)) for player_id in player_ids) or "NULL"
    with closing(sqlite3.connect(database_file)) as database:
        database.execute(f"DELETE FROM {table} WHERE {players.PLAYER_ID.category_name} NOT IN ({kept})")
        database.commit()
        database.execute("VACUUM")
        row_count = database.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    _integrity_check(database_file)
    return int(row_count)


def _required_database_files() -> list[Path]:
    files = [paths.database_file(name.removesuffix(".db")) for name in DATABASE_TABLES]
    missing = [database_file.name for database_file in files if not database_file.exists()]
    if missing:
        raise RuntimeError(f"Cannot package serving data. Missing database files: {', '.join(missing)}.")
    return files


def _model_files() -> list[Path]:
    return paths.published_model_files()


def pack(archive: Path, window_start_date: date | None = None) -> Path:
    """Write an archive with models and the raw rows needed to rebuild the serving cache."""

    if archive.exists():
        raise FileExistsError(f"Refusing to overwrite existing serving archive {archive}.")
    if not SOURCE_MARKER.exists():
        raise RuntimeError("Cannot package serving data without a data-source marker.")

    window_start_date = window_start_date or season.today() - relativedelta(
        years=features.HISTORICAL_WINDOW_LENGTH_YEARS
    )
    source_name = SOURCE_MARKER.read_text(encoding="utf-8").strip()
    if not source_name:
        raise RuntimeError("Cannot package serving data with an empty data-source marker.")

    databases = _required_database_files()
    models = _model_files()
    if not models:
        raise RuntimeError("Cannot package serving data without a trained model file.")

    archive.parent.mkdir(parents=True, exist_ok=True)
    working_archive = archive.with_name(archive.name + ".incomplete")

    with tempfile.TemporaryDirectory(prefix="nba-serving-data-") as temporary:
        working = Path(temporary)
        database_directory = working / DATABASES
        database_directory.mkdir()
        row_counts = {
            database_file.name: _copy_database(database_file, database_directory / database_file.name, window_start_date)
            for database_file in databases
        }
        row_counts[players.FILEPATH.name] = _narrow_to_players(
            database_directory / players.FILEPATH.name,
            _player_ids(database_directory / player_games.FILEPATH.name)
        )
        model_names = [str(model_file.relative_to(paths.MODELS_DIRECTORY).as_posix()) for model_file in models]
        (working / SOURCE_MARKER.name).write_text(source_name + "\n", encoding="utf-8")
        (working / MANIFEST).write_text(
            json.dumps(
                {
                    "format_version": FORMAT_VERSION,
                    "source": source_name,
                    "window_start_date": season.to_date_string(window_start_date),
                    "database_rows": row_counts,
                    "model_files": model_names
                },
                indent=2,
                sort_keys=True
            ),
            encoding="utf-8"
        )

        with tarfile.open(working_archive, "w:gz") as writing:
            writing.add(database_directory, arcname=DATABASES)
            writing.add(working / SOURCE_MARKER.name, arcname=SOURCE_MARKER.name)
            writing.add(working / MANIFEST, arcname=MANIFEST)
            for model_file in models:
                writing.add(model_file, arcname=f"{MODELS}/{model_file.relative_to(paths.MODELS_DIRECTORY)}")

    os.replace(working_archive, archive)
    return archive


def _safe_members(reading: tarfile.TarFile) -> list[tarfile.TarInfo]:
    members = reading.getmembers()
    for member in members:
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or member.issym() or member.islnk():
            raise RuntimeError(f"Serving archive contains an unsafe member: {member.name}.")
        if not (member.isdir() or member.isfile()):
            raise RuntimeError(f"Serving archive contains an unsupported member: {member.name}.")
    return members


def _read_manifest(directory: Path) -> dict:
    try:
        manifest = json.loads((directory / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError("Serving archive has no readable manifest.") from error

    if manifest.get("format_version") != FORMAT_VERSION:
        raise RuntimeError("Serving archive has an unsupported format version.")
    if not isinstance(manifest.get("source"), str) or not manifest["source"]:
        raise RuntimeError("Serving archive has no source identity.")
    if not isinstance(manifest.get("database_rows"), dict) or not isinstance(manifest.get("model_files"), list):
        raise RuntimeError("Serving archive manifest is incomplete.")
    return manifest


def _verify_loaded_data(directory: Path):
    manifest = _read_manifest(directory)
    marker = directory / SOURCE_MARKER.name
    if not marker.exists() or marker.read_text(encoding="utf-8").strip() != manifest["source"]:
        raise RuntimeError("Serving archive source marker does not match its manifest.")
    try:
        window_start_date = season.from_date_string(manifest["window_start_date"]).date()
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("Serving archive has no valid game-window start date.") from error

    for filename, (table, date_column) in DATABASE_TABLES.items():
        database_file = directory / DATABASES / filename
        if not database_file.exists() or filename not in manifest["database_rows"]:
            raise RuntimeError(f"Serving archive is missing {filename}.")
        _integrity_check(database_file)
        with closing(sqlite3.connect(database_file)) as database:
            actual_rows = database.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            oldest = None if date_column is None else database.execute(
                f"SELECT MIN({date_column}) FROM {table}"
            ).fetchone()[0]
        if actual_rows != manifest["database_rows"][filename]:
            raise RuntimeError(f"Serving archive row count does not match for {filename}.")
        if oldest is not None and season.from_date_string(oldest).date() < window_start_date:
            raise RuntimeError(f"Serving archive holds a game before its stated window in {filename}.")

    # A feature build drops every game of a player it holds no information about, so a package
    # missing one would quietly serve less than it carries.
    described = _player_ids(directory / DATABASES / players.FILEPATH.name)
    unknown = _player_ids(directory / DATABASES / player_games.FILEPATH.name) - described
    if unknown:
        raise RuntimeError(
            f"Serving archive holds games of {len(unknown)} players it has no information row for."
        )

    expected_models = sorted(str(name) for name in manifest["model_files"])
    found_models = sorted(
        str(path.relative_to(directory / MODELS).as_posix())
        for path in (directory / MODELS).rglob("*")
        if path.is_file()
    ) if (directory / MODELS).exists() else []
    if not expected_models or found_models != expected_models:
        raise RuntimeError("Serving archive model files do not match its manifest.")


def load(archive: Path, data_directory: Path = paths.DATA_DIRECTORY) -> Path:
    """Verify and install a serving archive into an empty data directory."""

    if not archive.exists():
        raise FileNotFoundError(f"Serving archive does not exist: {archive}.")
    if data_directory.exists() and any(data_directory.iterdir()):
        raise RuntimeError(f"Refusing to replace nonempty data directory {data_directory}.")

    data_directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".nba-serving-data-", dir=data_directory) as temporary:
        working = Path(temporary)
        with tarfile.open(archive) as reading:
            for member in _safe_members(reading):
                reading.extract(member, working, filter="data")

        _verify_loaded_data(working)
        for child in working.iterdir():
            os.replace(child, data_directory / child.name)

    return data_directory


def main():
    parser = argparse.ArgumentParser(description="Packages and loads the raw data a prediction server needs.")
    commands = parser.add_subparsers(dest="command", required=True)
    pack_command = commands.add_parser("pack", help="Write a server-data archive from this machine's archive.")
    pack_command.add_argument("archive", type=Path, help="New .tar.gz file to write. It must not exist.")
    load_command = commands.add_parser("load", help="Verify and load a server-data archive into an empty data directory.")
    load_command.add_argument("archive", type=Path, help="Archive to load.")
    arguments = parser.parse_args()

    if arguments.command == "pack":
        print(f"Wrote serving data to {pack(arguments.archive)}.")
    else:
        print(f"Loaded serving data into {load(arguments.archive)}.")


if __name__ == "__main__":
    main()
