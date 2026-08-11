"""
One builder per named column, grouped by what each group describes: the schedule, the player, the
team, and the season.

Every builder takes column names rather than assuming them, so the same code builds a player frame
and a team frame. None of them decides which columns a model wants.
"""

import numpy as np
import pandas as pd
from typing import Any

from nba_ml.season import GAME_ID_PREFIXES, SEASON_START_MONTH, SeasonType

def _encode_equality_as_integer(column: pd.Series, value: Any) -> pd.Series:
    """One where the value matches, zero everywhere else."""

    return (column == value).astype(int)

def sort_columns_alphabetically(dataframe: pd.DataFrame) -> pd.DataFrame:
    return dataframe.sort_index(axis=1)

def _column_or_grouped_column(
    dataframe: pd.DataFrame,
    column_name: str,
    group_by_column: str | list[str] | None
    ):
    """
    Returns the column, grouped when a group column is given, so diff and shift stay inside one
    group instead of reading whatever row happens to sit above.
    """

    if group_by_column is None:
        return dataframe[column_name]

    return dataframe.groupby(by=group_by_column, sort=False)[column_name]

REST = 'REST'
BREAK_LENGTH = 'BREAK_LENGTH'
SEASON_OPENER = 'SEASON_OPENER'
CAREER_DEBUT = 'CAREER_DEBUT'
MAX_REST = 7
MAX_BREAK_DAYS = 90
def season_of(game_dates: pd.Series) -> pd.Series:
    """
    The calendar year each game's season started in, which is season.season_of over a whole column.
    The dates must be in datetime form.
    """

    return game_dates.dt.year - (game_dates.dt.month < SEASON_START_MONTH)

def add_break_columns(
    game_data: pd.DataFrame,
    game_date_column: str,
    max_rest: int = MAX_REST,
    max_break_days: int = MAX_BREAK_DAYS,
    group_by_column: str | None = None
    ) -> pd.DataFrame:
    """
    Adds the four columns describing the gap before each game.

    REST is days off capped at max_rest, the range almost every game falls in. BREAK_LENGTH covers
    the whole range as the logarithm of one plus the days off. SEASON_OPENER and CAREER_DEBUT mark
    the two gaps that are not layoffs at all, and a career debut is given the longest gap.

    The given game_data must be sorted by game date, grouped by id, and the game_date column must be
    in datetime form.

    Args:
        group_by_column covers every group in one pass. Without it the frame must hold one group.
    """

    game_dates = game_data[game_date_column]
    groups = None if group_by_column is None else game_data[group_by_column]

    days_since_last_game = _column_or_grouped_column(game_data, game_date_column, group_by_column).diff().dt.days - 1
    days_since_last_game = days_since_last_game.fillna(max_break_days).clip(lower=0, upper=max_break_days)

    season = season_of(game_dates)
    previous_season = season.shift(1) if groups is None else season.groupby(groups, sort=False).shift(1)

    game_data[REST] = days_since_last_game.clip(upper=max_rest)
    game_data[BREAK_LENGTH] = np.log1p(days_since_last_game)
    # A missing previous season only happens on a debut, which counts as opening a season too.
    game_data[SEASON_OPENER] = (season != previous_season).astype(int)
    game_data[CAREER_DEBUT] = previous_season.isna().astype(int)
    return game_data

GAMES_PLAYED = 'GAMES_PLAYED'
def add_games_played_column(
    game_data: pd.DataFrame,
    group_by_column: str
    ) -> pd.DataFrame:
    """
    Counts how many games came before each row, within each group. Rolling columns fill their first
    rows with a set value, so this is what tells a model whether to trust the averages beside it.

    The given game_data must be sorted so that each group runs from oldest to newest.
    """

    game_data[GAMES_PLAYED] = game_data.groupby(by=group_by_column, sort=False).cumcount()
    return game_data

CHANGED_TEAM = 'CHANGED_TEAM'
def add_changed_team_column(
    player_game_data: pd.DataFrame,
    team_id_column: str,
    group_by_column: str | None = None
    ) -> pd.DataFrame:
    """
    The given game_data must be sorted by game date and grouped by player id.

    Args:
        group_by_column covers every group in one pass. Without it the frame must hold one group.
    """

    team_id = player_game_data[team_id_column]
    previous_team_id = _column_or_grouped_column(player_game_data, team_id_column, group_by_column).shift(1)
    player_game_data[CHANGED_TEAM] = ((team_id != previous_team_id) & previous_team_id.notna()).astype(int)
    return player_game_data

