import requests
import time
import pandas

from nba_api.stats.static import teams, players
from nba_api.stats.endpoints import boxscoretraditionalv3, playergamelog, teaminfocommon, teamgamelogs

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

# Helper For Retrieving NBA Data
class NBAData():

    @staticmethod
    def convert_year_to_NBA_season(season_year: int) -> str:
        return str(season_year) + '-' + str(season_year + 1)[-2:]

    @staticmethod
    def team_abb_to_id(abbreviation: str) -> str:
        team = teams.find_team_by_abbreviation(abbreviation)
        if (team != None):
            return team["id"]
        raise ValueError(
            f"{abbreviation} does not correspond with a team."
        )
    
    @staticmethod
    def player_name_to_ids(name: str) -> list:
        players_data = players.find_players_by_full_name(name)
        ids = []
        for player in players_data:
            ids.append(player["id"])
        return ids
    
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