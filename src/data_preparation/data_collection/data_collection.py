from src.data_preparation.data_collection.data_collectors import player_game_data_collector, player_info_collector, team_game_data_collector
from src.data_preparation.components.nba_data import NBAData
from src.data_preparation.data_collection import data_query

def collect_player_info_data(wait_interval: float, starting_index: int, player_ids: list = []):
    if not player_ids:
        players = NBAData.get_all_players()
        player_ids = [player['id'] for player in players]

    return player_info_collector.PLAYER_INFO_COLLECTOR.begin_collect_data(starting_index, wait_interval, player_ids)

def collect_player_game_data(wait_interval: float, starting_index: int, player_info: list = []):
    if not player_info:
        try:
            player_info = data_query.get_all_players_season_played_info()
        except:
            print("Database of player seasons is non-functional. Automatic data collection is non-functional.")
            return starting_index
        
    return player_game_data_collector.PLAYER_GAME_DATA_COLLECTOR.begin_collect_data(starting_index, wait_interval, player_info)

def collect_team_game_data(wait_interval: float, starting_index: int, team_info: list = []):
    if not team_info:
        teams = NBAData.get_all_teams()
        team_info = [(team['id'], NBAData.get_oldest_season_with_data(), NBAData.get_current_nba_season()) for team in teams]
    
    return team_game_data_collector.TEAM_GAME_DATA_COLLECTOR.begin_collect_data(starting_index, wait_interval, team_info)