POINTS = 'POINTS'
def add_points_column(
    game_data: pd.DataFrame,
    fgm_column: str,
    fg3m_column: str,
    ftm_column: str
    ) -> pd.DataFrame:
    fgm = game_data[fgm_column]
    fg3m = game_data[fg3m_column]
    ftm = game_data[ftm_column]
    game_data[POINTS] = (fgm - fg3m) * 2 + fg3m * 3 + ftm
    return game_data

REBOUNDS = 'REBOUNDS'
def add_total_rebounds_column(
    game_data: pd.DataFrame,
    orb_column: str,
    drb_column: str
    ) -> pd.DataFrame:
    orb = game_data[orb_column]
    drb = game_data[drb_column]
    game_data[REBOUNDS] = orb + drb
    return game_data

POSSESSIONS = 'POSSESSIONS'
def add_possessions_column(
    team_game_data: pd.DataFrame,
    fga_column: str,
    fta_column: str,
    orb_column: str,
    tov_column: str
    ) -> pd.DataFrame:
    fga = team_game_data[fga_column]
    fta = team_game_data[fta_column]
    orb = team_game_data[orb_column]
    tov = team_game_data[tov_column]
    team_game_data[POSSESSIONS] = fga + (0.44 * fta) - orb + tov
    return team_game_data

POINT_DIFFERENTIAL = 'POINT_DIFFERENTIAL'
GAME_TOTAL = 'GAME_TOTAL'
def add_game_result_columns(
    team_game_data: pd.DataFrame,
    points_column: str,
    opponent_points_column: str
    ) -> pd.DataFrame:
    """
    How much the team won or lost the game by, and how many points the two teams scored together.

    Both need the opposing team's points already on the row, so this runs after they are copied over.
    """

    points = team_game_data[points_column]
    opponent_points = team_game_data[opponent_points_column]
    team_game_data[POINT_DIFFERENTIAL] = points - opponent_points
    team_game_data[GAME_TOTAL] = points + opponent_points
    return team_game_data

DIFFERENCE_INFIX = "_DIFF_FROM_"
def get_all_differences_columns(
    stat_columns: list[tuple[str, str]]
    ) -> list[str]:
    return [minuend_column + DIFFERENCE_INFIX + subtrahend_column for minuend_column, subtrahend_column in stat_columns]
def add_differences_columns(
    dataframe: pd.DataFrame,
    stat_columns: list[tuple[str, str]]
) -> pd.DataFrame:
    """Adds one column per pair, holding the first column minus the second."""

    for minuend_column, subtrahend_column in stat_columns:
        dataframe[minuend_column + DIFFERENCE_INFIX + subtrahend_column] = (
            dataframe[minuend_column] - dataframe[subtrahend_column]
        )
    return dataframe

# A value of 0 represents home, and a value of 1 represents away.
HOME_OR_AWAY = 'HOME_OR_AWAY'
HOME = "HOME"
AWAY = "AWAY"
# The raw data writes the away team's game as "ATL @ DET" and the home team's as "DET vs. ATL".
HOME_OR_AWAY_ENCODING = {
    HOME : "vs.",
    AWAY : '@'
}
def add_encoded_home_or_away_column(
    team_game_data: pd.DataFrame,
    matchup_column: str
    ) -> pd.DataFrame:
    matchup = team_game_data[matchup_column]
    home_or_away = pd.Series(index=matchup.index, dtype='Int64')
    home_or_away[matchup.str.contains(HOME_OR_AWAY_ENCODING[AWAY], regex=False, na=False)] = 1
    home_or_away[matchup.str.contains(HOME_OR_AWAY_ENCODING[HOME], regex=False, na=False)] = 0
    team_game_data[HOME_OR_AWAY] = home_or_away
    return team_game_data

