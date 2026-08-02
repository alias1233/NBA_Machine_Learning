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
    """
    Defines a data category.
    """

    category_name: str
    """
    The public name of the category.
    """

    private_name: str
    """
    The private name of this category.
    If not initialized, it will be set to the same as the category_name.
    """

    category_type: DataType
    """
    The datatype of this category's values.
    """

    @classmethod
    def create(cls, category_name: str, category_type: DataType, private_name: str | None = None):
        """
        Creates a Category.
        If no private_name is given, then the private_name will be set to the same as the category_name.
        """

        private_name = private_name if private_name is not None else category_name
        return cls(category_name=category_name, private_name=private_name, category_type=category_type)

class Categories():
    """
    Helper class for creating Category lists
    """
    
    def __init__(self):
        self.categories: list[Category] = []

    def add_category(
        self, 
        category_name: str, 
        category_type: DataType, 
        private_name: str | None = None
        ) -> Category:
        """
        Creates and registers a Category to this Category list.

        If no private_name is given, then the private_name will be set to the same as the category_name.
        """

        category = Category.create(category_name, category_type, private_name)
        self.categories.append(category)
        return category
    
    def get_categories(self) -> list[Category]:
        return self.categories