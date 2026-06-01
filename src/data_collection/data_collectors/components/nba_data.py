import requests
import time
from enum import Enum, auto

from nba_api.stats.static import teams, players
from nba_api.stats.library.parameters import Season
from nba_api.stats.endpoints import boxscoretraditionalv3, playergamelog, teamgamelog, commonplayerinfo

def retry(func, retries: int = 3, timeout: int = 5):
    """
    Wrapper to retry a function call [retries] times as originally defined in:
    https://github.com/swar/nba_api/blob/master/docs/examples/Home%20Team%20Win-Loss%20Modeling/Home%20Team%20Win-Loss%20Data%20Prep.ipynb
    """
    def retry_wrapper(*args, **kwargs):
        attempts = 0
        while attempts < retries:
            try:
                return func(*args, **kwargs)
            except requests.exceptions.RequestException as e:
                print(e)
                time.sleep(timeout)
                attempts += 1

    return retry_wrapper

# Handles Retrieving NBA Data
class NBAData():

    @staticmethod
    def get_oldest_season_with_data():
        return 1985
    
    @staticmethod
    def get_current_nba_season():
        return Season.current_season_year

    @staticmethod
    def convert_year_to_NBA_season(season_year: int) -> str:
        return str(season_year) + '-' + str(season_year + 1)[-2:]

    @staticmethod
    def get_all_teams():
        return teams.get_teams()

    @staticmethod
    def team_abb_to_id(abbreviation: str) -> str:
        team = teams.find_team_by_abbreviation(abbreviation)
        if team != None:
            return team["id"]
        raise ValueError(
            f"{abbreviation} does not correspond with a team."
        )
    
    @staticmethod
    def team_name_to_id(name: str) -> str:
        team = teams.find_teams_by_full_name(name)
        if team == []:
            raise ValueError(
            f"{name} does not correspond with a team."
            )
        return team[0]['id']
    
    @staticmethod
    def get_all_players():
        return players.get_players()
    
    @staticmethod
    def player_name_to_ids(name: str) -> list:
        players_data = players.find_players_by_full_name(name)
        ids = []
        for player in players_data:
            ids.append(player["id"])
        return ids
    
    @staticmethod
    def player_id_to_name(id: str) -> str | None:
        player_data = players.find_player_by_id(id)
        if player_data is None:
            return None
        
        return player_data['full_name']
    
    @staticmethod
    @retry
    def get_common_player_info(player_id: str):
        return commonplayerinfo.CommonPlayerInfo(
            player_id=player_id
        ).get_data_frames()
    
    @staticmethod
    @retry
    def get_game_box_score_stats(game_id: str):
        return boxscoretraditionalv3.BoxScoreTraditionalV3(
            game_id=game_id
            ).get_data_frames()
    
    @staticmethod
    @retry
    def get_player_season_game_logs(player_id: str, season_year: int):
        try:
            return playergamelog.PlayerGameLog(
                player_id=player_id,
                season=NBAData.convert_year_to_NBA_season(season_year)
            ).get_data_frames()
        except:
            print(f"player id {player_id} in the {season_year} season is invalid.")
    
    @staticmethod
    @retry
    def get_team_season_stats(team_id: str, season_year: int):
        return teamgamelog.TeamGameLog(
            team_id=team_id,
            season=NBAData.convert_year_to_NBA_season(season_year)
        ).get_data_frames()
    
# Helper For Retrieving Data With User Input
class NBADataUser():

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
    def get_team_id_user(choose_type: TeamChooseSchema) -> str | None:
        match choose_type:
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
                    