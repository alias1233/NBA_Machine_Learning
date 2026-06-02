from ..components import database
from ..components.database import Database, Categories, DataType

FILEPATH = "data/player_info.db"
NAME = "player_info"
CATEGORIES = Categories()
PLAYER_ID = CATEGORIES.add_category("PERSON_ID", DataType.INTEGER)
HEIGHT = CATEGORIES.add_category("HEIGHT", DataType.INTEGER)
WEIGHT = CATEGORIES.add_category("WEIGHT", DataType.REAL)
POSITION = CATEGORIES.add_category("POSITION", DataType.TEXT)
FROM_YEAR = CATEGORIES.add_category("FROM_YEAR", DataType.INTEGER)
TO_YEAR = CATEGORIES.add_category("TO_YEAR", DataType.INTEGER)
PRIMARY_KEYS = [
    PLAYER_ID
]
DATA_CONFLICT_HANDLER = database.DataConflictHandler.REPLACE
DATABASE = Database(FILEPATH, NAME, CATEGORIES.get_categories(), DATA_CONFLICT_HANDLER, PRIMARY_KEYS)