from src.data_preparation.components.database import Database, DataConflictHandler
from src.data_preparation.components.category import DataType, Categories

FILEPATH = "data/team_game_data.db"
NAME = "teams"
CATEGORIES = Categories()
TEAM_ID = CATEGORIES.add_category("TEAM_ID", DataType.INTEGER)
GAME_ID = CATEGORIES.add_category("GAME_ID", DataType.INTEGER)
SEASON_ID = CATEGORIES.add_category("SEASON_ID", DataType.INTEGER)
GAME_DATE = CATEGORIES.add_category("GAME_DATE", DataType.TEXT)
MATCHUP = CATEGORIES.add_category("MATCHUP", DataType.TEXT)
WIN_LOSS = CATEGORIES.add_category("WL", DataType.TEXT)
MINUTES_PLAYED = CATEGORIES.add_category("MIN", DataType.INTEGER)
FIELD_GOALS_MADE = CATEGORIES.add_category("FGM", DataType.INTEGER)
FIELD_GOALS_ATTEMPTED = CATEGORIES.add_category("FGA", DataType.INTEGER)
THREE_POINTERS_MADE = CATEGORIES.add_category("FG3M", DataType.INTEGER)
THREE_POINTERS_ATTEMPTED = CATEGORIES.add_category("FG3A", DataType.INTEGER)
FREE_THROWS_MADE = CATEGORIES.add_category("FTM", DataType.INTEGER)
FREE_THROWS_ATTEMPTED = CATEGORIES.add_category("FTA", DataType.INTEGER)
OFFENSIVE_REBOUNDS = CATEGORIES.add_category("OREB", DataType.INTEGER)
DEFENSIVE_REBOUNDS = CATEGORIES.add_category("DREB", DataType.INTEGER)
ASSISTS = CATEGORIES.add_category("AST", DataType.INTEGER)
STEALS = CATEGORIES.add_category("STL", DataType.INTEGER)
BLOCKS = CATEGORIES.add_category("BLK", DataType.INTEGER)
TURNOVERS = CATEGORIES.add_category("TOV", DataType.INTEGER)
PERSONAL_FOULS = CATEGORIES.add_category("PF", DataType.INTEGER)
PRIMARY_KEYS = [
    TEAM_ID,
    GAME_ID
]
DATA_CONFLICT_HANDLER = DataConflictHandler.IGNORE
DATABASE = Database(FILEPATH, NAME, CATEGORIES.get_categories(), DATA_CONFLICT_HANDLER, PRIMARY_KEYS)