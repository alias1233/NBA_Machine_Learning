"""
The nba.com statistics service, reached through the `nba_api` package.

It is free and complete, but it is reported to refuse requests from datacenter addresses, so it has
to be tested from the server before anything depends on it. That is why it sits behind DataSource.

The service names its box score columns the way the stores hold them, so those are not renamed here.
Its own names for anything else are, which is what a source whose names differ does throughout.
"""

from datetime import date

import pandas as pd
from nba_api.stats.endpoints.commonplayerinfo import CommonPlayerInfo
from nba_api.stats.endpoints.leaguegamelog import LeagueGameLog
from nba_api.stats.library.parameters import PlayerOrTeamAbbreviation, SeasonTypeAllStar
from nba_api.stats.static import players as static_players, teams as static_teams

from nba_ml.entities import Player, Team
from nba_ml.season import SeasonType
from nba_ml.sources.base import DataSource

# Columns this service names differently from the stores. A source imports no store, so the two
# agree on these names rather than share a constant, exactly as they already do for a box score.
COLUMN_NAMES = {
    "DISPLAY_FIRST_LAST": "PLAYER_NAME"
}

SEASON_TYPE_NAMES = {
    SeasonType.PRESEASON: SeasonTypeAllStar.preseason,
    SeasonType.REGULAR_SEASON: SeasonTypeAllStar.regular,
    SeasonType.PLAY_IN: SeasonTypeAllStar.playin,
    SeasonType.PLAYOFFS: SeasonTypeAllStar.playoffs
}

# The service writes a season as the two years it spans, and a date as month, day, year.
def season_name(season_year: int) -> str:
    return f"{season_year}-{str(season_year + 1)[-2:]}"

def date_name(day: date | None) -> str:
    return "" if day is None else day.strftime("%m/%d/%Y")

class NBAApiSource(DataSource):
    name = "nba_api"
    oldest_season = 1996
    request_interval = 0.6

    def teams(self) -> list[Team]:
        return [
            Team(team["id"], team["full_name"], team["abbreviation"])
            for team in static_teams.get_teams()
        ]

    def players(self) -> list[Player]:
        """This list ships with the package, so it is only as current as the installed version."""

        return [Player(player["id"], player["full_name"]) for player in static_players.get_players()]

    def player_info(self, player_id: int) -> pd.DataFrame | None:
        return self._fetch(
            lambda: CommonPlayerInfo(player_id=player_id).get_data_frames()[0].rename(columns=COLUMN_NAMES),
            f"player {player_id}"
        )

    def player_games(
        self,
        season_year: int,
        season_type: SeasonType,
        date_from: date | None = None,
        date_to: date | None = None
        ) -> pd.DataFrame | None:
        return self._game_log(
            season_year,
            season_type,
            date_from,
            date_to,
            PlayerOrTeamAbbreviation.player
        )

    def team_games(
        self,
        season_year: int,
        season_type: SeasonType,
        date_from: date | None = None,
        date_to: date | None = None
        ) -> pd.DataFrame | None:
        return self._game_log(
            season_year,
            season_type,
            date_from,
            date_to,
            PlayerOrTeamAbbreviation.team
        )

    def _game_log(
        self,
        season_year: int,
        season_type: SeasonType,
        date_from: date | None,
        date_to: date | None,
        player_or_team: str
        ) -> pd.DataFrame | None:
        return self._fetch(
            lambda: LeagueGameLog(
                player_or_team_abbreviation=player_or_team,
                season=season_name(season_year),
                season_type_all_star=SEASON_TYPE_NAMES[season_type],
                date_from_nullable=date_name(date_from),
                date_to_nullable=date_name(date_to)
            ).get_data_frames()[0],
            f"the {season_name(season_year)} {season_type.value.lower()}"
        )
