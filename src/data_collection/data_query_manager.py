from .data_collectors import player_game_data_collector, player_info_collector

from .data_collectors import team_game_data_collector

PLAYER_INFO_DATABASE = player_info_collector.DATABASE
PLAYER_GAME_DATABASE = player_game_data_collector.DATABASE

def get_all_players_info():
    PLAYER_INFO_DATABASE.initialize_components()
    data = PLAYER_INFO_DATABASE.query_all_SQL()
    PLAYER_INFO_DATABASE.close()
    return data

def get_all_players_season_played_info():
    data = get_all_players_info()
    players = []
    for player_data in data:
        player_id = PLAYER_INFO_DATABASE.get_property_from_value(player_data, player_info_collector.PLAYER_ID.category_name)
        from_year = PLAYER_INFO_DATABASE.get_property_from_value(player_data, player_info_collector.FROM_YEAR.category_name)
        to_year = PLAYER_INFO_DATABASE.get_property_from_value(player_data, player_info_collector.TO_YEAR.category_name)
        players.append((player_id, from_year, to_year))
    return players

def get_all_player_game_info():
    PLAYER_GAME_DATABASE.initialize_components()
    data = PLAYER_GAME_DATABASE.query_all_SQL()
    PLAYER_GAME_DATABASE.close()
    return data

if __name__ == "__main__":
    print(get_all_player_game_info())