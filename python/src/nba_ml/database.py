import sqlite3 as sq
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any
import pandas as pd

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
    The name of the category, which is also the name of its column.
    """

    category_type: DataType
    """
    The datatype of this category's values.
    """

class Categories():
    """
    Helper class for creating Category lists
    """

    def __init__(self):
        self.categories: list[Category] = []

    def add_category(
        self,
        category_name: str,
        category_type: DataType
        ) -> Category:
        """
        Creates and registers a Category to this Category list.
        """

        category = Category(category_name, category_type)
        self.categories.append(category)
        return category

    def get_categories(self) -> list[Category]:
        return self.categories

class DataConflictHandler(Enum):
        IGNORE = "IGNORE"
        REPLACE = "REPLACE"

class Database():
    """
    Simple SQLite Database
    """

    def __init__(
        self,
        filepath: Path,
        name: str,
        categories: list[Category],
        data_conflict_handler: DataConflictHandler,
        primary_keys: list[Category]
        ):

        self.filepath = filepath
        self.name = name
        self.categories = categories
        self.category_names = [property.category_name for property in categories]
        self.primary_keys = primary_keys
        self.create_command = Database.get_create_command(name, categories, primary_keys)
        self.insert_command = Database.get_insert_command(name, categories, data_conflict_handler)

    def initialize_components(self):
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sq.connect(self.filepath)
        self.cursor = self.connection.cursor()
        self.cursor.execute(self.create_command)
        self.add_missing_columns()

    def add_missing_columns(self):
        """
        Adds any column a table was created before. New columns hold null until something fills them.
        """

        held = {row[1] for row in self.cursor.execute(f"PRAGMA table_info({self.name})")}

        for category in self.categories:
            if category.category_name not in held:
                self.cursor.execute(
                    f"ALTER TABLE {self.name} ADD COLUMN {category.category_name} {category.category_type.value}"
                )

    @staticmethod
    def get_insert_command(
        name: str,
        categories: list[Category],
        data_conflict_handler: DataConflictHandler
        ) -> str:

        # The columns are named rather than left to the table's own order, so a column added later
        # still receives the value meant for it.
        column_names = ",".join(category.category_name for category in categories)
        placeholders = ",".join(f":{category.category_name}" for category in categories)

        return f"INSERT OR {data_conflict_handler.value} INTO {name} ({column_names}) VALUES ({placeholders})"

    @staticmethod
    def get_create_command(
        name: str,
        categories: list[Category],
        primary_keys: list[Category]
        ) -> str:

        command = f"CREATE TABLE IF NOT EXISTS {name} ("
        for category in categories:
            command += f"{category.category_name} {category.category_type.value},"

        primary_key_categories = ""
        for category in primary_keys:
            primary_key_categories += category.category_name + ","

        primary_key_categories = primary_key_categories.rstrip(',')
        command += f"PRIMARY KEY ({primary_key_categories}))"

        return command

    @staticmethod
    def category_to_category_name_dict(value: dict[Category, Any]):
        return {category.category_name : v for category, v in value.items()}

    def add_dataframe(self, dataframe: pd.DataFrame) -> int:
        """
        Adds every row of the given dataframe, reading one column per category and ignoring the
        rest. Returns how many rows were added.

        Raises:
            ValueError if the dataframe is missing a category's column.
        """

        missing = [name for name in self.category_names if name not in dataframe.columns]
        if missing:
            raise ValueError(f"{self.name} needs columns that the given data does not have: {', '.join(missing)}.")

        rows = dataframe[self.category_names].to_dict("records")
        self.cursor.executemany(self.insert_command, rows)
        self.connection.commit()

        return len(rows)

    def get_query_columns(self, categories: list[Category] | None = None) -> str:
        return ",".join(category.category_name for category in categories or self.categories)

    def query(
            self,
            SQL_condition: str | None = None,
            condition_params: dict[Category, Any] | None = None,
            categories: list[Category] | None = None,
            limit: int | None = None,
            order_by: str | None = None
            ) -> list:
        """
        Queries the database with the given parameters and returns the values found as a list.

        Args:
            SQL_condition: A filter in SQL style on the returned values.
            condition_params: A dictionary that maps each category in the SQL_condition to a value.
            categories: The specified returned categories of the fetched values. An input value of None will return all categories.
            limit: The maximum number of returned values. An input value of None corresponds to no limit.
            order_by: A sort in SQL style, such as "GAME_DATE DESC", which a limit reads the top of.
        """

        query_columns = self.get_query_columns(categories)
        command = f"""SELECT {query_columns} FROM {self.name}"""
        if SQL_condition:
            command = f"{command} WHERE {SQL_condition}"
        if order_by:
            command += f""" ORDER BY {order_by}"""
        if limit is not None:
            command += f""" LIMIT {limit}"""
        if condition_params:
            string_dict = self.category_to_category_name_dict(condition_params)
            self.cursor.execute(command, string_dict)
        else:
            self.cursor.execute(command)
        return self.cursor.fetchall()

    def query_dataframe(
            self,
            SQL_condition: str | None = None,
            condition_params: dict[Category, Any] | None = None,
            categories: list[Category] | None = None,
            limit: int | None = None,
            order_by: str | None = None
            ) -> pd.DataFrame:
        """
        Identical to [query] except that the values are returned as a labeled pandas.DataFrame.
        """

        data = self.query(SQL_condition, condition_params, categories, limit, order_by)
        if not categories:
            categories = self.categories
        return pd.DataFrame(data, columns=[category.category_name for category in categories])

    def max_value(self, category: Category) -> Any:
        """The largest value held in one category, or None when the table is empty."""

        self.cursor.execute(f"SELECT MAX({category.category_name}) FROM {self.name}")
        return self.cursor.fetchone()[0]

    def close(self):
        self.connection.commit()
        self.connection.close()

    def get_categories(self) -> list[Category]:
        return self.categories

    def __enter__(self):
        self.initialize_components()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
