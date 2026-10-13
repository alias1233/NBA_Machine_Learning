"""Builds placeholder rows for a game that has not been played yet."""

from typing import Any, Collection

import pandas as pd

from nba_ml import season
from nba_ml.entities import Game
from nba_ml.feature_engineering import roster_columns, season_columns, team_columns
from nba_ml.stores import player_games, team_games

def game_id(target_game: Game) -> str:
    """Returns the placeholder game ID for the game being predicted. It can't match a real game ID."""

    return season_columns.SEASON_ENCODINGS[target_game.season_type.value]

def _matchup(target_game: Game, team_id: int) -> str:
    """Returns the matchup marker the raw data uses for home (vs.) or away (@)."""

    return team_columns.HOME_OR_AWAY_ENCODING[
        team_columns.HOME if target_game.is_home(team_id) else team_columns.AWAY
    ]

def _known_before_the_game(target_game: Game, team_id: int) -> dict[str, Any]:
    """Returns the columns that are known before the game for the given team."""

    return {
        team_games.TEAM_ID.category_name: team_id,
        team_games.GAME_DATE.category_name: season.to_date_string(target_game.date),
        team_games.GAME_ID.category_name: game_id(target_game),
        team_games.SEASON_TYPE.category_name: season_columns.SEASON_ENCODINGS[target_game.season_type.value],
        team_games.MATCHUP.category_name: _matchup(target_game, team_id)
    }

def game_rows(target_game: Game) -> pd.DataFrame:
    """Returns two placeholder team rows for the game being predicted, home team first."""

    return pd.DataFrame([
        _known_before_the_game(target_game, team_id)
        for team_id in (target_game.home_team_id, target_game.away_team_id)
    ])

def player_rows(
    target_game: Game,
    team_id: int,
    playing_player_ids: Collection[int],
    returning_player_ids: Collection[int]
    ) -> pd.DataFrame:
    """Returns one placeholder player row for each player expected to play for the given team."""

    returning = set(returning_player_ids)

    return pd.DataFrame([
        {
            **_known_before_the_game(target_game, team_id),
            player_games.PLAYER_ID.category_name: player_id,
            player_games.MINUTES_PLAYED.category_name: (
                roster_columns.CORE_PLAYER_MINUTES_CUTOFF + 1 if player_id in returning else 1
            )
        }
        for player_id in playing_player_ids
    ])
