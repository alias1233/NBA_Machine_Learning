"""
The nba.com statistics service, reached through the `nba_api` package.

It is free and complete, but it is reported to refuse requests from datacenter addresses, so it has
to be tested from the server before anything depends on it. That is why it sits behind DataSource.

The service names its box score columns the way the stores hold them, so those are not renamed here.
Its own names for anything else are, which is what a source whose names differ does throughout.
"""

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

GAME_STATUSES = {
    1: GameStatus.SCHEDULED,
    2: GameStatus.LIVE,
    3: GameStatus.FINAL
}

# A team the service has not decided yet, which is how a playoff game reads before the series that
# feeds it has finished.
UNDECIDED_TEAM_ID = 0

def _scheduled_game(row: pd.Series) -> ScheduledGame | None:
    """One schedule row, or None when it is a game this project does not model."""

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
            # The eastern date, because that is the date a box score is written under.
            date.fromisoformat(row["gameDateEst"][:10]),
            home_team_id,
            away_team_id,
            season_type
        ),
        status=GAME_STATUSES.get(int(row["gameStatus"]), GameStatus.SCHEDULED),
        tipoff=None if not tipoff else datetime.fromisoformat(tipoff)
    )

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

    def rosters(self) -> list[RosterEntry] | None:
        """
        None, because nba.com publishes no roster or injury feed this project can read.

        An archive collected through this source therefore goes on assuming a team plays whoever
        played its last game, and the site's roster controls open empty. See nba_ml/stores/rosters.py.
        """

        return None

    def schedule(self, season_year: int) -> list[ScheduledGame] | None:
        """
        One request covers a whole season, played games and unplayed ones alike, so this is cheap
        enough to run as often as the box score collection it sits beside.
        """

        return self._fetch(
            lambda: self._season_games(season_year),
            f"the {season_name(season_year)} schedule"
        )

    def _season_games(self, season_year: int) -> list[ScheduledGame]:
        """Reading the rows sits inside the fetch, so a response this cannot read is retried."""

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
