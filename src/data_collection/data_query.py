from .databases import player_game_database, player_info_database, team_game_database
from data_collection.components.database import Database

PLAYER_INFO_DATABASE = player_info_database.DATABASE
PLAYER_GAME_DATABASE = player_game_database.DATABASE
TEAM_GAME_DATABASE = team_game_database.DATABASE

class Query():
    """
    Handles querying databases.
    """

    @staticmethod
    def get_all_database_info(database: Database):
        database.initialize_components()
        data = database.query()
        database.close()
        return data

    @staticmethod
    def get_all_players_info():
        return Query.get_all_database_info(PLAYER_INFO_DATABASE)

    @staticmethod
    def get_all_players_season_played_info():
        PLAYER_INFO_DATABASE.initialize_components()
        categories = [
            player_info_database.PLAYER_ID,
            player_info_database.FROM_YEAR,
            player_info_database.TO_YEAR
        ]
        data = PLAYER_INFO_DATABASE.query(categories=categories)
        PLAYER_INFO_DATABASE.close()
        return data

    @staticmethod
    def get_all_player_game_info():
        return Query.get_all_database_info(PLAYER_GAME_DATABASE)
    
    @staticmethod
    def get_all_team_game_info():
        return Query.get_all_database_info(TEAM_GAME_DATABASE)
    
class Processing():
    """
    Helpers for processing NBA stats
    """
    pass

if __name__ == "__main__":
    print(Query.get_all_player_game_info())