"""
Copying what the server cannot rebuild for itself.

Two things are irreplaceable: the collected box scores, which took thousands of paced requests to a
data service, and the trained model files, which were fit on a machine the server is not. Everything
else under the data directory is derived. A feature build is ten seconds of work and a training cache
is a saved copy of work any training run can simply do again, so neither is worth carrying.

A database is copied with SQLite's own backup rather than read as bytes, so an archive taken while a
collection is writing still holds a whole database rather than a torn one.

Every choice is a command line argument and nothing is asked for at a prompt, so the command a person
runs by hand is the command a scheduled job runs.
"""

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
"""How an archive is named after when it was taken. Sorting these names sorts them by age."""

WORKING_SUFFIX = ".incomplete"
"""What an archive is called while it is being written, so a half written one is never kept."""

KEPT_BACKUPS = 7
"""How many archives are left on disk. A week of nightly ones, which is what catches a slow mistake."""

DATABASES = "databases"
MODELS = "models"

def _copy_databases(into: Path) -> int:
    """Every database, copied through SQLite so that a copy taken mid write is still whole."""

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
    """
    Writes one archive holding the databases and the model files.

    Returns:
        (databases copied, model files copied)
    """

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
    """Leaves the newest archives and removes the rest. Returns how many went."""

    archives = sorted(paths.BACKUP_DIRECTORY.glob(f"{ARCHIVE_PREFIX}*{ARCHIVE_SUFFIX}"))

    for archive in archives[:-keep]:
        archive.unlink()

    return max(len(archives) - keep, 0)

def back_up(keep: int = KEPT_BACKUPS) -> Path:
    """
    Writes one archive of everything that cannot be rebuilt, then removes all but the newest keep.

    The archive is written under a working name and moved into place whole, so a run that dies part
    way through leaves nothing that reads like a finished backup.

    Args:
        keep counts the archive this run writes, so it is at least one.

    Returns:
        The archive written.
    """

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
