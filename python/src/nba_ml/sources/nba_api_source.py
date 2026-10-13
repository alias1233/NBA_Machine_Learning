"""Data source for nba.com stats, using the `nba_api` package."""

from datetime import date, datetime

import pandas as pd
from nba_api.stats.endpoints.commonplayerinfo import CommonPlayerInfo
from nba_api.stats.endpoints.leaguegamelog import LeagueGameLog
from nba_api.stats.endpoints.scheduleleaguev2 import ScheduleLeagueV2
from nba_api.stats.library.parameters import PlayerOrTeamAbbreviation, SeasonTypeAllStar
from nba_api.stats.static import players as static_players, teams as static_teams

from nba_ml import season
from nba_ml.entities import Game, GameStatus, Player, RosterEntry, ScheduledGame, Team
from nba_ml.season import SeasonType
from nba_ml.sources.base import DataSource

# Columns that have a different name in this source than in the stores.
COLUMN_NAMES = {
    "DISPLAY_FIRST_LAST": "PLAYER_NAME"
}

SEASON_TYPE_NAMES = {
    SeasonType.PRESEASON: SeasonTypeAllStar.preseason,
    SeasonType.REGULAR_SEASON: SeasonTypeAllStar.regular,
    SeasonType.PLAY_IN: SeasonTypeAllStar.playin,
    SeasonType.PLAYOFFS: SeasonTypeAllStar.playoffs
}

GAME_STATUSES = {
    1: GameStatus.SCHEDULED,
    2: GameStatus.LIVE,
    3: GameStatus.FINAL
}

# Team ID used for games whose teams are not known yet.
UNDECIDED_TEAM_ID = 0

def _scheduled_game(row: pd.Series) -> ScheduledGame | None:
    """Converts a schedule row to a ScheduledGame. Returns None for unsupported season types or undecided teams."""

    game_id = int(row["gameId"])
    season_type = season.season_type_of_game_id(game_id)
    home_team_id = int(row["homeTeam_teamId"])
    away_team_id = int(row["awayTeam_teamId"])

    if season_type is None or UNDECIDED_TEAM_ID in (home_team_id, away_team_id):
        return None

    tipoff = row["gameDateTimeUTC"]

    return ScheduledGame(
        id=game_id,
        game=Game(
            # Use the Eastern date, since box scores are stored under it.
            date.fromisoformat(row["gameDateEst"][:10]),
            home_team_id,
            away_team_id,
            season_type
        ),
        status=GAME_STATUSES.get(int(row["gameStatus"]), GameStatus.SCHEDULED),
        tipoff=None if not tipoff else datetime.fromisoformat(tipoff)
    )

# The API formats a season as "2024-25" and a date as MM/DD/YYYY.
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
        """This list comes bundled with nba_api, so it is only as up to date as the installed version."""

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

    def rosters(self) -> list[RosterEntry] | None:
        """Returns None because nba.com has no roster or injury data."""

        return None

    def schedule(self, season_year: int) -> list[ScheduledGame] | None:
        return self._fetch(
            lambda: self._season_games(season_year),
            f"the {season_name(season_year)} schedule"
        )

    def _season_games(self, season_year: int) -> list[ScheduledGame]:
        games = ScheduleLeagueV2(season=season_name(season_year)).season_games.get_data_frame()
        scheduled = (_scheduled_game(row) for _, row in games.iterrows())

        return [game for game in scheduled if game is not None]

    def _game_log(
        self,
        season_year: int,
        season_type: SeasonType,
        date_from: date | None,
        date_to: date | None,
        player_or_team: str
        ) -> pd.DataFrame | None:
        games = self._fetch(
            lambda: LeagueGameLog(
                player_or_team_abbreviation=player_or_team,
                season=season_name(season_year),
                season_type_all_star=SEASON_TYPE_NAMES[season_type],
                date_from_nullable=date_name(date_from),
                date_to_nullable=date_name(date_to)
            ).get_data_frames()[0],
            f"the {season_name(season_year)} {season_type.value.lower()}"
        )

        if games is not None:
            games["SEASON_TYPE"] = season.GAME_ID_PREFIXES[season_type]

        return games
