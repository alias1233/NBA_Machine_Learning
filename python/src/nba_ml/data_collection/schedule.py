"""
Collecting the schedule, which is the games that have not been played yet.

One request covers a whole season, so an update refetches the season outright rather than working
out what changed. That is also what keeps a postponed game's new date correct.
"""

from typing import Iterable

from nba_ml import season
from nba_ml.sources.base import DataSource
from nba_ml.stores import schedule as schedule_store

def collect(
    source: DataSource,
    seasons: Iterable[int] | None = None,
    print_debug: bool = True
    ) -> int:
    """
    Writes one row per scheduled game to the store and returns how many were written.

    Args:
        seasons defaults to the season under way and the one after it, because next season's
        schedule is published months before it starts.
    """

    if seasons is None:
        seasons = (season.current_season(), season.current_season() + 1)

    rows_written = 0
    for season_year in seasons:
        games = source.schedule(season_year)
        if not games:
            continue

        rows_written += schedule_store.store(games)

        if print_debug:
            print(f"schedule: {season_year}, {len(games)} games")

    return rows_written