PLAYER_SUFFIX = '_PLAYER'
TEAM_SUFFIX = '_TEAM'
def merge_player_team_game_data(
    player_game_data: pd.DataFrame,
    team_game_data: pd.DataFrame,
    game_id_column_team: str,
    game_id_column_player: str,
    team_id_column_team: str,
    team_id_column_player: str,
    duplicate_categories_player: list[str] | None = None,
    ) -> pd.DataFrame:
    """
    Joins each player's game row onto their own team's row for that game.

    Args:
        duplicate_categories_player names player columns the team frame also holds, which are
        dropped rather than suffixed.
    """

    non_duplicate_player_game_data = player_game_data.drop(columns=duplicate_categories_player or [], errors='ignore')

    player_team_game_data: pd.DataFrame = non_duplicate_player_game_data.merge(
        team_game_data,
        left_on=game_id_column_player,
        right_on=game_id_column_team,
        suffixes=(PLAYER_SUFFIX, TEAM_SUFFIX)
        )

    if team_id_column_team == team_id_column_player:
        player_team_game_data = player_team_game_data[
            player_team_game_data[team_id_column_team + PLAYER_SUFFIX]
            == player_team_game_data[team_id_column_player + TEAM_SUFFIX]
            ]

        player_team_game_data = player_team_game_data.drop(columns=team_id_column_player + PLAYER_SUFFIX, errors='ignore')
        player_team_game_data = player_team_game_data.rename(columns={team_id_column_team + TEAM_SUFFIX : team_id_column_player}, errors='ignore')

    else:
        player_team_game_data = player_team_game_data[
            player_team_game_data[team_id_column_team]
            == player_team_game_data[team_id_column_player]
            ]

    return player_team_game_data

OPPONENT_PREFIX = 'OPP_'
def add_opponent_stat_columns(
    team_game_data: pd.DataFrame,
    game_id_column: str,
    team_id_column: str,
    columns_to_copy: list[str]
    ) -> pd.DataFrame:
    """
    Adds the other team's stats to each row under the opponent prefix.

    Only columns_to_copy are copied. This frame is the widest in the pipeline, so copying all of it
    would roughly double the peak memory for columns that are never read back. The team id is always
    copied, because it is what pairs the two rows of a game up.

    Calling this again replaces what an earlier call copied rather than colliding with it, which is
    what lets a build copy raw stats, roll windows over them, and then copy those windows too.
    """

    opponent_columns = [team_id_column] + [column for column in columns_to_copy if column != team_id_column]
    copied_column_names = {column: OPPONENT_PREFIX + column for column in opponent_columns}
    opponent_stats = team_game_data[[game_id_column] + opponent_columns].rename(columns=copied_column_names)

    merged = team_game_data.drop(columns=list(copied_column_names.values()), errors='ignore').merge(
        opponent_stats, on=game_id_column
    )
    return merged[merged[team_id_column] != merged[OPPONENT_PREFIX + team_id_column]]

TEAM_GAME_NUMBER = "TEAM_GAME_NUMBER"
def number_team_games(
    team_game_data: pd.DataFrame,
    game_id_column: str,
    team_id_column: str,
    game_date_column: str
    ) -> pd.DataFrame:
    """
    Returns each team's games numbered from its first, so that "the game before this one" becomes a
    subtraction and the comparisons built on it become joins.

    The date column must be in datetime form. The frame need not be sorted.
    """

    team_games = team_game_data[[game_id_column, team_id_column, game_date_column]].sort_values(
        by=[team_id_column, game_date_column]
    )
    team_games[TEAM_GAME_NUMBER] = team_games.groupby(by=team_id_column, sort=False).cumcount()
    return team_games

