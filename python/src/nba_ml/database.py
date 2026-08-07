"""
The SQLite table layer every store is built on.

A connection belongs to the thread that opened it, because SQLite refuses one opened elsewhere and
the prediction service answers requests on several threads at once. Open a table with
`with database:` around the work, and do not nest two of those blocks on the same table.
"""

import sqlite3 as sq
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any
import pandas as pd

class DataType(Enum):
    """A value's type. Each name is also the SQL name for that type."""

    INTEGER = "integer"
    REAL = "real"
    TEXT = "text"
    NULL = "null"
    BLOB = "blob"

@dataclass(frozen=True)
class Category():
    """One column: what it is called, and what it holds."""

    category_name: str
    category_type: DataType

class Categories():
    """Builds a Category list, registering each one as it is named."""

    def __init__(self):
        self.categories: list[Category] = []

    def add_category(
        self,
        category_name: str,
        category_type: DataType
        ) -> Category:
        category = Category(category_name, category_type)
        self.categories.append(category)
        return category

    def get_categories(self) -> list[Category]:
        return self.categories

class DataConflictHandler(Enum):
        IGNORE = "IGNORE"
        REPLACE = "REPLACE"

class Database():
    """One SQLite table, holding the columns it has and the commands that read and write it."""

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
        self._open = threading.local()

    def _opened(self, part: str):
        value = getattr(self._open, part, None)
        if value is None:
            raise RuntimeError(f"{self.name} is not open. Wrap the work in `with database:`.")

        return value

    @property
    def connection(self) -> sq.Connection:
        return self._opened("connection")

    @property
    def cursor(self) -> sq.Cursor:
        return self._opened("cursor")

    def initialize_components(self):
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        connection = sq.connect(self.filepath)
        self._open.connection = connection
        self._open.cursor = connection.cursor()
        self.cursor.execute(self.create_command)
        self.add_missing_columns()

    def add_missing_columns(self):
        """Adds any column named after the table was created. New columns hold null until filled."""

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

        columns = "".join(f"{category.category_name} {category.category_type.value}," for category in categories)
        primary_key_columns = ",".join(category.category_name for category in primary_keys)

        return f"CREATE TABLE IF NOT EXISTS {name} ({columns}PRIMARY KEY ({primary_key_columns}))"

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
        Queries the table and returns the rows found.

        Args:
            SQL_condition: a filter in SQL, naming each value it compares against as :COLUMN_NAME.
            condition_params: the value for each category named in SQL_condition.
            categories: which columns to return. None returns all of them.
            limit: the most rows to return. None returns all of them.
            order_by: a sort in SQL, such as "GAME_DATE DESC", which a limit reads the top of.
        """

        command = f"SELECT {self.get_query_columns(categories)} FROM {self.name}"
        if SQL_condition:
            command += f" WHERE {SQL_condition}"
        if order_by:
            command += f" ORDER BY {order_by}"
        if limit is not None:
            command += f" LIMIT {int(limit)}"

        if condition_params:
            self.cursor.execute(command, self.category_to_category_name_dict(condition_params))
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
        """Identical to [query] except that the rows are returned as a labeled pandas.DataFrame."""

        data = self.query(SQL_condition, condition_params, categories, limit, order_by)

        return pd.DataFrame(data, columns=[category.category_name for category in categories or self.categories])

    def delete(
        self,
        SQL_condition: str,
        condition_params: dict[Category, Any] | None = None
        ) -> int:
        """
        Removes the rows matching a filter written the same way [query] writes one. Returns how many
        went. A filter is required, so nothing can empty a table by leaving one out.
        """

        self.cursor.execute(
            f"DELETE FROM {self.name} WHERE {SQL_condition}",
            self.category_to_category_name_dict(condition_params or {})
        )
        self.connection.commit()

        return self.cursor.rowcount

    def max_value(self, category: Category) -> Any:
        """The largest value held in one category, or None when the table is empty."""

        self.cursor.execute(f"SELECT MAX({category.category_name}) FROM {self.name}")
        return self.cursor.fetchone()[0]

    def close(self):
        connection = getattr(self._open, "connection", None)
        if connection is None:
            return

        connection.commit()
        connection.close()
        self._open.connection = None
        self._open.cursor = None

    def get_categories(self) -> list[Category]:
        return self.categories

    def __enter__(self):
        self.initialize_components()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
