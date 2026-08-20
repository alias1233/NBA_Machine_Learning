"""
Collecting who is on each team right now, and who is hurt.

A handful of requests, and the only ones that describe a game that has not been played. It is a
snapshot, so each run replaces the whole table rather than adding to it. See nba_ml/stores/rosters.py.
"""

from nba_ml.sources.base import DataSource
from nba_ml.stores import rosters as rosters_store

def collect(source: DataSource, print_debug: bool = True) -> int:
    """
    Replaces the stored roster snapshot and returns how many rows were written.

    A source with no roster feed writes nothing and is not a failure. The pipeline goes on assuming
    a team plays whoever played its last game, which is what it did before any of this was collected.
    """

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
