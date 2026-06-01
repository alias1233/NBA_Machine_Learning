from .data_collectors import player_game_data_collector, player_info_collector

from .data_collectors.components.nba_data import NBAData
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