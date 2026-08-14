"""Collecting a player's own information."""

from datetime import date
from typing import Iterable

from nba_ml.sources.base import DataSource
from nba_ml.stores import player_games
from nba_ml.stores import players as players_store

def _with_career_seasons(player_info, careers, player_id):
    """Fill provider gaps from the player's collected game history."""

    career = careers.get(player_id)
    if career is None:
        return player_info

    first, last = career
    for column, value in (
        (players_store.FROM_YEAR.category_name, first),
        (players_store.TO_YEAR.category_name, last)
    ):
        if column not in player_info.columns or player_info[column].isna().all():
            player_info[column] = value
    return player_info

def collect(
    source: DataSource,
    player_ids: Iterable[int] | None = None,
    starting_index: int = 0,
    print_debug: bool = True
    ) -> int:
    """
    Writes one row per player to the store and returns how many were written.

    The index of each player is printed and starting_index picks a stopped run back up from where it
    reached. A source may cache its player list, so one player does not necessarily mean one request.

    Args:
        player_ids defaults to every player the source knows of.
    """

    ids = [player.id for player in source.players()] if player_ids is None else list(player_ids)

    rows_written = 0
    careers = player_games.career_seasons()
    for index in range(starting_index, len(ids)):
        player_id = ids[index]
        player_info = source.player_info(player_id)

        if player_info is None or player_info.empty:
            continue

        player_info = _with_career_seasons(player_info, careers, player_id)
        rows_written += players_store.store(player_info)

        if print_debug:
            print(f"players: index {index} of {len(ids)}, player {player_id}")

    return rows_written

def missing_player_ids(source: DataSource) -> list[int]:
    """Players the source knows of that the store holds nothing for."""

    stored = players_store.stored_player_ids()

    return [player.id for player in source.players() if player.id not in stored]

def fill_missing_names(source: DataSource, print_debug: bool = True) -> int:
    """
    Names the held players that have none, reading the source's player list rather than one request
    each. Returns how many rows were rewritten.
    """

    wanted = set(players_store.player_ids_without_names())
    if not wanted:
        return 0

    names = {player.id: player.name for player in source.players() if player.id in wanted}
    if not names:
        return 0

    held = players_store.get_all_players_info()
    named = held[held[players_store.PLAYER_ID.category_name].isin(names)].copy()
    named[players_store.PLAYER_NAME.category_name] = named[players_store.PLAYER_ID.category_name].map(names)

    rows_written = players_store.store(named)

    if print_debug:
        print(f"players: named {rows_written} of {len(wanted)} unnamed players")

    return rows_written

def update(source: DataSource, print_debug: bool = True) -> int:
    """Collects the players that are not held yet, then names any held player still without one."""

    return (
        collect(source, missing_player_ids(source), print_debug=print_debug)
        + fill_missing_names(source, print_debug)
    )

def update_from_games(source: DataSource, date_start: date, print_debug: bool = True) -> int:
    """Collects only players first seen in an already collected game window."""

    stored = players_store.stored_player_ids()
    if not stored:
        return update(source, print_debug)

    player_ids = [
        player_id
        for player_id in player_games.player_ids_since(date_start)
        if player_id not in stored
    ]
    return collect(source, player_ids, print_debug=print_debug)
