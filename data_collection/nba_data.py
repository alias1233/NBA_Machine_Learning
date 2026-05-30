import requests
import time

from nba_api.stats.static import teams, players
from nba_api.stats.endpoints import boxscoretraditionalv3, playergamelog, teamgamelogs, commonplayerinfo

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
    def convert_year_to_NBA_season(season_year: int) -> str:
        return str(season_year) + '-' + str(season_year + 1)[-2:]

    @staticmethod
    def get_all_teams():
        return teams.get_teams()

    @staticmethod
    def team_abb_to_id(abbreviation: str) -> str:
        team = teams.find_team_by_abbreviation(abbreviation)
        if (team != None):
            return team["id"]
        raise ValueError(
            f"{abbreviation} does not correspond with a team."
        )
    
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
        return playergamelog.PlayerGameLog(
            player_id=player_id,
            season=NBAData.convert_year_to_NBA_season(season_year)
        ).get_data_frames()
    
    @staticmethod
    @retry
    def get_team_season_stats(team_id: str, season_year: int):
        return teamgamelogs.TeamGameLogs(
            team_id_nullable=team_id,
            season_nullable=NBAData.convert_year_to_NBA_season(season_year)
        ).get_data_frames()
    
# Helper For Retrieving Data With User Input
class NBADataUser():

    @staticmethod
    def get_player_id(use_id: bool):
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
    def get_season_range():
        start_season = input("Input the start season year: ")
        end_season = input("Input the end season year: ")
        return (int(start_season), int(end_season))