"""The SQLite table wrapper's transaction boundary, and reading a file while it is written."""

import sqlite3
import threading

import pandas as pd
import pytest

from nba_ml.database import Categories, DataConflictHandler, DataType, Database, held_in


def test_a_list_of_numbers_becomes_a_filter_nothing_else_can_reach(tmp_path):
    """The values go into the SQL rather than into a bound parameter, so each is read as one."""

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
    """
    The deployment's load-bearing property: the service reads these files while the collection job
    writes them, from two containers sharing one directory.

    On a rollback journal, which is what SQLite does without being told otherwise, a reader queues
    behind the writer and is refused once its wait runs out. Measured against a batch-committing
    writer with no wait allowed: eight of eighteen reads refused on a rollback journal, none under
    write-ahead logging.
    """

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
            # Only what the writer has committed, and answered rather than refused or queued.
            assert database.query() == [(1,)]
    finally:
        finish.set()
        thread.join()

    with database:
        assert len(database.query()) == 4_999


def test_the_journal_survives_a_data_directory_being_replaced(tmp_path):
    """
    The schema is prepared once a process, and a file that is not there is prepared again.

    A first server loads its data directory whole, so a table this process has already opened can
    be replaced by one it has never seen. See nba_ml/cli/serving_data.py.
    """

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
