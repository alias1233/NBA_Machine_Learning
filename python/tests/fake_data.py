"""A small fake league used as test data, in the same format as the stores."""

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from types import ModuleType
from typing import Collection, Iterable, Sequence

import pandas as pd

from nba_ml import paths, season
from nba_ml.database import Database
from nba_ml.entities import Game, GameStatus, Player, RosterEntry, ScheduledGame, Team
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
    """Returns the four teams in the team store's format."""

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
"""The season's two digits as they appear in a game ID."""

def game_id(number: int, season_type: SeasonType = SeasonType.REGULAR_SEASON) -> int:
    """Returns a game ID in the real format: season type prefix, season digits, then game number."""

    return int(f"{season.GAME_ID_PREFIXES[season_type]}{SEASON_DIGITS}{number:05d}")

@dataclass(frozen=True)
class PlayedGame():
    """A finished game, defined by its teams and final score."""

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
"""Six games for each of the four teams."""

NEXT_GAME_DATE = date(2024, 11, 8)
"""A date after every game above, used for upcoming games."""

def games_of(team_id: int, games: Sequence[PlayedGame] = SEASON_GAMES) -> list[PlayedGame]:
    return [game for game in games if team_id in (game.home_team_id, game.away_team_id)]

def points_in(game: PlayedGame, team_id: int) -> int:
    return game.home_points if team_id == game.home_team_id else game.away_points

def opponent_in(game: PlayedGame, team_id: int) -> int:
    return game.away_team_id if team_id == game.home_team_id else game.home_team_id

def matchup(team_id: int, opponent_team_id: int, home: bool) -> str:
    """Returns the matchup string in the raw data format, e.g. ANC vs. BRK or ANC @ BRK."""

    side = team_columns.HOME if home else team_columns.AWAY

    return f"{ABBREVIATIONS[team_id]} {team_columns.HOME_OR_AWAY_ENCODING[side]} {ABBREVIATIONS[opponent_team_id]}"

def _made_shots(points: int) -> tuple[int, int, int]:
    """Returns field goals, three pointers and free throws that add up to the given points."""

    three_pointers = points // 12
    free_throws = (points - three_pointers) % 2
    field_goals = (points - three_pointers - free_throws) // 2

    return (field_goals, three_pointers, free_throws)

def _box_score(points: int, opponent_points: int) -> dict:
    """Returns the box score columns shared by the player and team stores, generated from a points total."""

    field_goals, three_pointers, free_throws = _made_shots(points)

    return {
        team_games.WIN_LOSS.category_name: "W" if points > opponent_points else "L",
        team_games.FIELD_GOALS_MADE.category_name: field_goals,
        team_games.FIELD_GOALS_ATTEMPTED.category_name: field_goals + 45,
        team_games.THREE_POINTERS_MADE.category_name: three_pointers,
        team_games.THREE_POINTERS_ATTEMPTED.category_name: three_pointers + 20,
        team_games.FREE_THROWS_MADE.category_name: free_throws,
        team_games.FREE_THROWS_ATTEMPTED.category_name: free_throws + 5,
        # These vary with the score so rolling columns aren't constant.
        team_games.OFFENSIVE_REBOUNDS.category_name: 8 + points % 5,
        team_games.DEFENSIVE_REBOUNDS.category_name: 30 + points % 7,
        team_games.ASSISTS.category_name: 20 + points % 9,
        team_games.STEALS.category_name: 6 + points % 4,
        team_games.BLOCKS.category_name: 4 + points % 3,
        team_games.TURNOVERS.category_name: 10 + points % 6,
        team_games.PERSONAL_FOULS.category_name: 17 + points % 5
    }

def team_game_rows(game: PlayedGame) -> list[dict]:
    """Returns both teams' rows for a game in the team game store's format."""

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

# PLAYERS: #
PLAYERS_PER_TEAM = 3

def player_id(team_id: int, number: int) -> int:
    """Returns a player ID that encodes the team: team ID * 100 + number."""

    return team_id * 100 + number

def team_of(a_player_id: int) -> int:
    return a_player_id // 100

ALL_PLAYERS = tuple(
    Player(player_id(team.id, number), f"{team.name.split()[0]} Player {number}")
    for team in TEAMS
    for number in range(PLAYERS_PER_TEAM)
)

def player_info_frame(players_to_describe: Sequence[Player] = ALL_PLAYERS) -> pd.DataFrame:
    """Returns one player info row per player, in the format a data source returns."""

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
    """Returns the player's share of the team's points."""

    shares = (5, 3, 2)
    number = a_player_id % 100

    return round(team_points * shares[number] / sum(shares))

def player_game_rows(game: PlayedGame) -> list[dict]:
    """Returns the rows of every player in a game, in the player game store's format."""

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

