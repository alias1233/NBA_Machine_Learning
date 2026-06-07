import requests
import time

from nba_api.stats.static import teams, players
from nba_api.stats.library.parameters import Season, SeasonTypeAllStar, PlayerOrTeamAbbreviation
from nba_api.stats.endpoints import boxscoretraditionalv3, playergamelog, commonplayerinfo, leaguegamelog

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

class NBAData():
    """
    Handles Retrieving NBA Data
    """

    @staticmethod
    def get_oldest_season_with_all_player_box_score_data_data():
        return 1996
    
    @staticmethod
    def get_current_nba_season():
        return Season.current_season_year

    @staticmethod
    def convert_year_to_NBA_season(season_year: int) -> str:
        return str(season_year) + '-' + str(season_year + 1)[-2:]
    
    @staticmethod
    def get_all_season_types() -> list[str]:
        return [SeasonTypeAllStar.preseason, SeasonTypeAllStar.regular, SeasonTypeAllStar.playin, SeasonTypeAllStar.playoffs]

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
    def team_id_to_name(id: str) -> str | None:
        team_data = teams.find_team_name_by_id(id)
        if team_data is None:
            return None
        
        return team_data['full_name']
    
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
    def get_player_season_game_logs(player_id: str, season_year: int, season_type: str):
        try:
            return playergamelog.PlayerGameLog(
                player_id=player_id,
                season=NBAData.convert_year_to_NBA_season(season_year),
                season_type_all_star=season_type
            ).get_data_frames()
        except Exception as e:
            print(f"player id {player_id} in the {season_year} season with {season_type} season type is invalid.")
            print(f"Error Message: {e}")

    @staticmethod
    @retry
    def get_all_teams_season_game_logs(season_year: int, season_type: str):
        try:
            return leaguegamelog.LeagueGameLog(
                season=NBAData.convert_year_to_NBA_season(season_year),
                season_type_all_star=season_type
            ).get_data_frames()
        except Exception as e:
            print(f"The year {season_year} with {season_type} season type is invalid")
            print(f"Error Message: {e}")

    @staticmethod
    @retry
    def get_all_players_season_game_logs(season_year: int, season_type: str):
        try:
            return leaguegamelog.LeagueGameLog(
                player_or_team_abbreviation=PlayerOrTeamAbbreviation.player,
                season=NBAData.convert_year_to_NBA_season(season_year),
                season_type_all_star=season_type
            ).get_data_frames()
        except Exception as e:
            print(f"The year {season_year} with {season_type} season type is invalid")
            print(f"Error Message: {e}")