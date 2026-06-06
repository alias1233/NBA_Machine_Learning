from enum import Enum

from src.data_preparation.data_collection import data_collection
from src.data_preparation.components.nba_data import NBAData

class NBADataUser():
    """
    Helper class for user prompting with NBA data
    """

    @staticmethod
    def get_player_id_user(use_id: bool) -> str | None:
        if use_id:
            player = input("Input the player id or q to quit: ")
            if player.capitalize() == "Q":
                return None
            return player
        
        player = input("Input the player name or q to quit: ")
        if player.capitalize() == "Q":
            return None

        player_ids = NBAData.player_name_to_ids(player)
        while not player_ids:
            player = input("Player name does not correspond with a player. Input the player name or q to quit: ")
            if player.capitalize() == "Q":
                return None
            player_ids = NBAData.player_name_to_ids(player)

        player_id = 0
        if len(player_ids) == 1:
            player_id = player_ids[0]
        else:
            id_index = -1
            while id_index < 0 or id_index >= len(player_ids):
                print(player_ids)
                id_index = int(input("Input the index of the id to use: "))
            player_id = player_ids[id_index]
        return player_id
    
    @staticmethod
    def get_season_range_user():
        def get_season_range_user():
            start_season = int(input("Input the start season year: "))
            end_season = int(input("Input the end season year: "))
            invalid_input = (end_season < start_season) or (start_season < 1950 or end_season < 1950) or (start_season > 2100 or end_season > 2100)
            if invalid_input:
                raise ValueError
            return (int(start_season), int(end_season))
        
        while True:
            try:
                return get_season_range_user()
            except:
                print("Not a valid season range. ")
    
    class TeamChooseSchema(Enum):
        ID = 1
        ABBREVIATION = 2
        FULL_NAME = 3

    @staticmethod
    def get_team_choose_schema_user() -> TeamChooseSchema:
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
        return choose_schema

    @staticmethod
    def get_team_id_user() -> str | None:
        match NBADataUser.get_team_choose_schema_user():
            case NBADataUser.TeamChooseSchema.ID:
                team = input("Input the team id or q to quit: ")
                if team.capitalize() == "Q":
                    return None
                return team
            case NBADataUser.TeamChooseSchema.ABBREVIATION:
                while True:
                    team = input("Input the team abbreviation or q to quit: ")
                    if (team.capitalize() == "Q"):
                        return None
                    try:
                        return NBAData.team_abb_to_id(team)
                    except:
                        print("Team abbreviation does not correspond with a team.")
            case NBADataUser.TeamChooseSchema.FULL_NAME:
                while True:
                    team = input("Input the team name or q to quit: ")
                    if (team.capitalize() == "Q"):
                        return None
                    try:
                        return NBAData.team_name_to_id(team)
                    except:
                        print("Team name does not correspond with a team.")

def get_collection_params_user():
    wait_interval = input("Input the wait interval between each data fetch: ")
    get_all = input("Input whether to automatically collect all informations or manually choose specific targets: (a/m) ").capitalize() == 'A'
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
    
    return collect_data_user(get_player_ids_user, data_collection.collect_player_info_data)

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

    return collect_data_user(get_player_infos_user, data_collection.collect_player_game_data)

def collect_team_game_data_user():
    def get_team_infos_user() -> list:
        team_info = []
        while True:
            team_id = NBADataUser.get_team_id_user()
            if team_id is None:
                break
            season_start, season_end = NBADataUser.get_season_range_user()
            team_info.append((team_id, season_start, season_end))
        return team_info
    
    return collect_data_user(get_team_infos_user, data_collection.collect_team_game_data)

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

CURRENT_PLAYER_INFO_LOOP_INDEX = ~5000 # DONE
CURRENT_PLAYER_GAME_DATA_LOOP_INDEX = 4709
CURRENT_TEAM_GAME_DATA_LOOP_INDEX = 0