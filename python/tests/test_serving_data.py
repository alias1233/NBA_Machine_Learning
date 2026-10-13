"""Tests for packing and loading the serving data archive."""

import sqlite3
import tarfile
from datetime import date

import pytest

from nba_ml import paths
from nba_ml.cli import serving_data
from nba_ml.data_collection import source_identity
from nba_ml.stores import player_games, players, schedule, team_games, teams

import fake_data


@pytest.fixture(autouse=True)
def collected_data():
    player_games.store(fake_data.player_game_frame())
    team_games.store(fake_data.team_game_frame())
    players.store(fake_data.player_info_frame())
    teams.store(fake_data.teams_frame())
    schedule.store([fake_data.scheduled_game(game) for game in fake_data.SEASON_GAMES])
    source_identity.MARKER.write_text("balldontlie\n", encoding="utf-8")
    model_file = paths.model_file("player_stats", "points")
    model_file.parent.mkdir(parents=True, exist_ok=True)
    model_file.write_bytes(b"weights")
    paths.evaluation_file("player_stats", "points").write_text("{}", encoding="utf-8")
    paths.training_report_file("player_stats", "points").write_text("report", encoding="utf-8")
    graph = paths.graphs_directory("player_stats", "points") / "training.png"
    graph.parent.mkdir()
    graph.write_bytes(b"graph")


def _row_count(database_file, table):
    with sqlite3.connect(database_file) as database:
        return database.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_a_serving_archive_keeps_only_the_needed_game_window_and_loads_it(tmp_path):
    archive = tmp_path / "server-data.tar.gz"
    cutoff = date(2024, 10, 30)

    serving_data.pack(archive, cutoff)

    assert _row_count(player_games.FILEPATH, player_games.NAME) == len(fake_data.SEASON_GAMES) * 6
    with tarfile.open(archive) as packed:
        packed.extractall(tmp_path / "packed", filter="data")
    packed_player_games = tmp_path / "packed" / serving_data.DATABASES / player_games.FILEPATH.name
    assert _row_count(packed_player_games, player_games.NAME) < len(fake_data.SEASON_GAMES) * 6
    assert _row_count(packed_player_games, player_games.NAME) > 0

    loaded = serving_data.load(archive, tmp_path / "server-data")

    assert (loaded / source_identity.MARKER.name).read_text(encoding="utf-8") == "balldontlie\n"
    assert (loaded / serving_data.MODELS / "player_stats" / "points" / "model.pth").read_bytes() == b"weights"
    assert (loaded / serving_data.MODELS / "player_stats" / "points" / "evaluation.json").read_text(
        encoding="utf-8"
    ) == "{}"
    assert not (loaded / serving_data.MODELS / "player_stats" / "points" / "training_report.txt").exists()
    assert not (loaded / serving_data.MODELS / "player_stats" / "points" / "graphs").exists()
    assert _row_count(
        loaded / serving_data.DATABASES / team_games.FILEPATH.name,
        team_games.NAME
    ) == _row_count(tmp_path / "packed" / serving_data.DATABASES / team_games.FILEPATH.name, team_games.NAME)


def test_a_player_with_no_game_in_the_window_is_left_out_of_the_release(tmp_path):
    retired = fake_data.player_info_frame(fake_data.ALL_PLAYERS[:1]).assign(PERSON_ID=999_001)
    players.store(retired)
    archive = tmp_path / "server-data.tar.gz"

    serving_data.pack(archive, date(2024, 10, 30))
    loaded = serving_data.load(archive, tmp_path / "server-data")

    described = serving_data._player_ids(loaded / serving_data.DATABASES / players.FILEPATH.name)
    played = serving_data._player_ids(loaded / serving_data.DATABASES / player_games.FILEPATH.name)

    assert 999_001 not in described
    assert described == played


def test_a_release_holding_a_player_it_describes_nothing_about_is_refused(tmp_path):
    archive = tmp_path / "server-data.tar.gz"
    serving_data.pack(archive, date(2024, 10, 30))
    unpacked = tmp_path / "packed"
    with tarfile.open(archive) as packed:
        packed.extractall(unpacked, filter="data")
    with sqlite3.connect(unpacked / serving_data.DATABASES / players.FILEPATH.name) as described:
        described.execute(
            f"UPDATE {players.NAME} SET {players.PLAYER_ID.category_name} = 999001 "
            f"WHERE {players.PLAYER_ID.category_name} = "
            f"(SELECT MIN({players.PLAYER_ID.category_name}) FROM {players.NAME})"
        )

    with pytest.raises(RuntimeError, match="no information row"):
        serving_data._verify_loaded_data(unpacked)


def test_loading_refuses_to_replace_existing_data(tmp_path):
    archive = tmp_path / "server-data.tar.gz"
    serving_data.pack(archive, date(2024, 10, 30))
    destination = tmp_path / "server-data"
    destination.mkdir()
    sentinel = destination / "keep"
    sentinel.write_text("here", encoding="utf-8")

    with pytest.raises(RuntimeError, match="nonempty"):
        serving_data.load(archive, destination)

    assert sentinel.read_text(encoding="utf-8") == "here"
