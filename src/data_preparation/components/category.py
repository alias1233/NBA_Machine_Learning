from enum import Enum
from dataclasses import dataclass

class DataType(Enum):
    """
    Specifies a value's type. The string enum representation is the SQL name for the corresponding type.
    """

    INTEGER = "integer"
    REAL = "real"
    TEXT = "text"
    NULL = "null"
    BLOB = "blob"

@dataclass(frozen=True)
class Category():
    category_name: str
    category_type: DataType

class Categories():
    """
    Helper Class For Managing Categories Lists
    """
    
    def __init__(self):
        self.categories: list[Category] = []

    def add_category(self, category_name: str, category_type: DataType) -> Category:
        category = Category(category_name, category_type)
        self.categories.append(category)
        return category
    
    def get_categories(self) -> list[Category]:
        return self.categories