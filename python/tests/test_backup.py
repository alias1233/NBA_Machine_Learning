"""Tests for the backup command."""

import sqlite3
import tarfile

import pytest

from nba_ml import paths
from nba_ml.cli import backup
from nba_ml.data_collection import source_identity
from nba_ml.stores import player_games, team_games

import fake_data

@pytest.fixture(autouse=True)
def collected_league():
    player_games.store(fake_data.player_game_frame())
    team_games.store(fake_data.team_game_frame())

def published_model_file():
    """Creates fake model files in place of a trained model."""

    model_file = paths.model_file("player_stats", "points")
    model_file.parent.mkdir(parents=True, exist_ok=True)
    model_file.write_bytes(b"weights")
    paths.evaluation_file("player_stats", "points").write_text("{}", encoding="utf-8")
    paths.training_report_file("player_stats", "points").write_text("report", encoding="utf-8")
    graph = paths.graphs_directory("player_stats", "points") / "training.png"
    graph.parent.mkdir()
    graph.write_bytes(b"graph")

    return model_file

def test_an_archive_holds_the_databases_and_the_model_files():
    source_identity.MARKER.write_text("balldontlie\n", encoding="utf-8")
    published_model_file()

    with tarfile.open(backup.back_up()) as archive:
        held = archive.getnames()

    assert f"{backup.DATABASES}/{player_games.FILEPATH.name}" in held
    assert f"{backup.DATABASES}/{team_games.FILEPATH.name}" in held
    assert f"{backup.MODELS}/player_stats/points/model.pth" in held
    assert f"{backup.MODELS}/player_stats/points/evaluation.json" in held
    assert f"{backup.MODELS}/player_stats/points/training_report.txt" not in held
    assert f"{backup.MODELS}/player_stats/points/graphs/training.png" not in held
    assert source_identity.MARKER.name in held

def test_a_backed_up_database_opens_and_holds_the_rows_it_held(tmp_path):
    with tarfile.open(backup.back_up()) as archive:
        archive.extractall(tmp_path, filter="data")

    copy = sqlite3.connect(tmp_path / backup.DATABASES / team_games.FILEPATH.name)
    held = copy.execute(f"SELECT COUNT(*) FROM {team_games.NAME}").fetchone()[0]
    copy.close()

    assert held == len(fake_data.SEASON_GAMES) * 2

def test_only_the_newest_archives_are_left():
    paths.BACKUP_DIRECTORY.mkdir(parents=True, exist_ok=True)
    older = ["20200101-000000", "20200102-000000", "20200103-000000"]

    for taken in older:
        (paths.BACKUP_DIRECTORY / f"{backup.ARCHIVE_PREFIX}{taken}{backup.ARCHIVE_SUFFIX}").write_bytes(b"old")

    written = backup.back_up(keep=2)
    left = {path.name for path in paths.BACKUP_DIRECTORY.glob(f"{backup.ARCHIVE_PREFIX}*")}

    assert left == {f"{backup.ARCHIVE_PREFIX}{older[-1]}{backup.ARCHIVE_SUFFIX}", written.name}

def test_an_archive_left_half_written_by_a_failed_run_is_removed():
    paths.BACKUP_DIRECTORY.mkdir(parents=True, exist_ok=True)
    half_written = paths.BACKUP_DIRECTORY / (
        f"{backup.ARCHIVE_PREFIX}20200101-000000{backup.ARCHIVE_SUFFIX}{backup.WORKING_SUFFIX}"
    )
    half_written.write_bytes(b"partial")

    backup.back_up()

    assert not half_written.exists()

def test_a_run_that_leaves_nothing_is_refused():
    with pytest.raises(ValueError):
        backup.back_up(keep=0)
