"""SQLite table wrapper used by every store."""

import sqlite3 as sq
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Collection
import pandas as pd

BUSY_TIMEOUT_SECONDS = 30
"""Seconds a statement waits on a locked database before failing."""

PRAGMAS = (
    f"PRAGMA busy_timeout = {BUSY_TIMEOUT_SECONDS * 1000}",
    # WAL mode lets readers keep reading while another connection writes.
    "PRAGMA journal_mode = WAL",
    "PRAGMA synchronous = NORMAL"
)

class DataType(Enum):
    INTEGER = "integer"
    REAL = "real"
    TEXT = "text"
    NULL = "null"
    BLOB = "blob"

@dataclass(frozen=True)
class Category():
    """A table column with its name and data type."""

    category_name: str
    category_type: DataType

class Categories():
    """Collects Category objects into a list as they are added."""

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

def held_in(category: Category, values: Collection[int]) -> str:
    """Returns a SQL IN condition for the given integers."""

    return f"{category.category_name} IN ({','.join(str(int(value)) for value in values)})"

class Database():
    """A single SQLite table with its columns and the SQL commands for reading and writing it."""

    def __init__(
        self,
        filepath: Path,
        name: str,
        categories: list[Category],
        data_conflict_handler: DataConflictHandler,
        primary_keys: list[Category],
        indexes: list[list[Category]] | None = None
        ):
        self.filepath = filepath
        self.name = name
        self.categories = categories
        self.category_names = [property.category_name for property in categories]
        self.primary_keys = primary_keys
        self.create_command = Database.get_create_command(name, categories, primary_keys)
        self.insert_command = self.get_insert_command(name, categories, data_conflict_handler)
        self.index_commands = [Database.get_index_command(name, columns) for columns in indexes or []]
        self._open = threading.local()
        self._preparing = threading.Lock()
        self._prepared = False

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
        # Check before connecting, since connecting creates the file.
        file_is_new = not self.filepath.exists()
        connection = sq.connect(self.filepath)

        try:
            for pragma in PRAGMAS:
                connection.execute(pragma)

            self._open.connection = connection
            self._open.cursor = connection.cursor()
            self._prepare_schema(file_is_new)
        except Exception:
            self._open.connection = None
            self._open.cursor = None
            connection.close()
            raise

    def _prepare_schema(self, file_is_new: bool):
        """Creates the table, any newly added columns, and the indexes."""

        if self._prepared and not file_is_new:
            return

        with self._preparing:
            self.cursor.execute(self.create_command)
            self.add_missing_columns()
            for command in self.index_commands:
                self.cursor.execute(command)
            self._prepared = True

    def add_missing_columns(self):
        """Adds columns defined after the table was created. Existing rows get null in them."""

        held = {row[1] for row in self.cursor.execute(f"PRAGMA table_info({self.name})")}

        for category in self.categories:
            if category.category_name not in held:
                self.cursor.execute(
                    f"ALTER TABLE {self.name} ADD COLUMN {category.category_name} {category.category_type.value}"
                )

    def get_insert_command(
        self,
        name: str,
        categories: list[Category],
        data_conflict_handler: DataConflictHandler
        ) -> str:

        column_names = ",".join(category.category_name for category in categories)
        placeholders = ",".join(f":{category.category_name}" for category in categories)

        command = f"INSERT INTO {name} ({column_names}) VALUES ({placeholders})"
        if data_conflict_handler is DataConflictHandler.IGNORE:
            return command.replace("INSERT INTO", "INSERT OR IGNORE INTO", 1)

        primary_key_names = {category.category_name for category in self.primary_keys}
        updates = ",".join(
            f"{category.category_name}=excluded.{category.category_name}"
            for category in categories
            if category.category_name not in primary_key_names
        )
        primary_keys = ",".join(category.category_name for category in self.primary_keys)
        if not updates:
            return f"{command} ON CONFLICT ({primary_keys}) DO NOTHING"
        return f"{command} ON CONFLICT ({primary_keys}) DO UPDATE SET {updates}"

    @staticmethod
    def get_index_command(name: str, columns: list[Category]) -> str:
        column_names = [category.category_name for category in columns]

        return (
            f"CREATE INDEX IF NOT EXISTS {name}_{'_'.join(column_names)}_index "
            f"ON {name} ({','.join(column_names)})"
        )

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
        """Inserts every row of the given dataframe and returns the number of rows."""

        missing = [name for name in self.category_names if name not in dataframe.columns]
        if missing:
            raise ValueError(f"{self.name} needs columns that the given data does not have: {', '.join(missing)}.")

        rows = dataframe[self.category_names].to_dict("records")
        self.cursor.executemany(self.insert_command, rows)

        return len(rows)

    def get_query_columns(self, categories: list[Category] | None = None) -> str:
        return ",".join(category.category_name for category in categories or self.categories)

    def query(
            self,
            SQL_condition: str | None = None,
            condition_params: dict[Category, Any] | None = None,
            categories: list[Category] | None = None,
            limit: int | None = None,
            order_by: str | None = None,
            distinct: bool = False
            ) -> list:
        """Queries the table. Parameters in SQL_condition are written as :COLUMN_NAME."""

        command = (
            f"SELECT {'DISTINCT ' if distinct else ''}{self.get_query_columns(categories)} "
            f"FROM {self.name}"
        )
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
            order_by: str | None = None,
            distinct: bool = False
            ) -> pd.DataFrame:
        """Same as query, but returns the rows as a DataFrame."""

        data = self.query(SQL_condition, condition_params, categories, limit, order_by, distinct)

        return pd.DataFrame(data, columns=[category.category_name for category in categories or self.categories])

    def delete(
        self,
        SQL_condition: str,
        condition_params: dict[Category, Any] | None = None
        ) -> int:
        """Deletes the rows matching the condition and returns the number deleted."""

        self.cursor.execute(
            f"DELETE FROM {self.name} WHERE {SQL_condition}",
            self.category_to_category_name_dict(condition_params or {})
        )

        return self.cursor.rowcount

    def max_value(self, category: Category) -> Any:
        """Returns the largest value in a column, or None if the table is empty."""

        self.cursor.execute(f"SELECT MAX({category.category_name}) FROM {self.name}")
        return self.cursor.fetchone()[0]

    def close(self, commit: bool = True):
        connection = getattr(self._open, "connection", None)
        if connection is None:
            return

        if commit:
            connection.commit()
        else:
            connection.rollback()
        connection.close()
        self._open.connection = None
        self._open.cursor = None

    def get_categories(self) -> list[Category]:
        return self.categories

    def __enter__(self):
        self.initialize_components()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close(commit=exc_type is None)
        return False
