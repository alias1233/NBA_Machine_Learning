"""
How a subject has done in games like the one being predicted.

Every model here already reads recent form and the order of the games behind it. What none of them
can easily work out is whether this particular kind of game changes what a subject does: a player
who disappears against one team, one who sits out preseason, one who is a different player away
from home. A sequence carries that information in principle, but only as a mark on a handful of the
fifty games it reads, which is a lot to ask a running memory to hold onto.

A situation is one thing about a game that earlier games can be grouped by. For each of them a
subject carries two columns: how far above or below its own running average it landed in its last
games of that kind, and how many such games there were. Zero means nothing unusual, which is what a
subject with no such games behind it also reads as, and the count is what tells those two apart.

Every column here is exclusive, like every other rolling column in this package, so a row only ever
holds what was known before it and a game not yet played is built the same way as one already
played.
"""

from dataclasses import dataclass
from typing import Sequence

import pandas as pd

from nba_ml.feature_engineering import game_columns, rolling
from nba_ml.feature_engineering.rolling import RollingCategory
from nba_ml.stores import team_games

@dataclass(frozen=True)
class Situation():
    """One thing about a game that a subject's earlier games can be grouped by."""

    name: str
    """Names the columns this situation produces."""

    label_column: str
    """The column whose value decides which earlier games count as the same kind of game."""

    window: int
    """How many of the most recent games of this kind are read."""

@dataclass(frozen=True)
class SituationalStat():
    """One statistic to read in a situation, and what counts as ordinary for it."""

    name: str
    """Names the columns this statistic produces, which is the stat in the words a reader knows."""

    value_column: str
    expectation_column: str
    """What the subject was averaging going into a game, which the value is measured against."""

FORM_PREFIX = "FORM_"
GAMES_PREFIX = "GAMES_"
OVER_EXPECTED_PREFIX = "OVER_EXPECTED_"
"""Names the working column a form column averages: one game's value, less what was expected of it."""

# A different opponent every few weeks, so ten reaches back about three seasons and no further than
# a roster that still resembles the one playing. The other two recur constantly, and the reason to
# read them at all is a phase or a side that only comes around a few times a year, so both reach
# further back.
AGAINST_THIS_OPPONENT = Situation(
    "AGAINST_THIS_OPPONENT",
    game_columns.OPPONENT_PREFIX + team_games.TEAM_ID.category_name,
    10
)
IN_THIS_SEASON_TYPE = Situation("IN_THIS_SEASON_TYPE", game_columns.SEASON_TYPE, 20)
AT_HOME_OR_AWAY = Situation("AT_HOME_OR_AWAY", game_columns.HOME_OR_AWAY, 20)

ALL_SITUATIONS = [AGAINST_THIS_OPPONENT, IN_THIS_SEASON_TYPE, AT_HOME_OR_AWAY]
"""
Every situation defined here. Both builds can read any of them, since both are one subject per game
and the opponent's team id column is named the same way in either.

Which of them a family actually reads is that family's own answer, measured rather than assumed, so
each names its own list rather than taking this one.
"""

def form_column(situation: Situation, stat: SituationalStat) -> str:
    return f"{FORM_PREFIX}{situation.name}_{stat.name}"

def games_column(situation: Situation) -> str:
    return f"{GAMES_PREFIX}{situation.name}"

def all_columns(
    situations: Sequence[Situation],
    stats: Sequence[SituationalStat]
    ) -> list[str]:
    """Every column add_columns produces, so a model can list what it reads without building it."""

    return [
        form_column(situation, stat) for situation in situations for stat in stats
    ] + [
        games_column(situation) for situation in situations
    ]

def add_columns(
    game_data: pd.DataFrame,
    subject_id_column: str,
    situations: Sequence[Situation],
    stats: Sequence[SituationalStat]
    ) -> pd.DataFrame:
    """
    Adds every situational column to a frame of one row per subject per game.

    The frame must be sorted so that each subject's games sit in the order they happened, and must
    already hold each situation's label column and each statistic's value and expectation.

    The working columns each form column is averaged from are left on the frame rather than dropped,
    because dropping them copies the whole frame for no gain.
    """

    if not situations or not stats:
        return game_data

    # A subject's first game has nothing to expect anything of it, and its recent average reads as
    # zero, so the whole statistic would land in the difference. Left blank, it is skipped by the
    # means below rather than dragging every reading built on it.
    first_game = game_data.groupby(by=subject_id_column, sort=False).cumcount() == 0
    over_expected = pd.DataFrame(
        {
            OVER_EXPECTED_PREFIX + stat.name: (
                game_data[stat.value_column] - game_data[stat.expectation_column]
            )
            for stat in stats
        },
        index=game_data.index
    ).mask(first_game)

    game_data = pd.concat([game_data, over_expected], axis=1)

    for situation in situations:
        game_data = rolling.add_rolling_function_columns(
            game_data,
            [
                RollingCategory(
                    form_column(situation, stat),
                    OVER_EXPECTED_PREFIX + stat.name,
                    rolling.MEAN_FUNCTION,
                    situation.window
                )
                for stat in stats
            ] + [
                # Counted off the subject's own id, which is never blank, so this is simply how many
                # games of this kind sit behind the row, capped at the window.
                RollingCategory(
                    games_column(situation),
                    subject_id_column,
                    rolling.COUNT_FUNCTION,
                    situation.window
                )
            ],
            group_by_column=[subject_id_column, situation.label_column]
        )

    return game_data
