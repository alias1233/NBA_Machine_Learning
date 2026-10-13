"""Collects the NBA teams."""

import pandas as pd

from nba_ml.sources.base import DataSource, SourceDataError
from nba_ml.stores import teams as teams_store

def collect(source: DataSource, print_debug: bool = True) -> int:
    """Fetches the teams, stores them, and returns the number of rows written."""

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