# LEGACY ARCHIVE: #
LEGACY_TEAM_IDS = {team.id: 900 + team.id for team in TEAMS}
LEGACY_PLAYER_IDS = {player.id: 50_000 + player.id for player in ALL_PLAYERS}
LEGACY_GAME_NUMBER_OFFSET = 500
"""Added to the game number so legacy game IDs differ from current ones but keep the same prefix."""

RETIRED_PLAYER_IDS = {player.id: 60_000 + player.id for player in ALL_PLAYERS}
"""A second set of legacy IDs, used for players who retired before the cutoff."""

def legacy_teams_frame() -> pd.DataFrame:
    """Returns the four teams with legacy IDs and the same abbreviations."""

    frame = teams_frame()
    frame[teams_store.TEAM_ID.category_name] = frame[teams_store.TEAM_ID.category_name].map(LEGACY_TEAM_IDS)

    return frame

def legacy_player_game_frame(
    games: Sequence[PlayedGame] = SEASON_GAMES,
    retired: Collection[int] = (),
    season_type: SeasonType = SeasonType.REGULAR_SEASON
    ) -> pd.DataFrame:
    """Returns the given games with legacy IDs and an empty season type."""

    rows = player_game_frame(games)
    player_ids = {
        player.id: (RETIRED_PLAYER_IDS if player.id in retired else LEGACY_PLAYER_IDS)[player.id]
        for player in ALL_PLAYERS
    }
    rows[player_games.PLAYER_ID.category_name] = rows[player_games.PLAYER_ID.category_name].map(player_ids)
    rows[player_games.TEAM_ID.category_name] = rows[player_games.TEAM_ID.category_name].map(LEGACY_TEAM_IDS)
    rows[player_games.GAME_ID.category_name] = rows[player_games.GAME_ID.category_name].map({
        game.id: game_id(game.number + LEGACY_GAME_NUMBER_OFFSET, season_type) for game in games
    })
    rows[player_games.SEASON_TYPE.category_name] = None

    return rows

def legacy_player_info_frame(described: Sequence[Player] = ALL_PLAYERS) -> pd.DataFrame:
    """Returns player info rows for each player under both sets of legacy IDs."""

    return pd.concat(
        [
            player_info_frame(described).assign(**{
                players.PLAYER_ID.category_name: [ids[player.id] for player in described]
            })
            for ids in (LEGACY_PLAYER_IDS, RETIRED_PLAYER_IDS)
        ],
        ignore_index=True
    )

def _write_table(directory: Path, store: ModuleType, rows: pd.DataFrame):
    database = Database(
        directory / paths.DATABASE_DIRECTORY.name / store.FILEPATH.name,
        store.NAME,
        store.ALL_CATEGORIES.get_categories(),
        store.DATA_CONFLICT_HANDLER,
        store.PRIMARY_KEYS
    )
    with database:
        database.add_dataframe(rows)

def write_legacy_archive(
    directory: Path,
    player_rows: pd.DataFrame,
    described: Sequence[Player] = ALL_PLAYERS
    ) -> Path:
    """Writes a legacy data directory with the three tables the import needs."""

    _write_table(directory, teams_store, legacy_teams_frame())
    _write_table(directory, player_games, player_rows)
    _write_table(directory, players, legacy_player_info_frame(described))

    return directory

# SCHEDULE: #
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

# DATA SOURCE: #
class FakeSource(DataSource):
    """A data source that returns the fake league above instead of calling an API."""

    name = "fake"
    oldest_season = SEASON_YEAR
    request_interval = 0.0
    retry_interval = 0.0

    def __init__(
        self,
        games: Sequence[PlayedGame] = SEASON_GAMES,
        known_players: Sequence[Player] = ALL_PLAYERS,
        schedule: Sequence[ScheduledGame] = (),
        failing_seasons: Iterable[int] = (),
        rosters: Sequence[RosterEntry] | None = None
        ):
        super().__init__()

        self.games = list(games)
        self.known_players = list(known_players)
        self.scheduled = list(schedule)
        self.rostered = None if rosters is None else list(rosters)
        self.failing_seasons = set(failing_seasons)
        self.requests: list[str] = []
        """Log of the requests made, in order, so tests can check what was fetched."""

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

    def rosters(self) -> list[RosterEntry] | None:
        """Returns None unless the test provided rosters, like a source with no roster data."""

        self.requests.append("rosters")

        return None if self.rostered is None else list(self.rostered)

    def schedule(self, season_year: int) -> list[ScheduledGame] | None:
        self.requests.append(f"schedule {season_year}")

        return [game for game in self.scheduled if season.season_of(game.game.date) == season_year]

def roster_entries(
    hurt: Collection[int] = (),
    moved: dict[int, int] | None = None,
    left_out: Collection[int] = ()
    ) -> list[RosterEntry]:
    """Returns a roster entry for every player, with options for injured, traded and missing players."""

    moved = moved or {}

    return [
        RosterEntry(
            player.id,
            moved.get(player.id, team_of(player.id)),
            "Out" if player.id in hurt else None
        )
        for player in ALL_PLAYERS
        if player.id not in left_out
    ]
