"""Collects the season schedule."""

from typing import Iterable

from nba_ml import season
from nba_ml.sources.base import DataSource, SourceDataError
from nba_ml.stores import schedule as schedule_store

def collect(
    source: DataSource,
    seasons: Iterable[int] | None = None,
    print_debug: bool = True
    ) -> int:
    """Fetches the schedule for the given seasons, stores it, and returns the number of games written."""

    if seasons is None:
        seasons = (season.current_season(), season.current_season() + 1)

    rows_written = 0
    for season_year in seasons:
        games = source.schedule(season_year)
        if games is None:
            raise SourceDataError(f"The {season_year} schedule could not be fetched. No schedule rows were stored.")
        if not games:
            continue

        rows_written += schedule_store.store(games)

        if print_debug:
            print(f"schedule: {season_year}, {len(games)} games")

    return rows_written
