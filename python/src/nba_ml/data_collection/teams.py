"""Collecting the thirty teams. One fetch, and it rarely changes."""

import pandas as pd

from nba_ml.sources.base import DataSource, SourceDataError
from nba_ml.stores import teams as teams_store

def collect(source: DataSource, print_debug: bool = True) -> int:
    """Writes one row per team to the store and returns how many were written."""

    teams = source.teams()
    if not teams:
        raise SourceDataError("The data source named no teams at all, so nothing was stored.")

    rows_written = teams_store.store(
        pd.DataFrame(
            [
                {
                    teams_store.TEAM_ID.category_name : team.id,
                    teams_store.ABBREVIATION.category_name : team.abbreviation,
                    teams_store.TEAM_NAME.category_name : team.name
                }
                for team in teams
            ]
        )
    )

    if print_debug:
        print(f"teams: {rows_written} rows")

    return rows_written
