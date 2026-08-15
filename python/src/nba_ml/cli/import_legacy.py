"""
Filling the archive with the seasons the data source does not reach, out of an older nba.com archive.

A developer command, run once on the machine that trains. It reads a second data directory rather
than a service, so it takes no source and makes no request. See
nba_ml/data_collection/legacy_archive.py for how the two archives' identifiers are matched up.

Collect from the data source before running this. The seasons the two archives share are what a
legacy player is recognised by, and without them nothing can be.
"""

import argparse
from datetime import date
from pathlib import Path

from nba_ml import season
from nba_ml.data_collection import legacy_archive


def _date(text: str) -> date:
    return season.from_date_string(text).date()


def main():
    parser = argparse.ArgumentParser(
        description="Fills the seasons before the data source's floor from an older nba.com archive."
    )
    parser.add_argument(
        "legacy_directory",
        type=Path,
        help="A data directory collected through nba_api, holding its databases the way this one does."
    )
    parser.add_argument(
        "--until",
        type=_date,
        default=season.PLAYER_GAME_COLLECTION_START_DATE,
        metavar="YYYY-MM-DD",
        help=(
            "The first date the data source itself covers. Games before it are imported and the "
            f"rest are left to the source. Defaults to {season.PLAYER_GAME_COLLECTION_START_DATE}."
        )
    )
    parser.add_argument(
        "--minimum-matching-games",
        type=int,
        default=legacy_archive.MINIMUM_MATCHING_GAMES,
        metavar="GAMES",
        help=(
            "How many games two players must record the same line in before they are taken to be "
            f"one player. Defaults to {legacy_archive.MINIMUM_MATCHING_GAMES}."
        )
    )
    parser.add_argument("--quiet", action="store_true", help="Only print the finished report.")
    arguments = parser.parse_args()

    report = legacy_archive.import_games(
        arguments.legacy_directory,
        arguments.until,
        arguments.minimum_matching_games,
        print_debug=not arguments.quiet
    )
    print(report.describe())


if __name__ == "__main__":
    main()
