import pandas as pd
from typing import Any

def _encode_equality_as_integer(column: pd.Series, value: Any) -> pd.Series:
    """
    Returns a series where each value is 1 if the value corresponding to the given series equals the given string, and 0 otherwise.  
    """

    return (column == value).astype(int)

def sort_columns_alphabetically(dataframe: pd.DataFrame) -> pd.DataFrame:
    return dataframe.sort_index(axis=1)

def create_lookup_table(
    dataframe: pd.DataFrame,
    key_column: str
    ) -> dict[Any, pd.DataFrame]:
    lookup_table = {}
    for key, data in dataframe.groupby(by=key_column, sort=False):
        lookup_table[key] = data
    return lookup_table

REST = 'REST'
LONG_BREAK = 'LONG_BREAK'
def add_rest_and_long_break_columns(
    game_data: pd.DataFrame, 
    game_date_column: str,
    max_rest: int = 7,
    long_break_threshold: int = 25
    ) -> pd.DataFrame:
    """
    Adds rest and long break columns to the given game_data. 
    The given game_data must be sorted by game date, grouped by id, and the game_date column must be in datetime form.
    The value of rest is clamped to MAX_REST.
    If it is the first game that has ever been played, the value for 'rest' will be MAX_REST.
    Long break is set to 1 if the player has not played a game in more than or equal to LONG_BREAK_THRESHOLD days, and 0 otherwise.
    """

    game_data[REST] = (game_data[game_date_column].diff().dt.days - 1).fillna(long_break_threshold)
    game_data[LONG_BREAK] = (game_data[REST] >= long_break_threshold).astype(int)
    game_data[REST] = game_data[REST].clip(upper=max_rest)
    return game_data

DAYS_BEFORE_LAST_GAME = 'DAYS_BEFORE_LAST_GAME'
def add_days_between_games_columns(
    game_data: pd.DataFrame, 
    game_date_column: str,
    max_interval: int = 100
    ) -> pd.DataFrame:
    """
    Adds days before last game columns to the given game_data. 
    The given game_data must be sorted by game date, grouped by id, and the game_date column must be in datetime form.
    If it is the first game that has ever been played, the value will be max_interval.
    """

    game_data[DAYS_BEFORE_LAST_GAME] = (game_data[game_date_column].diff().dt.days - 1).fillna(max_interval).clip(upper=max_interval)
    return game_data

CHANGED_TEAM = 'CHANGED_TEAM'
def add_changed_team_column(
    player_game_data: pd.DataFrame,
    team_id_column: str
    ) -> pd.DataFrame:
    """
    The given game_data must be sorted by game date and grouped by player id.
    """

    team_id = player_game_data[team_id_column]
    previous_team_id = team_id.shift(1)
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

def _add_percentage_column(
    dataframe: pd.DataFrame,
    part_column: str,
    whole_column: str,
    new_column_name: str
    ) -> pd.DataFrame:
    part = dataframe[part_column]
    whole = dataframe[whole_column]
    dataframe[new_column_name] = part.div(whole, fill_value=0)
    return dataframe

FIELD_GOAL_PERCENTAGE = 'FIELD_GOAL_PERCENTAGE'
def add_field_goal_percentage_column(
    game_data: pd.DataFrame,
    fgm_column: str,
    fga_column: str
    ) -> pd.DataFrame:
    return _add_percentage_column(game_data, fgm_column, fga_column, FIELD_GOAL_PERCENTAGE)

THREE_POINT_PERCENTAGE = 'THREE_POINT_PERCENTAGE'
def add_three_point_percentage_column(
    game_data: pd.DataFrame,
    fg3m_column: str,
    fg3a_column: str
    ) -> pd.DataFrame:
    return _add_percentage_column(game_data, fg3m_column, fg3a_column, THREE_POINT_PERCENTAGE)

