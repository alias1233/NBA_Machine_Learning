from .data_collectors import player_game_data_collector, player_info_collector, team_game_data_collector
from .databases import player_game_database, player_info_database, team_game_database
from .components.base_data_collector import DataCollector
from .components.nba_data import NBAData
from .components.database import Database
from .data_query import Query

def collect_data(database: Database, collector: DataCollector, wait_interval: float, starting_index: int, **kwargs):
    database.initialize_components()
    database.create_database_self()
    index = collector.begin_fetch_data(starting_index=starting_index, wait_interval=wait_interval, **kwargs)
    database.close()
    return index

def collect_player_info_data(wait_interval: float, starting_index: int, player_ids: list = []):
    if not player_ids:
        players = NBAData.get_all_players()
        player_ids = [player['id'] for player in players]

    return collect_data(
        player_info_database.DATABASE, 
        player_info_collector.PlayerInfoCollector(), 
        wait_interval, starting_index, 
        player_ids=player_ids
        )

def collect_player_game_data(wait_interval: float, starting_index: int, player_info: list = []):
    if not player_info:
        try:
            player_info = Query.get_all_players_season_played_info()
        except:
            print("Database of player seasons is non-functional. Automatic data collection is non-functional.")
            return starting_index
        
    return collect_data(
        player_game_database.DATABASE, 
        player_game_data_collector.PlayerGameDataCollector(), 
        wait_interval, starting_index, 
        player_info=player_info
        )

def collect_team_game_data(wait_interval: float, starting_index: int, team_info: list = []):
    if not team_info:
        teams = NBAData.get_all_teams()
        team_info = [(team['id'], NBAData.get_oldest_season_with_data(), NBAData.get_current_nba_season()) for team in teams]
    
    return collect_data(
        team_game_data_collector.DATABASE, 
        team_game_data_collector.TeamDameDataCollector(), 
        wait_interval, starting_index, 
        team_info=team_info
        )