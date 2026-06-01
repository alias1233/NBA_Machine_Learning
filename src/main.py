from data_collection import data_collection_manager

from data_collection.data_collectors.components.nba_data import NBADataUser

def get_collection_params_user():
    wait_interval = input("Input the wait interval between each data fetch: ")
    get_all = input("Input whether to automatically collect all player's informations or manually input specific players: (a/m) ").capitalize() == 'A'
    starting_index = 0
    if get_all:
        starting_index = int(input("Input the starting index: "))
    return int(wait_interval), get_all, int(starting_index)

def collect_data_user(user_choice_function, collect_data_function) -> int:
    wait_interval, get_all, starting_index = get_collection_params_user()
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
    
    return collect_data_user(get_player_ids_user, data_collection_manager.collect_player_info_data)

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

    return collect_data_user(get_player_infos_user, data_collection_manager.collect_player_game_data)

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
    
    return collect_data_user(get_team_infos_user, data_collection_manager.collect_team_game_data)

def begin_collect_data_user():
    data_category_input = input("""Input the category of data to collect:
                          PI for player information 
                          PGI for player game information 
                          TGI for team game information
                          """)
    match data_category_input.capitalize():
        case _ if data_category_input == 'PI':
            collect_player_info_data_user()
        case _ if data_category_input == "PGI":
            collect_player_game_data_user()
        case _ if data_category_input == "TGI":
            collect_team_game_data_user()

if __name__ == "__main__":
    begin_collect_data_user()

CURRENT_PLAYER_INFO_LOOP_INDEX = 5000 # DONE
CURRENT_PLAYER_GAME_DATA_LOOP_INDEX = 616