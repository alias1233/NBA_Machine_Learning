"""Tests for the SQLite table wrapper: transactions and reading during a write."""

import sqlite3
import threading

import pandas as pd
import pytest

from nba_ml.database import Categories, DataConflictHandler, DataType, Database, held_in


def test_a_list_of_numbers_becomes_a_filter_nothing_else_can_reach(tmp_path):
    categories = Categories()
    identifier = categories.add_category("IDENTIFIER", DataType.INTEGER)
    database = Database(
        tmp_path / "rows.db",
        "rows",
        categories.get_categories(),
        DataConflictHandler.IGNORE,
        [identifier]
    )

    with database:
        database.add_dataframe(pd.DataFrame({"IDENTIFIER": [1, 2, 3]}))
        assert database.query(held_in(identifier, [3, 1])) == [(1,), (3,)]
        assert database.query(held_in(identifier, [])) == []

    with pytest.raises(ValueError):
        held_in(identifier, ["1); DROP TABLE rows; --"])


def test_a_failed_batch_is_rolled_back(tmp_path):
    categories = Categories()
    identifier = categories.add_category("IDENTIFIER", DataType.INTEGER)
    database = Database(
        tmp_path / "rows.db",
        "rows",
        categories.get_categories(),
        DataConflictHandler.IGNORE,
        [identifier]
    )

    with pytest.raises(sqlite3.ProgrammingError):
        with database:
            database.add_dataframe(pd.DataFrame({"IDENTIFIER": [1, {"not": "a value"}]}))

    with database:
        assert database.query() == []


def test_an_exception_after_a_write_leaves_the_previous_rows_intact(tmp_path):
    categories = Categories()
    identifier = categories.add_category("IDENTIFIER", DataType.INTEGER)
    value = categories.add_category("VALUE", DataType.TEXT)
    database = Database(
        tmp_path / "rows.db",
        "rows",
        categories.get_categories(),
        DataConflictHandler.REPLACE,
        [identifier]
    )

    with database:
        database.add_dataframe(pd.DataFrame({"IDENTIFIER": [1], "VALUE": ["before"]}))

    with pytest.raises(RuntimeError, match="stop"):
        with database:
            database.add_dataframe(pd.DataFrame({"IDENTIFIER": [1, 2], "VALUE": ["after", "new"]}))
            raise RuntimeError("stop")

    with database:
        assert database.query() == [(1, "before")]


def test_a_reader_is_answered_while_a_writer_holds_the_same_file(tmp_path):
    categories = Categories()
    identifier = categories.add_category("IDENTIFIER", DataType.INTEGER)
    database = Database(
        tmp_path / "rows.db",
        "rows",
        categories.get_categories(),
        DataConflictHandler.REPLACE,
        [identifier]
    )

    with database:
        database.add_dataframe(pd.DataFrame({"IDENTIFIER": [1]}))

    writing = threading.Event()
    finish = threading.Event()

    def writer():
        with database:
            database.add_dataframe(pd.DataFrame({"IDENTIFIER": range(2, 5_000)}))
            writing.set()
            finish.wait(timeout=10)

    thread = threading.Thread(target=writer)
    thread.start()
    try:
        writing.wait(timeout=10)
        with database:
            assert database.query() == [(1,)]
    finally:
        finish.set()
        thread.join()

    with database:
        assert len(database.query()) == 4_999


def test_the_journal_survives_a_data_directory_being_replaced(tmp_path):
    categories = Categories()
    identifier = categories.add_category("IDENTIFIER", DataType.INTEGER)
    database = Database(
        tmp_path / "rows.db",
        "rows",
        categories.get_categories(),
        DataConflictHandler.REPLACE,
        [identifier]
    )

    with database:
        database.add_dataframe(pd.DataFrame({"IDENTIFIER": [1]}))
        assert database.cursor.execute("PRAGMA journal_mode").fetchone() == ("wal",)

    for leftover in tmp_path.iterdir():
        leftover.unlink()

    with database:
        assert database.query() == []
