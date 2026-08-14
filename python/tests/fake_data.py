"""
A made up league, written the way the stores hold real data.

One place builds these rows, so every test describes the same games and a column renamed in a store
breaks here rather than in each test. Nothing in this module reaches the network.

The league is four teams playing twelve games over two and a half weeks. The dates are chosen so
that a team plays on back to back days, has a long gap, and wins and loses, because those are what
the schedule and season columns are read off.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable, Sequence

import pandas as pd

from nba_ml import season
from nba_ml.entities import Game, GameStatus, Player, ScheduledGame, Team
from nba_ml.feature_engineering import player_columns, team_columns
from nba_ml.season import SeasonType
from nba_ml.sources.base import DataSource
from nba_ml.stores import player_games, players, team_games, teams as teams_store

TEAMS = (
    Team(1, "Anchorage Anchors", "ANC"),
    Team(2, "Brookvale Bears", "BRK"),
    Team(3, "Cardiff Chargers", "CAR"),
    Team(4, "Dunmore Dragons", "DUN")
)

ABBREVIATIONS = {team.id: team.abbreviation for team in TEAMS}

def teams_frame() -> pd.DataFrame:
    """The four teams as the team store holds them."""

    return pd.DataFrame([
        {
            teams_store.TEAM_ID.category_name: team.id,
            teams_store.ABBREVIATION.category_name: team.abbreviation,
            teams_store.TEAM_NAME.category_name: team.name
        }
        for team in TEAMS
    ])

SEASON_YEAR = 2024
SEASON_DIGITS = "24"
"""How the two year old season is written inside a game id, which is where its phase is written too."""

def game_id(number: int, season_type: SeasonType = SeasonType.REGULAR_SEASON) -> int:
    """
    A game id shaped like a real one: the phase first, then the season, then the game.

    Real ids are stored as numbers, so the leading zeros a service writes are gone and the phase is
    the first character. Everything reading a phase off an id depends on that.
    """

    return int(f"{season.GAME_ID_PREFIXES[season_type]}{SEASON_DIGITS}{number:05d}")

@dataclass(frozen=True)
class PlayedGame():
    """One finished game, described by the two things a box score is worked out from."""

    number: int
    day: date
    home_team_id: int
    away_team_id: int
    home_points: int
    away_points: int

    @property
    def id(self) -> int:
        return game_id(self.number)

SEASON_GAMES = (
    PlayedGame(1, date(2024, 10, 22), 1, 2, 110, 104),
    PlayedGame(2, date(2024, 10, 22), 3, 4, 98, 101),
    PlayedGame(3, date(2024, 10, 23), 2, 3, 112, 115),
    PlayedGame(4, date(2024, 10, 25), 4, 1, 99, 120),
    PlayedGame(5, date(2024, 10, 27), 1, 3, 105, 107),
    PlayedGame(6, date(2024, 10, 27), 2, 4, 118, 96),
    PlayedGame(7, date(2024, 10, 30), 3, 2, 100, 92),
    PlayedGame(8, date(2024, 10, 30), 4, 1, 111, 113),
    PlayedGame(9, date(2024, 11, 2), 1, 4, 108, 100),
    PlayedGame(10, date(2024, 11, 2), 2, 3, 121, 119),
    PlayedGame(11, date(2024, 11, 5), 3, 1, 95, 102),
    PlayedGame(12, date(2024, 11, 5), 4, 2, 103, 109)
)
"""Six games for each of the four teams. Every team wins some and loses some."""

NEXT_GAME_DATE = date(2024, 11, 8)
"""A date after every game above, which is what a game still to be played is dated."""

def games_of(team_id: int, games: Sequence[PlayedGame] = SEASON_GAMES) -> list[PlayedGame]:
    return [game for game in games if team_id in (game.home_team_id, game.away_team_id)]

def points_in(game: PlayedGame, team_id: int) -> int:
    return game.home_points if team_id == game.home_team_id else game.away_points

def opponent_in(game: PlayedGame, team_id: int) -> int:
    return game.away_team_id if team_id == game.home_team_id else game.home_team_id

def matchup(team_id: int, opponent_team_id: int, home: bool) -> str:
    """How the raw data writes which side of a game a row belongs to."""

    side = team_columns.HOME if home else team_columns.AWAY

    return f"{ABBREVIATIONS[team_id]} {team_columns.HOME_OR_AWAY_ENCODING[side]} {ABBREVIATIONS[opponent_team_id]}"

def _made_shots(points: int) -> tuple[int, int, int]:
    """
    Field goals, three pointers and free throws adding up to exactly the given points.

    Points are the number a test is written against, so the shots behind them are worked out rather
    than chosen, which is the reverse of what the pipeline does with them.
    """

    three_pointers = points // 12
    free_throws = (points - three_pointers) % 2
    field_goals = (points - three_pointers - free_throws) // 2

    return (field_goals, three_pointers, free_throws)

def _box_score(points: int, opponent_points: int) -> dict:
    """The columns both the player store and the team store hold, filled from a points total."""

    field_goals, three_pointers, free_throws = _made_shots(points)

    return {
        team_games.WIN_LOSS.category_name: "W" if points > opponent_points else "L",
        team_games.FIELD_GOALS_MADE.category_name: field_goals,
        team_games.FIELD_GOALS_ATTEMPTED.category_name: field_goals + 45,
        team_games.THREE_POINTERS_MADE.category_name: three_pointers,
        team_games.THREE_POINTERS_ATTEMPTED.category_name: three_pointers + 20,
        team_games.FREE_THROWS_MADE.category_name: free_throws,
        team_games.FREE_THROWS_ATTEMPTED.category_name: free_throws + 5,
        # Varied with the score so no rolling column is built over a constant.
        team_games.OFFENSIVE_REBOUNDS.category_name: 8 + points % 5,
        team_games.DEFENSIVE_REBOUNDS.category_name: 30 + points % 7,
        team_games.ASSISTS.category_name: 20 + points % 9,
        team_games.STEALS.category_name: 6 + points % 4,
        team_games.BLOCKS.category_name: 4 + points % 3,
        team_games.TURNOVERS.category_name: 10 + points % 6,
        team_games.PERSONAL_FOULS.category_name: 17 + points % 5
    }

def team_game_rows(game: PlayedGame) -> list[dict]:
    """Both sides of one game, as the team game store holds them."""

    def row(team_id: int, opponent_team_id: int, points: int, opponent_points: int) -> dict:
        return {
            team_games.TEAM_ID.category_name: team_id,
            team_games.GAME_ID.category_name: game.id,
            team_games.GAME_DATE.category_name: season.to_date_string(game.day),
            team_games.SEASON_TYPE.category_name: season.GAME_ID_PREFIXES[SeasonType.REGULAR_SEASON],
            team_games.MATCHUP.category_name: matchup(
                team_id, opponent_team_id, home=team_id == game.home_team_id
            ),
            team_games.MINUTES_PLAYED.category_name: 240,
            **_box_score(points, opponent_points)
        }

    return [
        row(game.home_team_id, game.away_team_id, game.home_points, game.away_points),
        row(game.away_team_id, game.home_team_id, game.away_points, game.home_points)
    ]

def team_game_frame(games: Sequence[PlayedGame] = SEASON_GAMES) -> pd.DataFrame:
    return pd.DataFrame([row for game in games for row in team_game_rows(game)])

# THE PLAYERS: #
PLAYERS_PER_TEAM = 3

def player_id(team_id: int, number: int) -> int:
    """A player id that says which team the player is on, so a test can read one at a glance."""

    return team_id * 100 + number

def team_of(a_player_id: int) -> int:
    return a_player_id // 100

ALL_PLAYERS = tuple(
    Player(player_id(team.id, number), f"{team.name.split()[0]} Player {number}")
    for team in TEAMS
    for number in range(PLAYERS_PER_TEAM)
)

def player_info_frame(players_to_describe: Sequence[Player] = ALL_PLAYERS) -> pd.DataFrame:
    """
    One row per player, written the way a data service publishes one.

    Height arrives as feet and inches, and a player who was never drafted arrives with a word where
    a number goes, so both are here rather than only the tidy case.
    """

    return pd.DataFrame([
        {
            players.PLAYER_ID.category_name: player.id,
            players.PLAYER_NAME.category_name: player.name,
            players.HEIGHT.category_name: f"6-{4 + player.id % 8}",
            players.WEIGHT.category_name: 190 + player.id % 40,
            players.POSITION.category_name: "Guard",
            players.FROM_YEAR.category_name: 2015 + player.id % 5,
            players.TO_YEAR.category_name: SEASON_YEAR,
            players.BIRTHDATE.category_name: f"199{player.id % 8}-04-15T00:00:00",
            players.DRAFT_NUMBER.category_name: (
                player_columns.UNDRAFTED if player.id % 5 == 0 else str(1 + player.id % 30)
            )
        }
        for player in players_to_describe
    ])

def player_points(a_player_id: int, team_points: int) -> int:
    """
    How a team's points are split between its players.

    The first player takes the largest share, so the roster columns have a core player to lose and
    the players are not interchangeable.
    """

    shares = (5, 3, 2)
    number = a_player_id % 100

    return round(team_points * shares[number] / sum(shares))

def player_game_rows(game: PlayedGame) -> list[dict]:
    """Every player of both teams in one game, as the player game store holds them."""

    def rows(team_id: int, opponent_team_id: int, points: int, opponent_points: int) -> list[dict]:
        return [
            {
                player_games.PLAYER_ID.category_name: player.id,
                player_games.GAME_ID.category_name: game.id,
                player_games.TEAM_ID.category_name: team_id,
                player_games.GAME_DATE.category_name: season.to_date_string(game.day),
                player_games.SEASON_TYPE.category_name: season.GAME_ID_PREFIXES[SeasonType.REGULAR_SEASON],
                player_games.MATCHUP.category_name: matchup(
                    team_id, opponent_team_id, home=team_id == game.home_team_id
                ),
                # Everyone plays more than the core cutoff, so the roster is stable until a test
                # takes somebody out of it.
                player_games.MINUTES_PLAYED.category_name: 30,
                player_games.PLUS_MINUS.category_name: points - opponent_points,
                **_box_score(player_points(player.id, points), 0)
            }
            for player in ALL_PLAYERS
            if team_of(player.id) == team_id
        ]

    return (
        rows(game.home_team_id, game.away_team_id, game.home_points, game.away_points)
        + rows(game.away_team_id, game.home_team_id, game.away_points, game.home_points)
    )

def player_game_frame(games: Sequence[PlayedGame] = SEASON_GAMES) -> pd.DataFrame:
    return pd.DataFrame([row for game in games for row in player_game_rows(game)])

# THE SCHEDULE: #
def scheduled_game(
    game: PlayedGame,
    status: GameStatus = GameStatus.FINAL,
    tipoff: datetime | None = None
    ) -> ScheduledGame:
    return ScheduledGame(
        id=game.id,
        game=Game(game.day, game.home_team_id, game.away_team_id),
        status=status,
        tipoff=tipoff
    )

# THE SOURCE: #
class FakeSource(DataSource):
    """
    A data source answering out of the league above rather than out of a service.

    It behaves like a real one where that is what a test is about: it honours the season, phase and
    date a collector asks for, and it can be told to fail, which is what a service refusing a season
    looks like from here.
    """

    name = "fake"
    oldest_season = SEASON_YEAR
    request_interval = 0.0
    retry_interval = 0.0

    def __init__(
        self,
        games: Sequence[PlayedGame] = SEASON_GAMES,
        known_players: Sequence[Player] = ALL_PLAYERS,
        schedule: Sequence[ScheduledGame] = (),
        failing_seasons: Iterable[int] = ()
        ):
        super().__init__()

        self.games = list(games)
        self.known_players = list(known_players)
        self.scheduled = list(schedule)
        self.failing_seasons = set(failing_seasons)
        self.requests: list[str] = []
        """What was asked for, in order, so a test can check a collector asked for the right thing."""

    def teams(self) -> list[Team]:
        self.requests.append("teams")

        return list(TEAMS)

    def players(self) -> list[Player]:
        self.requests.append("players")

        return list(self.known_players)

    def player_info(self, a_player_id: int) -> pd.DataFrame | None:
        self.requests.append(f"player_info {a_player_id}")
        described = [player for player in self.known_players if player.id == a_player_id]

        return player_info_frame(described) if described else None

    def _games_in(
        self,
        season_year: int,
        season_type: SeasonType,
        date_from: date | None,
        date_to: date | None
        ) -> list[PlayedGame]:
        if season_year in self.failing_seasons:
            raise ConnectionError(f"The fake source refuses the {season_year} season.")

        if season_year != SEASON_YEAR or season_type is not SeasonType.REGULAR_SEASON:
            return []

        return [
            game for game in self.games
            if (date_from is None or game.day >= date_from)
            and (date_to is None or game.day <= date_to)
        ]

    def player_games(
        self,
        season_year: int,
        season_type: SeasonType,
        date_from: date | None = None,
        date_to: date | None = None
        ) -> pd.DataFrame | None:
        self.requests.append(f"player_games {season_year} {season_type.value} {date_from} {date_to}")

        return self._fetch(
            lambda: player_game_frame(self._games_in(season_year, season_type, date_from, date_to)),
            f"player games of {season_year}"
        )

    def schedule(self, season_year: int) -> list[ScheduledGame] | None:
        self.requests.append(f"schedule {season_year}")

        return [game for game in self.scheduled if season.season_of(game.game.date) == season_year]
