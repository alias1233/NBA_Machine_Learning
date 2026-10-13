"""Tests for publishing and loading feature builds."""

from datetime import date, datetime

import numpy as np
import pytest

from nba_ml import paths
from nba_ml.feature_engineering import feature_store

BUILD = "test_family"

def _subject(games: int, columns: int = 3, first_day: str = "2024-10-22") -> feature_store.SubjectSequences:
    dates = np.array(first_day, dtype="datetime64[ns]") + np.arange(games) * np.timedelta64(1, "D")

    return feature_store.SubjectSequences(
        game_dates=dates,
        sequence_values=np.arange(games * columns, dtype=np.float32).reshape(games, columns),
        opponent_team_ids=np.arange(games, dtype=np.int64)
    )

def _build(version_of: str = "2026-08-12T09:00:00") -> feature_store.FeatureBuild:
    built_at = datetime.fromisoformat(version_of)

    return feature_store.FeatureBuild(
        version=built_at.strftime(feature_store.VERSION_FORMAT),
        built_at=built_at,
        window_start_date=None,
        sequence_columns=("POINTS", "REBOUNDS", "ASSISTS"),
        subjects={1: _subject(4), 2: _subject(2)}
    )

def test_a_published_build_reads_back_as_it_was_written():
    published = _build()

    feature_store.publish(BUILD, published)
    read = feature_store.current(BUILD)

    assert read is not None
    assert read.version == published.version
    assert read.sequence_columns == published.sequence_columns
    assert set(read.subjects) == {1, 2}
    assert read.game_count == 6

    np.testing.assert_array_equal(read.subjects[1].sequence_values, published.subjects[1].sequence_values)
    np.testing.assert_array_equal(read.subjects[1].game_dates, published.subjects[1].game_dates)

def test_nothing_is_published_until_a_build_has_been():
    assert feature_store.current(BUILD) is None

def test_the_newest_build_is_the_one_that_is_read():
    feature_store.publish(BUILD, _build("2026-08-12T09:00:00"))
    feature_store.publish(BUILD, _build("2026-08-12T10:00:00"))

    read = feature_store.current(BUILD)

    assert read is not None
    assert read.version == "20260812-100000"

def test_a_build_left_half_written_by_a_failed_job_is_ignored():
    feature_store.publish(BUILD, _build("2026-08-12T09:00:00"))

    working = paths.feature_build_directory(BUILD) / (feature_store.WORKING_PREFIX + "20260812-110000")
    working.mkdir(parents=True)
    (working / feature_store.SEQUENCES_FILE).write_bytes(b"")
    (working / feature_store.DESCRIPTION_FILE).write_text("{}")

    read = feature_store.current(BUILD)

    assert read is not None
    assert read.version == "20260812-090000"

def test_whether_a_build_is_published_is_answered_without_reading_one():
    assert not feature_store.is_published(BUILD)

    feature_store.publish(BUILD, _build())

    assert feature_store.is_published(BUILD)
    assert feature_store._held == {}

def test_a_half_written_build_does_not_count_as_published():
    working = paths.feature_build_directory(BUILD) / (feature_store.WORKING_PREFIX + "20260812-110000")
    working.mkdir(parents=True)
    (working / feature_store.SEQUENCES_FILE).write_bytes(b"")
    (working / feature_store.DESCRIPTION_FILE).write_text("{}")

    assert not feature_store.is_published(BUILD)

def test_a_build_left_half_written_by_a_failed_job_is_removed_by_the_next_publish():
    working = paths.feature_build_directory(BUILD) / (feature_store.WORKING_PREFIX + "20260812-110000")
    working.mkdir(parents=True)
    (working / feature_store.SEQUENCES_FILE).write_bytes(b"")

    feature_store.publish(BUILD, _build("2026-08-12T12:00:00"))

    assert not working.exists()

def test_only_the_newest_builds_are_kept():
    for hour in range(9, 13):
        feature_store.publish(BUILD, _build(f"2026-08-12T{hour:02d}:00:00"))

    directory = paths.feature_build_directory(BUILD)
    versions = sorted(path.name for path in directory.iterdir() if path.is_dir())

    assert len(versions) == feature_store.KEPT_VERSIONS
    assert versions[-1] == "20260812-120000"

def test_a_model_reads_its_own_columns_out_of_a_build_made_for_every_model():
    build = _build()
    positions = build.column_positions(["ASSISTS", "POINTS"])
    subject = build.subjects[1].with_columns(positions)

    assert list(positions) == [2, 0]
    np.testing.assert_array_equal(subject.sequence_values[:, 0], build.subjects[1].sequence_values[:, 2])

def test_a_build_made_before_a_column_existed_says_so_rather_than_answering():
    build = _build()

    with pytest.raises(ValueError, match="STEALS"):
        build.column_positions(["POINTS", "STEALS"])

def test_only_the_games_before_the_predicted_one_are_read():
    subject = _subject(4, first_day="2024-10-22")

    assert subject.before(date(2024, 10, 22)).game_count == 0
    assert subject.before(date(2024, 10, 24)).game_count == 2
    assert subject.before(date(2030, 1, 1)).game_count == 4