TEAM_GAMES_MISSED = 'TEAM_GAMES_MISSED'
RECENT_AVAILABILITY = 'RECENT_AVAILABILITY'
ALL_AVAILABILITY_COLUMNS = [TEAM_GAMES_MISSED, RECENT_AVAILABILITY]
AVAILABILITY_WINDOW = 10
MAX_TEAM_GAMES_MISSED = 15
def add_availability_columns(
    player_game_data: pd.DataFrame,
    team_game_data: pd.DataFrame,
    player_id_column: str,
    game_id_column_player: str,
    team_id_column_player: str,
    game_id_column_team: str,
    team_id_column_team: str,
    game_date_column_team: str,
    window: int = AVAILABILITY_WINDOW,
    max_games_missed: int = MAX_TEAM_GAMES_MISSED
    ) -> pd.DataFrame:
    """
    Adds how much of their team's recent schedule the player has been available for. Rest only sees
    the gap in days, so a player in and out of the lineup reads as well rested without these.

    TEAM_GAMES_MISSED is how many games the team played since the player last appeared for them.
    RECENT_AVAILABILITY is the share of its games the player played over their last window
    appearances. Both are unknown until the player has a history with the team, and an unknown reads
    as fully available.

    Neither frame needs to be sorted. team_game_data supplies the order of a team's games and needs
    its date column in datetime form.
    """

    numbered = number_team_games(
        team_game_data, game_id_column_team, team_id_column_team, game_date_column_team
    ).rename(columns={game_id_column_team: game_id_column_player, team_id_column_team: team_id_column_player})

    appearances = player_game_data[[player_id_column, game_id_column_player, team_id_column_player]].merge(
        numbered, on=[game_id_column_player, team_id_column_player], how='left'
    )
    appearances.index = player_game_data.index
    appearances = appearances.sort_values(by=[player_id_column, team_id_column_player, TEAM_GAME_NUMBER])

    spell = appearances.groupby(by=[player_id_column, team_id_column_player], sort=False)[TEAM_GAME_NUMBER]
    game_number = appearances[TEAM_GAME_NUMBER]

    missed = (game_number - spell.shift(1) - 1).fillna(0).clip(lower=0, upper=max_games_missed)
    # Games the team played across the player's last window appearances. Equal to the window when
    # they played every one of them, and larger by however many they sat out.
    played_over = game_number - spell.shift(window)

    player_game_data[TEAM_GAMES_MISSED] = missed.reindex(player_game_data.index)
    player_game_data[RECENT_AVAILABILITY] = (
        (window / played_over).clip(upper=1.0).fillna(1.0).reindex(player_game_data.index)
    )
    return player_game_data

RECENT_GAME_COUNT_PREFIX = 'GAMES_IN_LAST_'
RECENT_GAME_COUNT_DAYS = (7, 14)
def get_recent_game_count_columns(day_counts: tuple[int, ...] = RECENT_GAME_COUNT_DAYS) -> list[str]:
    return [f"{RECENT_GAME_COUNT_PREFIX}{days}_DAYS" for days in day_counts]
def add_recent_game_count_columns(
    game_data: pd.DataFrame,
    game_date_column: str,
    group_by_column: str,
    day_counts: tuple[int, ...] = RECENT_GAME_COUNT_DAYS
    ) -> pd.DataFrame:
    """
    Adds how many games came before each one within the given number of days, not counting itself.
    Rest only measures the last gap, so three games in five nights reads the same as one without it.

    The frame need not be sorted, but its row labels must be unique and the date column must be in
    datetime form.
    """

    COUNTED = "COUNTED"

    # Sorted here rather than demanded of the caller, because a time based window has to read a
    # group in date order and the grouped result comes back in whatever order the groups were met.
    ordered = game_data[[group_by_column, game_date_column]].sort_values(
        by=[group_by_column, game_date_column]
    )
    ordered[COUNTED] = 1
    grouped = ordered.groupby(by=group_by_column, sort=False)

    columns = {}
    for days, column_name in zip(day_counts, get_recent_game_count_columns(day_counts)):
        within_days = grouped.rolling(f"{days}D", on=game_date_column)[COUNTED].count().to_numpy()
        columns[column_name] = pd.Series(within_days - 1, index=ordered.index).reindex(game_data.index)

    return pd.concat([game_data, pd.DataFrame(columns, index=game_data.index)], axis=1)

GAINED_CORE_TEAMMATE_PREFIX = "GAINED_CORE_TEAMMATE_"
LOST_CORE_TEAMMATE_PREFIX = "LOST_CORE_TEAMMATE_"
ABSENT_CORE_TEAMMATE_PREFIX = "ABSENT_CORE_TEAMMATE_"
CORE_PLAYER_MINUTES_CUTOFF = 25
CORE_ROTATION_WINDOW = 10
def get_core_teammate_columns(stat_columns: list[str]) -> list[str]:
    return [
        prefix + column
        for prefix in (GAINED_CORE_TEAMMATE_PREFIX, LOST_CORE_TEAMMATE_PREFIX, ABSENT_CORE_TEAMMATE_PREFIX)
        for column in stat_columns
    ]