TRUE_SHOOTING_PERCENTAGE = 'TRUE_SHOOTING_PERCENTAGE'
def add_true_shooting_percentage_column(
    game_data: pd.DataFrame,
    points_column: str,
    fga_column: str,
    fta_column: str
    ) -> pd.DataFrame:
    points = game_data[points_column]
    fga = game_data[fga_column]
    fta = game_data[fta_column]
    game_data[TRUE_SHOOTING_PERCENTAGE] = points.div(2 * (fga + 0.44 * fta), fill_value=0)
    return game_data

PER_INFIX = "_PER_"
def get_all_stat_per_stat_columns(
    part_stat_columns: list[str],
    whole_stat_columns: list[str]
    ) -> list[str]:
    return [
        part_stat_column + PER_INFIX + whole_stat_column
        for part_stat_column in part_stat_columns
        for whole_stat_column in whole_stat_columns
    ]
def add_stat_per_stat_columns(
    dataframe: pd.DataFrame,
    part_stat_columns: list[str],
    whole_stat_columns: list[str]
    ) -> pd.DataFrame:
    for part_stat_column in part_stat_columns:
        for whole_stat_column in whole_stat_columns:
            dataframe = _add_percentage_column(
                dataframe,
                part_stat_column,
                whole_stat_column,
                part_stat_column + PER_INFIX + whole_stat_column
            )

    return dataframe

DIFFERENCE_INFIX = "_DIFF_FROM_"
def get_all_differences_columns(
    stat_columns: list[tuple[str, str]]
    ) -> list[str]:
    return [minuend_column + DIFFERENCE_INFIX + subtrahend_column for minuend_column, subtrahend_column in stat_columns]
def add_differences_columns(
    dataframe: pd.DataFrame,
    stat_columns: list[tuple[str, str]]
) -> pd.DataFrame:
    """
    For each entry in stat_columns, add a column containing the difference between the first column and the second column.
    """
    
    for minuend_column, subtrahend_column in stat_columns:
        dataframe[minuend_column + DIFFERENCE_INFIX + subtrahend_column] = (
            dataframe[minuend_column] - dataframe[subtrahend_column]
        )
    return dataframe

# A value of 0 represents home, and a value of 1 represents away.
HOME_OR_AWAY = 'HOME_OR_AWAY'
def add_encoded_home_or_away_column(
    team_game_data: pd.DataFrame, 
    matchup_column: str
    ) -> pd.DataFrame:
    matchup = team_game_data[matchup_column]
    home_or_away = pd.Series(index=matchup.index, dtype='Int64')
    home_or_away[matchup.str.contains('@', regex=False, na=False)] = 1
    home_or_away[matchup.str.contains('vs.', regex=False, na=False)] = 0
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
    duplicate_categories_player: list[str] = [],
    ) -> pd.DataFrame:

    non_duplicate_player_game_data = player_game_data.drop(columns=duplicate_categories_player, errors='ignore')

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

def merge_player_game_info_data(
    player_game_data: pd.DataFrame,
    player_info_data: pd.DataFrame,
    player_id_column_game: str,
    player_id_column_info: str
    ) -> pd.DataFrame:
    return player_game_data.merge(right=player_info_data, left_on=player_id_column_game, right_on=player_id_column_info)

OPPONENT_PREFIX = 'OPP_'
def add_opponent_stat_columns(
    team_game_data: pd.DataFrame, 
    game_id_column: str, 
    team_id_column: str,
    duplicate_categories: list[str] = []
    ) -> pd.DataFrame:
    opponent_stats = team_game_data.copy()

    if duplicate_categories:
        opponent_stats = opponent_stats.drop(columns=duplicate_categories, errors='ignore')

    opponent_column_names = {}
    for column_name in opponent_stats.columns:
        opponent_column_name = column_name
        if column_name != game_id_column:
            opponent_column_name = OPPONENT_PREFIX + opponent_column_name
        opponent_column_names[column_name] = opponent_column_name

    opponent_stats = opponent_stats.rename(columns=opponent_column_names)

    merged = team_game_data.merge(opponent_stats, on=game_id_column)
    merged = merged[merged[team_id_column] != merged[OPPONENT_PREFIX + team_id_column]]
    return merged

