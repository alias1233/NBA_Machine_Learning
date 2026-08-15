"""
The SQLite table layer every store is built on.

A connection belongs to the thread that opened it, because SQLite refuses one opened elsewhere and
the prediction service answers requests on several threads at once. Open a table with
`with database:` around the work, and do not nest two of those blocks on the same table.

These files are read by the prediction service and written by the collection job at the same time,
from two containers sharing one directory, so every connection is opened for that. See PRAGMAS.
"""

import sqlite3 as sq
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any
import pandas as pd

BUSY_TIMEOUT_SECONDS = 30
"""
How long a statement waits for another writer before it gives up. Python's own default is five.

The backstop rather than the fix. Write-ahead logging below is what stops a reader queueing behind
a writer at all. This only decides how long one waits in the cases that still queue, such as the
moment a second writer holds the file.
"""

PRAGMAS = (
    f"PRAGMA busy_timeout = {BUSY_TIMEOUT_SECONDS * 1000}",
    # Write-ahead logging is what lets a reader and a writer hold the same file at once. On a
    # rollback journal a reader queues behind the writer and is refused once its wait runs out.
    # Measured against a batch-committing writer: with no wait allowed, eight of eighteen reads were
    # refused on a rollback journal and none under this. It is a property of the file rather than
    # the connection, so setting it again once it is on costs one read.
    "PRAGMA journal_mode = WAL",
    # A commit is written but not flushed to the disk platter. A power cut can then lose the last
    # transactions without corrupting the file, and every row here is collected again in one run.
    "PRAGMA synchronous = NORMAL"
)

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
        primary_keys: list[Category],
        indexes: list[list[Category]] | None = None
        ):
        """
        Args:
            indexes are the column groups a filter that is not the primary key reads. Without one,
            every such query reads the whole table, which is what makes a large archive slow.
        """

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
        # Read before connecting, because connecting is what creates the file.
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
        """
        Creates the table, any column named since it was created, and the indexes.

        Once per process, because the service opens a connection per query and this is the same
        work every time. A file that was not there is prepared whatever this process did before,
        which is what makes a data directory that has been replaced behave like a new one.
        """

        if self._prepared and not file_is_new:
            return

        with self._preparing:
            self.cursor.execute(self.create_command)
            self.add_missing_columns()
            for command in self.index_commands:
                self.cursor.execute(command)
            self._prepared = True

    def add_missing_columns(self):
        """Adds any column named after the table was created. New columns hold null until filled."""

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

        # The columns are named rather than left to the table's own order, so a column added later
        # still receives the value meant for it.
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
        """Named after the columns it covers, so the same index is never created twice."""

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
        """
        Queries the table and returns the rows found.

        Args:
            SQL_condition: a filter in SQL, naming each value it compares against as :COLUMN_NAME.
            condition_params: the value for each category named in SQL_condition.
            categories: which columns to return. None returns all of them.
            limit: the most rows to return. None returns all of them.
            order_by: a sort in SQL, such as "GAME_DATE DESC", which a limit reads the top of.
            distinct: drops repeated rows in SQLite rather than handing every one of them back.
        """

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
        """Identical to [query] except that the rows are returned as a labeled pandas.DataFrame."""

        data = self.query(SQL_condition, condition_params, categories, limit, order_by, distinct)

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

        return self.cursor.rowcount

    def max_value(self, category: Category) -> Any:
        """The largest value held in one category, or None when the table is empty."""

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
