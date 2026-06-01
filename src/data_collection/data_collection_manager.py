from enum import Enum, auto

from .data_collectors import player_game_data_collector, player_info_collector

from .data_collectors.components.nba_data import NBAData, NBADataUser
from .data_collectors import team_game_data_collector
from . import data_query_manager

def collect_player_info_data(wait_interval: float, starting_index: int, player_ids: list = []):
    if not player_ids:
        players = NBAData.get_all_players()
        player_ids = [player['id'] for player in players]

    return player_info_collector.collect_and_save_data(wait_interval, starting_index, player_ids)

def collect_player_game_data(wait_interval: float, starting_index: int, player_info: list = []):
    if not player_info:
        try:
            player_info = data_query_manager.get_all_players_season_played_info()
        except:
            print("Database of player seasons is non-functional. Automatic data collection is non-functional.")
            return starting_index
        
    return player_game_data_collector.collect_and_save_data(wait_interval, starting_index, player_info)

def collect_team_game_data(wait_interval: float, starting_index: int, team_info: list = []):
    if not team_info:
        teams = NBAData.get_all_teams()
        team_info = [(team['id'], NBAData.get_oldest_season_with_data(), NBAData.get_current_nba_season()) for team in teams]
    return team_game_data_collector.collect_and_save_data(wait_interval, starting_index, team_info)

def get_collection_params():
    wait_interval = input("Input the wait interval between each data fetch: ")
    get_all = input("Input whether to automatically collect all player's informations or manually input specific players: (a/m) ").capitalize() == 'A'
    starting_index = 0
    if get_all:
        starting_index = int(input("Input the starting index: "))
    return int(wait_interval), get_all, int(starting_index)

def collect_data_user(user_choice_function, collect_data_function) -> int:
    wait_interval, get_all, starting_index = get_collection_params()
    choice_data = []
    if not get_all:
        choice_data = user_choice_function()
    
    return collect_data_function(wait_interval, starting_index, choice_data)

def collect_player_info_data_user():
    def get_player_ids_user() -> list:
        use_id = input("Input whether to search for players by id or by full name: (i/n) ").capitalize() == 'I'
        player_ids = []
        while True:
            player_id = NBADataUser.get_player_id_user(use_id)
            if player_id is None:
                break 
            player_ids.append(player_id)
        return player_ids
    
    return collect_data_user(get_player_ids_user, collect_player_info_data)

def collect_player_game_data_user():
    def get_player_infos_user() -> list:
        use_id = input("Input whether to search for players by id or by full name: (i/n) ").capitalize() == 'I'
        player_info = []
        while True:
            player_id = NBADataUser.get_player_id_user(use_id)
            if player_id is None:
                break
            season_start, season_end = NBADataUser.get_season_range_user()
            player_info.append((player_id, season_start, season_end))
        return player_info

    return collect_data_user(get_player_infos_user, collect_player_game_data)

def collect_team_game_data_user():
    def get_team_infos_user() -> list:
        choose_schema: NBADataUser.TeamChooseSchema | None = None
        while choose_schema is None:
            choose_type = input("Input whether to search for teams by id, name, or abbreviation: (i/n/a) ")
            match choose_type.capitalize():
                case "I":
                    choose_schema = NBADataUser.TeamChooseSchema.ID
                case "N":
                    choose_schema = NBADataUser.TeamChooseSchema.FULL_NAME
                case "A":
                    choose_schema = NBADataUser.TeamChooseSchema.ABBREVIATION
                case _:
                    print("Not a valid choosing option.")
        
        team_info = []
        while True:
            team_id = NBADataUser.get_team_id_user(choose_schema)
            if team_id is None:
                break
            season_start, season_end = NBADataUser.get_season_range_user()
            team_info.append((team_id, season_start, season_end))
        return team_info
    
    return collect_data_user(get_team_infos_user, collect_team_game_data)

class DataCategories(Enum):
    PLAYER_INFO = 1
    PLAYER_GAME_BOX_SCORE_STATS = 2
    TEAM_GAME_BOX_SCORE_STATS = 3

def being_collect_data_user(data_category: DataCategories):
    match data_category:
        case DataCategories.PLAYER_INFO:
            collect_player_info_data_user()
        case DataCategories.PLAYER_GAME_BOX_SCORE_STATS:
            collect_player_game_data_user()
        case DataCategories.TEAM_GAME_BOX_SCORE_STATS:
            collect_team_game_data_user()

if __name__ == "__main__":
    data_category_input = input("""Input the category of data to collect:
                          PI for player information 
                          PGI for player game information 
                          TGI for team game information
                          """)
    data_category = None
    match data_category_input.capitalize():
        case _ if data_category_input == 'PI':
            data_category = DataCategories.PLAYER_INFO
        case _ if data_category_input == "PGI":
            data_category = DataCategories.PLAYER_GAME_BOX_SCORE_STATS
        case _ if data_category_input == "TGI":
            data_category = DataCategories.TEAM_GAME_BOX_SCORE_STATS
        
    if data_category is not None:
        being_collect_data_user(data_category)

CURRENT_PLAYER_INFO_LOOP_INDEX = 5000 # DONE
CURRENT_PLAYER_GAME_DATA_LOOP_INDEX = 571