STATS_BASED_ON_ATTRIBUTE_SUFFIX = "_BY_"
def get_all_stats_by_attribute_columns(
    attribute_columns: list[str],
    stat_columns: list[str]
    ) -> list[str]:
    return [
        stat + STATS_BASED_ON_ATTRIBUTE_SUFFIX + attribute 
        for stat in stat_columns 
        for attribute in attribute_columns
    ]   
def add_total_player_stats_per_game_by_attribute(
    team_game_data: pd.DataFrame,
    player_game_data: pd.DataFrame,
    player_info: pd.DataFrame,
    player_id_column_info: str,
    player_id_column_player: str,
    game_id_column: str,
    team_id_column: str,
    attribute_columns: list[str],
    stat_columns: list[str]
    ) -> pd.DataFrame:
    """
    Adds columns corresponding to the total stats of every player with the given attribute of each game to the team game dataframe.

    THe attribute column must be a hot encoded column in player_info, 
    where every value at each row index is 0 or 1 corresponding to whether the player has that attribute.
    """

    for attribute_column in attribute_columns:
        player_ids_with_attribute = player_info[player_info[attribute_column] == 1][player_id_column_info].unique()
        player_game_data_with_attribute = (
            player_game_data[player_game_data[player_id_column_player].isin(player_ids_with_attribute)]
        )

        total_player_stats_in_game_by_attribute = (
            player_game_data_with_attribute.groupby(
                by=[game_id_column, team_id_column], sort=False)
                [stat_columns]
                .sum()
                .reset_index()
                )
        
        rename_map = {
            stat: stat + STATS_BASED_ON_ATTRIBUTE_SUFFIX + attribute_column
            for stat in stat_columns
        }
        total_player_stats_in_game_by_attribute = total_player_stats_in_game_by_attribute.rename(columns=rename_map)
        
        team_game_data = (
            team_game_data
            .merge(
                total_player_stats_in_game_by_attribute, 
                on=[game_id_column, team_id_column], 
                how='left'
                )
                .fillna(0)
                )

    return team_game_data

OVER_BUCKET_BOUNDARY_PREFIX = "_OVER_"
BETWEEN_BUCKET_BOUNDARY_PREFIX = "_BETWEEN_"
BETWEEN_SPACE = "_"
UNDER_BUCKET_BOUNDARY_PREFIX = "_UNDER_"
def get_all_stats_by_bucket_columns(
    bucket_column: str,
    bucket_boundaries: list[float],
    stat_columns: list[str]
    ) -> list[str]:
    temp_attribute_columns: list[str] = []
    lower_bucket_boundary: float | None = None
    for upper_bucket_boundary in bucket_boundaries:
        temp_attribute_column: str = ""
        if lower_bucket_boundary is None:
            temp_attribute_column = bucket_column + UNDER_BUCKET_BOUNDARY_PREFIX + str(upper_bucket_boundary)

        else:
            temp_attribute_column = bucket_column + BETWEEN_BUCKET_BOUNDARY_PREFIX + str(lower_bucket_boundary) + BETWEEN_SPACE + str(upper_bucket_boundary)
        
        lower_bucket_boundary = upper_bucket_boundary
        temp_attribute_columns.append(temp_attribute_column)

    temp_attribute_column = bucket_column + OVER_BUCKET_BOUNDARY_PREFIX + str(lower_bucket_boundary)
    temp_attribute_columns.append(temp_attribute_column)

    return get_all_stats_by_attribute_columns(
        temp_attribute_columns,
        stat_columns
    )

