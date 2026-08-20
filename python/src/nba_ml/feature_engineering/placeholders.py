"""
The rows standing for a game that has not been played yet.

A prediction feeds the game it is about through the same build a played game goes through, as one
more row. That row holds only what is known before the game is played. Everything else on it, rest,
break length, form, the roster around a player, is filled by the build out of the rows in front of
it rather than assembled here.

Every family that predicts a game needs these rows, and what is known before a game is the same
whoever is being asked about, so it is written once here rather than once per family. A column added
to a store is remembered in one place.
"""

from typing import Any, Collection

import pandas as pd

from nba_ml import season
from nba_ml.entities import Game
from nba_ml.feature_engineering import roster_columns, season_columns, team_columns
from nba_ml.stores import player_games, team_games

def game_id(target_game: Game) -> str:
    """
    What the game being predicted is filed under, which no played game can collide with.

    A real game id is ten digits and this is the one character naming the season phase, which is how
    every other game in the data says which phase it belongs to.
    """

    return season_columns.SEASON_ENCODINGS[target_game.season_type.value]

def _matchup(target_game: Game, team_id: int) -> str:
    """How the raw data writes which side of a game a row belongs to."""

    return team_columns.HOME_OR_AWAY_ENCODING[
        team_columns.HOME if target_game.is_home(team_id) else team_columns.AWAY
    ]

def _known_before_the_game(target_game: Game, team_id: int) -> dict[str, Any]:
    """
    Everything a row of either frame records about the game itself.

    Both stores name these four columns the same way, so one function fills a team row and a player
    row.
    """

    return {
        team_games.TEAM_ID.category_name: team_id,
        team_games.GAME_DATE.category_name: season.to_date_string(target_game.date),
        team_games.GAME_ID.category_name: game_id(target_game),
        team_games.SEASON_TYPE.category_name: season_columns.SEASON_ENCODINGS[target_game.season_type.value],
        team_games.MATCHUP.category_name: _matchup(target_game, team_id)
    }

def game_rows(target_game: Game) -> pd.DataFrame:
    """
    The two rows standing for the game being predicted, one per side, the home team first.

    Both sides are always added, whichever one is being asked about, because every build reads the
    side a subject faces as well as its own.
    """

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
    """
    One row per player expected to play, for the one team a player prediction is about.

    Minutes stand in for being on the floor at all. A player named as returning is given more than
    the core cutoff, so the roster columns count them as core in a game nobody has played yet.
    """

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
