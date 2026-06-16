import pandas as pd
from typing import Any

# TODO: Fix errors concerning pandas: A value is trying to be set on a copy of a slice from a DataFrame.

def sort_columns_alphabetically(dataframe: pd.DataFrame) -> pd.DataFrame:
    return dataframe.sort_index(axis=1)

def create_lookup_table(
    dataframe: pd.DataFrame,
    key_column: str
    ) -> dict[Any, pd.DataFrame]:
    lookup_table = {}
    for key, data in dataframe.groupby(by=key_column):
        lookup_table[key] = data
    return lookup_table

# Represents the number of days without a game inbetween the current game and the player's last played game.
REST = 'REST'
MAX_REST = 7

def add_rest_column(
    game_data: pd.DataFrame, 
    game_date_column: str, 
    group_by_id: str | None = None
    ) -> pd.DataFrame:
    """
    Adds rest column to the given game_data. 
    The given game_data must be sorted by game date, and the game_date column must be in datetime form.
    The value of rest is clamped to MAX_REST.
    If it is the first game that has ever been played, the value for 'rest' will be MAX_REST.
    """

    game_dates = None
    if group_by_id:
        game_dates = game_data.groupby(group_by_id, sort=False)
    else:
        game_dates = game_data

    game_data[REST] = (game_dates[game_date_column].diff().dt.days - 1).fillna(MAX_REST).clip(upper=MAX_REST)
    return game_data

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

# TODO: Support bucketing on continuous data such as weight and height for by-attribute stat columns.

STATS_BASED_ON_ATTRIBUTE_SUFFIX = "_BY_"

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

    THe attribute column must be a hot encoded column in player_info, where every value at each row index is 0 or 1 corresponding to whether the player has that attribute.
    """

    for attribute_column in attribute_columns:
        player_ids_with_attribute = player_info[player_info[attribute_column] == 1][player_id_column_info].unique()
        player_game_data_with_attribute = (
            player_game_data[player_game_data[player_id_column_player].isin(player_ids_with_attribute)]
        )

        total_player_stats_in_game_by_attribute = (
            player_game_data_with_attribute.groupby(
                by=[game_id_column, team_id_column])
                [stat_columns]
                .sum()
                .reset_index()
                )
        
        team_game_data = (
            team_game_data
            .merge(
                total_player_stats_in_game_by_attribute, 
                on=[game_id_column, team_id_column], 
                suffixes=[None, STATS_BASED_ON_ATTRIBUTE_SUFFIX + attribute_column],
                how='left'
                )
                .fillna(0)
                )

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

def _encode_equality_as_integer(column: pd.Series, value: Any) -> pd.Series:
    """
    Returns a series where each value is 1 if the value corresponding to the given series equals the given string, and 0 otherwise.  
    """

    return (column == value).astype(int)

### SEASON TYPES: A value of 1 represents True, and a value of 0 represents False. ###
PRESEASON = 'PRESEASON'
REGULAR_SEASON = 'REGULAR_SEASON'
PLAYOFFS = 'PLAYOFFS'
PLAY_IN = 'PLAY_IN'

def add_encoded_season_type_columns(
    team_game_data: pd.DataFrame,
    game_id_column: str
    ) -> pd.DataFrame:
    season_type_id = team_game_data[game_id_column].astype(str).str[0]
    team_game_data[PRESEASON] = _encode_equality_as_integer(season_type_id, "1")
    team_game_data[REGULAR_SEASON] = _encode_equality_as_integer(season_type_id, "2")
    team_game_data[PLAYOFFS] = _encode_equality_as_integer(season_type_id, "4")
    team_game_data[PLAY_IN] = _encode_equality_as_integer(season_type_id, "5")
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
    height_column: str
    ) -> pd.DataFrame:
    heights = player_info[height_column]
    heights_split = heights.str.split("-", expand=True)
    feet = pd.to_numeric(heights_split[0], errors="coerce").fillna(0)
    inches = pd.to_numeric(heights_split[1], errors="coerce").fillna(0)
    player_info[height_column] = feet * 12 + inches
    player_info[UNKNOWN_HEIGHT] = _encode_equality_as_integer(heights, "")
    return player_info

UNKNOWN_WEIGHT = 'UNKNOWN_WEIGHT'

def encode_unknown_weight(
    player_info: pd.DataFrame,
    weight_column: str    
    ) -> pd.DataFrame:
    weights = player_info[weight_column]
    player_info[weight_column] = pd.to_numeric(weights, errors='coerce').fillna(0)
    player_info[UNKNOWN_WEIGHT] = _encode_equality_as_integer(weights, "")
    return player_info

### POSITION TYPES: A value of 1 represents True, and a value of 0 represents False. ###
CENTER = 'Center'
CENTER_FORWARD = 'Center-Forward'
FORWARD = 'Forward'
FORWARD_CENTER = 'Forward-Center'
FORWARD_GUARD = 'Forward-Guard'
GUARD = 'Guard'
GUARD_FORWARD = 'Guard-Forward'
UNKNOWN_POSITION = 'UNKNOWN_POSITION'
ALL_POSITIONS = [
    CENTER,
    CENTER_FORWARD,
    FORWARD,
    FORWARD_CENTER,
    FORWARD_GUARD,
    GUARD,
    GUARD_FORWARD,
    UNKNOWN_POSITION
]

def add_encoded_position_columns(
    player_info: pd.DataFrame,
    position_column: str,
    ) -> pd.DataFrame:
    position = player_info[position_column]
    player_info[CENTER] = _encode_equality_as_integer(position, CENTER)
    player_info[CENTER_FORWARD] = _encode_equality_as_integer(position, CENTER_FORWARD)
    player_info[FORWARD] = _encode_equality_as_integer(position, FORWARD)
    player_info[FORWARD_CENTER] = _encode_equality_as_integer(position, FORWARD_CENTER)
    player_info[FORWARD_GUARD] = _encode_equality_as_integer(position, FORWARD_GUARD)
    player_info[GUARD] = _encode_equality_as_integer(position, GUARD)
    player_info[GUARD_FORWARD] = _encode_equality_as_integer(position, GUARD_FORWARD)
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