def add_total_player_stats_per_game_by_bucket(
    team_game_data: pd.DataFrame,
    player_game_data: pd.DataFrame,
    player_info: pd.DataFrame,
    player_id_column_info: str,
    player_id_column_player: str,
    game_id_column: str,
    team_id_column: str,
    bucket_column: str,
    bucket_boundaries: list[float],
    stat_columns: list[str]
    ) -> pd.DataFrame:

    temp_player_info = player_info.copy()

    bucket = temp_player_info[bucket_column]

    temp_attribute_columns: list[str] = []
    lower_bucket_boundary: float | None = None
    for upper_bucket_boundary in bucket_boundaries:
        temp_attribute_column: str = ""
        if lower_bucket_boundary is None:
            temp_attribute_column = bucket_column + UNDER_BUCKET_BOUNDARY_PREFIX + str(upper_bucket_boundary)
            temp_player_info[temp_attribute_column] = (bucket < upper_bucket_boundary).astype(int)

        else:
            temp_attribute_column = bucket_column + BETWEEN_BUCKET_BOUNDARY_PREFIX + str(lower_bucket_boundary) + BETWEEN_SPACE + str(upper_bucket_boundary)
            temp_player_info[temp_attribute_column] = ((bucket < upper_bucket_boundary) & (bucket >= lower_bucket_boundary)).astype(int)
        
        lower_bucket_boundary = upper_bucket_boundary
        temp_attribute_columns.append(temp_attribute_column)

    temp_attribute_column = bucket_column + OVER_BUCKET_BOUNDARY_PREFIX + str(lower_bucket_boundary)
    temp_player_info[temp_attribute_column] = (bucket >= lower_bucket_boundary).astype(int)
    temp_attribute_columns.append(temp_attribute_column)

    team_game_data = add_total_player_stats_per_game_by_attribute(
        team_game_data,
        player_game_data,
        temp_player_info,
        player_id_column_info,
        player_id_column_player,
        game_id_column,
        team_id_column,
        temp_attribute_columns,
        stat_columns
    )

    return team_game_data