def add_core_teammate_columns(
    player_game_data: pd.DataFrame,
    team_game_data: pd.DataFrame,
    player_id_column: str,
    game_id_column_player: str,
    team_id_column_player: str,
    minutes_played_column: str,
    recent_minutes_column: str,
    game_id_column_team: str,
    team_id_column_team: str,
    game_date_column_team: str,
    stat_columns: list[str],
    rotation_window: int = CORE_ROTATION_WINDOW
    ) -> pd.DataFrame:
    """
    Adds, per player game, three readings of the players around them, each totalled over
    stat_columns. Those columns should hold what a player was averaging going into the game rather
    than what they did in it, so a total says what the team has, not what it got.

    Gained and lost compare this game's roster to the previous one, and leave the player's own
    numbers out of their own row. Absent is the shortfall against what the team normally has
    available over its last rotation_window games, which is what carries a star's whole absence
    rather than only the first game of it.

    Args:
        minutes_played_column decides who was core in a game that was played.
        recent_minutes_column decides who counts as core when only a roster is known, which is what
        a prediction has, so absent reads the same during training and during a prediction.

    team_game_data supplies the order of a team's games and needs its date column in datetime form.
    Neither frame needs to be sorted.
    """

    FOUND = "FOUND_IN_OTHER_GAME"

    team_games = number_team_games(
        team_game_data, game_id_column_team, team_id_column_team, game_date_column_team
    ).rename(columns={game_id_column_team: game_id_column_player, team_id_column_team: team_id_column_player})
    every_team_game = pd.MultiIndex.from_frame(team_games[[team_id_column_player, TEAM_GAME_NUMBER]])

    roster_columns = [player_id_column, team_id_column_player, minutes_played_column, recent_minutes_column]
    roster_columns += [column for column in stat_columns if column not in roster_columns]

    roster = player_game_data[roster_columns].copy()
    roster[TEAM_GAME_NUMBER] = (
        team_games.set_index([game_id_column_player, team_id_column_player])[TEAM_GAME_NUMBER]
        .reindex(pd.MultiIndex.from_arrays([
            player_game_data[game_id_column_player],
            player_game_data[team_id_column_player]
        ]))
        .to_numpy()
    )
    roster = roster.dropna(subset=[TEAM_GAME_NUMBER])
    roster[TEAM_GAME_NUMBER] = roster[TEAM_GAME_NUMBER].astype(np.int64)

    keys = [team_id_column_player, player_id_column, TEAM_GAME_NUMBER]
    core = roster[roster[minutes_played_column] >= CORE_PLAYER_MINUTES_CUTOFF]
    team_key = pd.MultiIndex.from_arrays([roster[team_id_column_player], roster[TEAM_GAME_NUMBER]])

    def keyed_to_next_game(rows: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        """The given rows, renumbered so they line up with the game that came after them."""

        rows = rows[keys + columns].copy()
        rows[TEAM_GAME_NUMBER] += 1
        return rows

    def missing_from(rows: pd.DataFrame, other_game: pd.DataFrame) -> pd.DataFrame:
        found = other_game[keys].assign(**{FOUND: True})
        merged = rows.merge(found, on=keys, how='left')
        return merged[merged[FOUND].isna()]

    def totals_per_game(rows: pd.DataFrame) -> pd.DataFrame:
        return rows.groupby(by=[team_id_column_player, TEAM_GAME_NUMBER], sort=False)[stat_columns].sum()

    gained = missing_from(core[keys + stat_columns], keyed_to_next_game(roster, []))
    lost = missing_from(keyed_to_next_game(core, stat_columns), roster)

    own_gained = gained.set_index(keys)[stat_columns].reindex(pd.MultiIndex.from_frame(roster[keys])).fillna(0)

    # Every team game in order, so a team's rolling level below reads consecutive games even when a
    # game had nobody the roster counts as core.
    present = totals_per_game(roster[roster[recent_minutes_column] >= CORE_PLAYER_MINUTES_CUTOFF])
    present = present.reindex(every_team_game).fillna(0.0).sort_index()
    usual = (
        present.groupby(level=team_id_column_player, sort=False).shift(1)
        .groupby(level=team_id_column_player, sort=False)
        .rolling(rotation_window, min_periods=1)
        .mean()
        .reset_index(level=0, drop=True)
    )
    absent = (usual - present).clip(lower=0)

    columns = pd.DataFrame(
        np.hstack([
            totals_per_game(gained).reindex(team_key).fillna(0).to_numpy() - own_gained.to_numpy(),
            totals_per_game(lost).reindex(team_key).fillna(0).to_numpy(),
            absent.reindex(team_key).fillna(0).to_numpy()
        ]),
        index=roster.index,
        columns=get_core_teammate_columns(stat_columns)
    )

    return pd.concat([player_game_data, columns.reindex(player_game_data.index, fill_value=0.0)], axis=1)

def _add_years_between_static_player_event_and_game_column(
    game_data: pd.DataFrame,
    player_info: pd.DataFrame,
    player_id_column_player_info: str,
    player_id_column_game_data: str,
    static_player_event_time_column: str,
    game_date_column: str,
    new_column_name: str,
    ) -> pd.DataFrame:
    """
    Adds the years between a date held once per player, such as their birthdate, and each game they
    played. Both date columns must be in datetime form.
    """

    TEMP = 'TEMP'
    player_id_to_static_event_time = player_info.set_index(player_id_column_player_info)[static_player_event_time_column].to_dict()
    game_data[TEMP] = game_data[player_id_column_game_data].map(player_id_to_static_event_time, na_action='ignore')
    game_data[new_column_name] = ((game_data[game_date_column] - game_data[TEMP]).dt.days / 365.25).astype(float)
    game_data = game_data.drop(columns=TEMP)
    return game_data

AGE_DURING_GAME = 'AGE_DURING_GAME'
def add_age_during_game_column(
    game_data: pd.DataFrame,
    player_info: pd.DataFrame,
    player_id_column_player_info: str,
    player_id_column_game_data: str,
    birthdate_column: str,
    game_date_column: str
    ) -> pd.DataFrame:
    """
    The birthdate and game_date columns must be represented in datetime form.
    """

    return _add_years_between_static_player_event_and_game_column(
        game_data,
        player_info,
        player_id_column_player_info,
        player_id_column_game_data,
        birthdate_column,
        game_date_column,
        AGE_DURING_GAME
    )

NBA_EXPERIENCE_DURING_GAME = 'NBA_EXPERIENCE_DURING_GAME'
def add_years_NBA_experience_during_game_column(
    game_data: pd.DataFrame,
    player_info: pd.DataFrame,
    player_id_column_player_info: str,
    player_id_column_game_data: str,
    date_entered_league_column: str,
    game_date_column: str
    ) -> pd.DataFrame:
    """
    The date_entered_league and game_date columns must be represented in datetime form.
    """

    return _add_years_between_static_player_event_and_game_column(
        game_data,
        player_info,
        player_id_column_player_info,
        player_id_column_game_data,
        date_entered_league_column,
        game_date_column,
        NBA_EXPERIENCE_DURING_GAME
    )

### SEASON TYPES: A value of 1 represents True, and a value of 0 represents False. ###
# One name per season phase, taken from the shared enum so a prediction can name the phase of the
# game it is asking about without a translation table.
PRESEASON = SeasonType.PRESEASON.value
REGULAR_SEASON = SeasonType.REGULAR_SEASON.value
PLAYOFFS = SeasonType.PLAYOFFS.value
PLAY_IN = SeasonType.PLAY_IN.value
ALL_SEASON_TYPES = [
    PRESEASON,
    REGULAR_SEASON,
    PLAYOFFS,
    PLAY_IN
]
SEASON_ENCODINGS = {
    season_type.value : prefix
    for season_type, prefix in GAME_ID_PREFIXES.items()
}
def add_encoded_season_type_columns(
    team_game_data: pd.DataFrame,
    game_id_column: str
    ) -> pd.DataFrame:
    """
    The season type is the third character of a game id such as "0022300001". Reading the first
    character works only because the id is stored as a number, which drops the two leading zeros.
    Storing game ids as text would silently break this.
    """

    season_type_id = team_game_data[game_id_column].astype(str).str[0]

    for season_type in ALL_SEASON_TYPES:
        team_game_data[season_type] = _encode_equality_as_integer(season_type_id, SEASON_ENCODINGS[season_type])

    return team_game_data

def encode_win_loss_column_as_integer(
    game_data: pd.DataFrame,
    win_loss_column: str
    ) -> pd.DataFrame:
    """Rewrites the win/loss column as one for a win and zero for a loss."""

    game_data[win_loss_column] = _encode_equality_as_integer(game_data[win_loss_column], "W")
    return game_data

SEASON_GAME_NUMBER = 'SEASON_GAME_NUMBER'
DAYS_INTO_SEASON = 'DAYS_INTO_SEASON'
TEAM_WIN_PERCENTAGE = 'TEAM_WIN_PERCENTAGE'
ALL_SEASON_CONTEXT_COLUMNS = [SEASON_GAME_NUMBER, DAYS_INTO_SEASON, TEAM_WIN_PERCENTAGE]
EVEN_RECORD = 0.5
def add_season_standings_columns(
    team_game_data: pd.DataFrame,
    game_date_column: str,
    team_id_column: str,
    won_column: str,
    regular_season_column: str
    ) -> pd.DataFrame:
    """
    Adds how far into its season each team game sits and how the team's season is going.

    SEASON_GAME_NUMBER and DAYS_INTO_SEASON place the game in the season. TEAM_WIN_PERCENTAGE says
    how much the game is still worth to the team, which separates a contender resting a star from an
    eliminated team handing minutes to its bench.

    Only regular season games count towards the record, and a game never counts itself. A playoff
    game therefore reads the record the team finished the regular season on, and a preseason game
    reads an even one.

    The given team_game_data must be sorted by game date, grouped by team id, with the date column
    in datetime form and the won column already encoded as 1 for a win.
    """

    game_dates = team_game_data[game_date_column]
    team_and_season = [team_game_data[team_id_column], season_of(game_dates)]
    played = team_game_data[regular_season_column]
    won = team_game_data[won_column] * played

    def totalled_before(counted: pd.Series) -> pd.Series:
        """Exclusive, so a game is never part of the record it is measured against."""

        return counted.groupby(team_and_season, sort=False).cumsum() - counted

    games_played = totalled_before(played)
    team_game_data[SEASON_GAME_NUMBER] = games_played
    team_game_data[TEAM_WIN_PERCENTAGE] = (totalled_before(won) / games_played).fillna(EVEN_RECORD)
    team_game_data[DAYS_INTO_SEASON] = (
        game_dates - game_dates.groupby(team_and_season, sort=False).transform('min')
    ).dt.days
    return team_game_data

def convert_height_to_inches(
    player_info: pd.DataFrame,
    height_column: str,
    fill_unknown_with_mean: bool = False
    ) -> pd.DataFrame:
    """Rewrites a height written as feet-inches, such as 6-7, as a number of inches."""

    heights_split = player_info[height_column].str.split("-", expand=True)
    feet = pd.to_numeric(heights_split[0], errors="coerce")
    inches = pd.to_numeric(heights_split[1], errors="coerce")
    player_info[height_column] = feet * 12 + inches

    if fill_unknown_with_mean:
        player_info[height_column] = player_info[height_column].fillna(player_info[height_column].mean())

    return player_info

def handle_unknown_weight(
    player_info: pd.DataFrame,
    weight_column: str,
    fill_unknown_with_mean: bool = False
    ) -> pd.DataFrame:
    """Makes the weight column a number, since an unknown weight arrives as empty text."""

    player_info[weight_column] = pd.to_numeric(player_info[weight_column], errors='coerce')

    if fill_unknown_with_mean:
        player_info[weight_column] = player_info[weight_column].fillna(player_info[weight_column].mean())

    return player_info

UNDRAFTED = 'Undrafted'
def encode_undrafted(
    player_info: pd.DataFrame,
    draft_number_column: str,
    ) -> pd.DataFrame:
    draft_number = player_info[draft_number_column]
    player_info[UNDRAFTED] = _encode_equality_as_integer(draft_number, UNDRAFTED)
    player_info[draft_number_column] = pd.to_numeric(player_info[draft_number_column].replace(UNDRAFTED, '0'))
    return player_info
