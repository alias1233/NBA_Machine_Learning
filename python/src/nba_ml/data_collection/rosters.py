"""Collects current team rosters and injury statuses."""

from nba_ml.sources.base import DataSource
from nba_ml.stores import rosters as rosters_store

def collect(source: DataSource, print_debug: bool = True) -> int:
    """Replaces the stored roster snapshot and returns the number of rows written."""

    entries = source.rosters()

    if entries is None:
        if print_debug:
            print(f"rosters: the {source.name} source publishes none, so none were collected")

        return 0

    rows_written = rosters_store.store(entries)

    if print_debug:
        hurt = sum(1 for entry in entries if not entry.playing)
        print(f"rosters: {rows_written} rows, {hurt} of them ruled out by the injury report")

    return rows_written