ROSTER_ADD_CORE_PLAYER = "ROSTER_ADD_CORE_PLAYER"
ROSTER_REMOVE_CORE_PLAYER = "ROSTER_REMOVE_CORE_PLAYER"
def add_core_roster_change_columns(
    team_game_data: pd.DataFrame,
    player_game_data: pd.DataFrame,
    player_id_column: str,
    game_id_column_player: str,
    game_id_column_team: str,
    team_id_column_player: str,
    team_id_column_team: str,
    minutes_played_column: str, # TODO: Potentially use previous rolling mean minutes played
    core_player_minutes_cutoff: int = 25
    ) -> pd.DataFrame:
    """
    Adds columns to team_game_data that encode whether the team completely gained a core player or completely lost a core player from the previous game.
    """

    PREV_PREFIX = "PREV"
    PLAYERS_ON_TEAM_IN_GAME = "PLAYERS_ON_TEAM_IN_GAME"
    CORE_PLAYERS_ON_TEAM_IN_GAME = "CORE_PLAYERS_ON_TEAM_IN_GAME"

    replace_missing_with_empty_set = lambda x : x if isinstance(x, set) else set()

    team_games = team_game_data[[game_id_column_team, team_id_column_team]]

    players_roster_data = player_game_data[[game_id_column_player, team_id_column_player, player_id_column, minutes_played_column]]
    core_players_in_game_dataframe = players_roster_data.loc[players_roster_data[minutes_played_column] >= core_player_minutes_cutoff]

    players_in_game = (
        players_roster_data.groupby(by=[game_id_column_player, team_id_column_player])
        [player_id_column]
        .agg(set)
        .reset_index(name=PLAYERS_ON_TEAM_IN_GAME)
    )
    core_players_in_game = (
        core_players_in_game_dataframe.groupby(by=[game_id_column_player, team_id_column_player])
        [player_id_column]
        .agg(set)
        .reset_index(name=CORE_PLAYERS_ON_TEAM_IN_GAME)
    )

    team_games = team_games.merge(
        right=players_in_game,
        how='left',
        left_on=[game_id_column_team, team_id_column_team],
        right_on=[game_id_column_player, team_id_column_player]
    )
    team_games = team_games.merge(
        right=core_players_in_game,
        how='left',
        left_on=[game_id_column_team, team_id_column_team],
        right_on=[game_id_column_player, team_id_column_player]
    )

    team_games[CORE_PLAYERS_ON_TEAM_IN_GAME] = team_games[CORE_PLAYERS_ON_TEAM_IN_GAME].map(replace_missing_with_empty_set)
    team_games[PLAYERS_ON_TEAM_IN_GAME] = team_games[PLAYERS_ON_TEAM_IN_GAME].map(replace_missing_with_empty_set)

    team_games[PREV_PREFIX + PLAYERS_ON_TEAM_IN_GAME] = (
        team_games.groupby(by=team_id_column_team)
            [PLAYERS_ON_TEAM_IN_GAME]
            .shift(1)
            .map(replace_missing_with_empty_set)
        )
    team_games[PREV_PREFIX + CORE_PLAYERS_ON_TEAM_IN_GAME] = (
        team_games.groupby(by=team_id_column_team)
            [CORE_PLAYERS_ON_TEAM_IN_GAME]
            .shift(1)
            .map(replace_missing_with_empty_set)
        )

    team_game_data[ROSTER_ADD_CORE_PLAYER] = team_games.apply(
        lambda row : 0.0 if len(row[CORE_PLAYERS_ON_TEAM_IN_GAME].difference(row[PREV_PREFIX + PLAYERS_ON_TEAM_IN_GAME])) == 0 else 1.0,
        axis=1
    )
    team_game_data[ROSTER_REMOVE_CORE_PLAYER] = team_games.apply(
        lambda row : 0.0 if len(row[PREV_PREFIX + CORE_PLAYERS_ON_TEAM_IN_GAME].difference(row[PLAYERS_ON_TEAM_IN_GAME])) == 0 else 1.0,
        axis=1
    )

    return team_game_data

# TODO: Implement
def add_net_expected_stat_changes_from_roster_change_columns(
    player_game_data: pd.DataFrame,
    team_game_data: pd.DataFrame,
    player_id_column_info: str,
    player_id_column_player: str,
    game_id_column: str,
    team_id_column: str,
    stat_columns: list[str],
    core_player_minutes_cutoff: int = 25
    ) -> pd.DataFrame:
    """
    Adds columnns to team_game_data containing the expected net change in the given stats based on the change in 
    """
    return team_game_data

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
    Adds a column to game_data representing the time elapsed between a static event's date and the current game date.
    The static event's dates are represented inside of a dataframe where each player_id corresponds to the static event's time.
    The static_player_event_time and game_date columns must be represented in datetime form.
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
PRESEASON = 'PRESEASON'
REGULAR_SEASON = 'REGULAR_SEASON'
PLAYOFFS = 'PLAYOFFS'
PLAY_IN = 'PLAY_IN'
ALL_SEASON_TYPES = [
    PRESEASON,
    REGULAR_SEASON,
    PLAYOFFS,
    PLAY_IN
]
SEASON_ENCODINGS = {
    PRESEASON : "1",
    REGULAR_SEASON : "2",
    PLAYOFFS : "4",
    PLAY_IN : "5"
}
def add_encoded_season_type_columns(
    team_game_data: pd.DataFrame,
    game_id_column: str
    ) -> pd.DataFrame:
    season_type_id = team_game_data[game_id_column].astype(str).str[0]

    for season_type in ALL_SEASON_TYPES:
        team_game_data[season_type] = _encode_equality_as_integer(season_type_id, SEASON_ENCODINGS[season_type])

    return team_game_data

