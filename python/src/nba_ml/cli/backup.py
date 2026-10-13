"""Command for backing up the databases and trained models."""

import argparse
import sqlite3
import tarfile
import tempfile
from contextlib import closing
from datetime import datetime
from pathlib import Path

from nba_ml import paths
from nba_ml.data_collection.source_identity import MARKER as SOURCE_MARKER

ARCHIVE_PREFIX = "nba-ml-"
ARCHIVE_SUFFIX = ".tar.gz"
VERSION_FORMAT = "%Y%m%d-%H%M%S"
"""Timestamp format used in archive names. Sorting by name sorts by date."""

WORKING_SUFFIX = ".incomplete"
"""Suffix added to an archive while it is still being written."""

KEPT_BACKUPS = 7

DATABASES = "databases"
MODELS = "models"

def _copy_databases(into: Path) -> int:
    """Copies every database with SQLite's backup API and returns the number copied."""

    into.mkdir(parents=True, exist_ok=True)
    copied = 0

    for database_file in sorted(paths.DATABASE_DIRECTORY.glob("*.db")):
        with (
            closing(sqlite3.connect(database_file)) as source,
            closing(sqlite3.connect(into / database_file.name)) as copy
        ):
            source.backup(copy)

        copied += 1

    return copied

def _write_archive(archive: Path) -> tuple[int, int]:
    """Writes the databases and model files to an archive. Returns the number of each."""

    archive.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="nba-ml-backup-") as working:
        databases = Path(working) / DATABASES
        copied = _copy_databases(databases)
        models = paths.published_model_files()

        with tarfile.open(archive, "w:gz") as writing:
            writing.add(databases, arcname=DATABASES)

            if SOURCE_MARKER.exists():
                writing.add(SOURCE_MARKER, arcname=SOURCE_MARKER.name)

            for model_file in models:
                writing.add(model_file, arcname=f"{MODELS}/{model_file.relative_to(paths.MODELS_DIRECTORY)}")

    return (copied, len(models))

def _remove_old_archives(keep: int) -> int:
    """Deletes all but the newest `keep` archives and any incomplete ones."""

    archives = sorted(paths.BACKUP_DIRECTORY.glob(f"{ARCHIVE_PREFIX}*{ARCHIVE_SUFFIX}"))

    for archive in archives[:-keep]:
        archive.unlink()

    for half_written in paths.BACKUP_DIRECTORY.glob(f"{ARCHIVE_PREFIX}*{ARCHIVE_SUFFIX}{WORKING_SUFFIX}"):
        half_written.unlink()

    return max(len(archives) - keep, 0)

def back_up(keep: int = KEPT_BACKUPS) -> Path:
    """Creates a new backup archive, then deletes all but the newest `keep`."""

    if keep < 1:
        raise ValueError(f"A backup run leaves at least the archive it just wrote. Got {keep}.")

    taken = datetime.now().strftime(VERSION_FORMAT)
    archive = paths.BACKUP_DIRECTORY / f"{ARCHIVE_PREFIX}{taken}{ARCHIVE_SUFFIX}"
    working = archive.with_name(archive.name + WORKING_SUFFIX)

    databases, models = _write_archive(working)
    working.replace(archive)
    removed = _remove_old_archives(keep)

    print(
        f"Backed up {databases} databases and {models} model files to {archive} "
        f"({archive.stat().st_size / 1024 ** 2:.0f} MB). Removed {removed} older archives."
    )

    return archive

def main():
    parser = argparse.ArgumentParser(
        description="Archives the collected data and the trained models, which nothing can rebuild."
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=KEPT_BACKUPS,
        metavar="N",
        help="How many archives to leave on disk, newest first, counting the one this run writes."
    )
    arguments = parser.parse_args()

    back_up(arguments.keep)

if __name__ == "__main__":
    main()
