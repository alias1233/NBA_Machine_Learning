"""Features for how a subject has performed in similar games, such as home games or playoff games."""

from dataclasses import dataclass
from typing import Sequence

import pandas as pd

from nba_ml.feature_engineering import game_columns, rolling, season_columns, team_columns
from nba_ml.feature_engineering.rolling import RollingCategory
from nba_ml.stores import team_games

@dataclass(frozen=True)
class Situation():
    """A way of grouping a subject's games, such as by opponent or by home and away."""

    name: str
    """Used in the names of the columns created for this situation."""

    label_column: str
    """Column whose value defines which games are in the same group."""

    window: int
    """Number of most recent games in the group to average over."""

@dataclass(frozen=True)
class SituationalStat():
    """A stat to track per situation, with the column it is compared against."""

    name: str
    """Used in the names of the columns created for this stat."""

    value_column: str
    expectation_column: str
    """Column with the subject's average going into the game, which is subtracted from the value."""

FORM_PREFIX = "FORM_"
GAMES_PREFIX = "GAMES_"
OVER_EXPECTED_PREFIX = "OVER_EXPECTED_"
"""Prefix for the temporary columns with a game's value minus its expected value."""

AGAINST_THIS_OPPONENT = Situation(
    "AGAINST_THIS_OPPONENT",
    team_columns.OPPONENT_PREFIX + team_games.TEAM_ID.category_name,
    10
)
IN_THIS_SEASON_TYPE = Situation("IN_THIS_SEASON_TYPE", season_columns.SEASON_TYPE, 20)
AT_HOME_OR_AWAY = Situation("AT_HOME_OR_AWAY", team_columns.HOME_OR_AWAY, 20)

ALL_SITUATIONS = [AGAINST_THIS_OPPONENT, IN_THIS_SEASON_TYPE, AT_HOME_OR_AWAY]

def form_column(situation: Situation, stat: SituationalStat) -> str:
    return f"{FORM_PREFIX}{situation.name}_{stat.name}"

def games_column(situation: Situation) -> str:
    return f"{GAMES_PREFIX}{situation.name}"

def all_columns(
    situations: Sequence[Situation],
    stats: Sequence[SituationalStat]
    ) -> list[str]:
    """Returns the names of every column add_columns creates."""

    return [
        form_column(situation, stat) for situation in situations for stat in stats
    ] + [
        games_column(situation) for situation in situations
    ]

def _windows_of(
    situation: Situation,
    subject_id_column: str,
    stats: Sequence[SituationalStat]
    ) -> list[RollingCategory]:
    """Returns the rolling definitions for one situation: a form column per stat and a game count."""

    return [
        RollingCategory(
            form_column(situation, stat),
            OVER_EXPECTED_PREFIX + stat.name,
            rolling.MEAN_FUNCTION,
            situation.window
        )
        for stat in stats
    ] + [
        RollingCategory(
            games_column(situation),
            subject_id_column,
            rolling.COUNT_FUNCTION,
            situation.window
        )
    ]

def add_columns(
    game_data: pd.DataFrame,
    subject_id_column: str,
    situations: Sequence[Situation],
    stats: Sequence[SituationalStat]
    ) -> pd.DataFrame:
    """Adds every situational column. Each subject's games must be sorted by date."""

    if not situations or not stats:
        return game_data

    # A subject's first game has no prior average to compare against, so it is left as NaN.
    first_game = game_data.groupby(by=subject_id_column, sort=False).cumcount() == 0
    read_by_the_windows = pd.DataFrame(
        {
            OVER_EXPECTED_PREFIX + stat.name: (
                game_data[stat.value_column] - game_data[stat.expectation_column]
            ).astype(game_columns.BUILT_COLUMN_TYPE)
            for stat in stats
        },
        index=game_data.index
    ).mask(first_game)

    for column in dict.fromkeys(
        [subject_id_column] + [situation.label_column for situation in situations]
    ):
        read_by_the_windows[column] = game_data[column]

    columns = {
        window.column_name: rolling.calculate_rolling_function_column(
            read_by_the_windows,
            window,
            group_by_column=[subject_id_column, situation.label_column]
        )
        for situation in situations
        for window in _windows_of(situation, subject_id_column, stats)
    }

    return pd.concat([game_data, pd.DataFrame(columns, index=game_data.index)], axis=1)