def encode_win_loss_column_as_integer(
    game_data: pd.DataFrame,
    win_loss_column: str
    ) -> pd.DataFrame:
    """
    Converts the given game_data's win/loss columnn from a string represenation to an interger representation.
    A value of 0 representing a loss, and a value of 1 representing a win.
    """

    game_data[win_loss_column] = _encode_equality_as_integer(game_data[win_loss_column], "W")
    return game_data

UNKNOWN_HEIGHT = 'UNKNOWN_HEIGHT'
def convert_height_to_inches(
    player_info: pd.DataFrame,
    height_column: str,
    add_unknown_heights_column: bool = False,
    fill_unknown_with_mean: bool = False
    ) -> pd.DataFrame:
    heights = player_info[height_column]
    heights_split = heights.str.split("-", expand=True)
    feet = pd.to_numeric(heights_split[0], errors="coerce")
    inches = pd.to_numeric(heights_split[1], errors="coerce")
    player_info[height_column] = feet * 12 + inches
    
    if add_unknown_heights_column:
        player_info[UNKNOWN_HEIGHT] = _encode_equality_as_integer(heights, "")

    if fill_unknown_with_mean:
        player_info[height_column] = player_info[height_column].fillna(player_info[height_column].mean())

    return player_info

UNKNOWN_WEIGHT = 'UNKNOWN_WEIGHT'
def handle_unknown_weight(
    player_info: pd.DataFrame,
    weight_column: str,
    add_unknown_weights_column: bool = False,
    fill_unknown_with_mean: bool = False
    ) -> pd.DataFrame:
    weights = player_info[weight_column]
    player_info[weight_column] = pd.to_numeric(weights, errors='coerce')

    if add_unknown_weights_column:
        player_info[UNKNOWN_WEIGHT] = _encode_equality_as_integer(weights, "")
        player_info[weight_column] = player_info[weight_column].fillna(0)

    if fill_unknown_with_mean:
        player_info[weight_column] = player_info[weight_column].fillna(player_info[weight_column].mean())

    return player_info

### POSITION TYPES: A value of 1 represents True, and a value of 0 represents False. ###
CENTER = 'Center'
CENTER_FORWARD = 'Center-Forward'
FORWARD = 'Forward'
_FORWARD_CENTER = 'Forward-Center'
_FORWARD_GUARD = 'Forward-Guard'
GUARD = 'Guard'
GUARD_FORWARD = 'Guard-Forward'
UNKNOWN_POSITION = 'UNKNOWN_POSITION'
ALL_POSITIONS = [
    CENTER,
    FORWARD,
    GUARD,
    GUARD_FORWARD,
    CENTER_FORWARD
]
def add_encoded_position_columns(
    player_info: pd.DataFrame,
    position_column: str,
    add_unknown_position_column: bool = False,
    fill_unknown_with_position: str | None = None
    ) -> pd.DataFrame:
    position = player_info[position_column]

    forward_center = _encode_equality_as_integer(position, _FORWARD_CENTER)
    forward_guard = _encode_equality_as_integer(position, _FORWARD_GUARD)

    player_info[GUARD] = _encode_equality_as_integer(position, GUARD)
    player_info[GUARD_FORWARD] = _encode_equality_as_integer(position, GUARD_FORWARD) + forward_guard
    player_info[FORWARD] = _encode_equality_as_integer(position, FORWARD)
    player_info[CENTER_FORWARD] = _encode_equality_as_integer(position, CENTER_FORWARD) + forward_center
    player_info[CENTER] = _encode_equality_as_integer(position, CENTER)

    if fill_unknown_with_position is not None:
        player_info[fill_unknown_with_position] += _encode_equality_as_integer(position, "")

    if add_unknown_position_column:
        player_info[UNKNOWN_POSITION] = _encode_equality_as_integer(position, "")

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

def drop_all_rows_with_missing_info(
        data: pd.DataFrame
    ) -> pd.DataFrame:
    """
    Drops all rows with any columns containing exactly '' as its value.
    """

    return data[(data != '').all(axis=1)]
