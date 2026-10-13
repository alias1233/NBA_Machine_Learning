"""Imports seasons older than the data source covers from a legacy nba.com archive."""

import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from types import ModuleType
from typing import Iterator

import pandas as pd

from nba_ml import paths, season
from nba_ml.data_collection import games, players as player_collection
from nba_ml.season import SeasonType
from nba_ml.sources.base import PLAYER_GAME_BATCH_SIZE
from nba_ml.stores import player_games, players, team_games, teams

LEGACY_PLAYER_ID_BASE = 10_000_000_000_000
"""Offset added to the IDs of players that only exist in the legacy archive."""

LEGACY_GAME_ID_BASE = 10_000_000_000_000
"""Offset added to the IDs of imported legacy games."""

MINIMUM_MATCHING_GAMES = 3
"""Number of games with identical stat lines needed to treat two player IDs as the same player."""

IMPORTED_PHASES = {
    season.GAME_ID_PREFIXES[SeasonType.REGULAR_SEASON]: season.GAME_ID_PREFIXES[SeasonType.REGULAR_SEASON],
    season.GAME_ID_PREFIXES[SeasonType.PLAYOFFS]: season.GAME_ID_PREFIXES[SeasonType.PLAYOFFS],
    # The data source labels play-in games as regular season, so do the same here.
    season.GAME_ID_PREFIXES[SeasonType.PLAY_IN]: season.GAME_ID_PREFIXES[SeasonType.REGULAR_SEASON]
}

MATCHING_COLUMNS = (
    player_games.FIELD_GOALS_MADE,
    player_games.FIELD_GOALS_ATTEMPTED,
    player_games.THREE_POINTERS_MADE,
    player_games.THREE_POINTERS_ATTEMPTED,
    player_games.FREE_THROWS_MADE,
    player_games.FREE_THROWS_ATTEMPTED,
    player_games.OFFENSIVE_REBOUNDS,
    player_games.DEFENSIVE_REBOUNDS,
    player_games.ASSISTS,
    player_games.STEALS,
    player_games.BLOCKS,
    player_games.TURNOVERS,
    player_games.PERSONAL_FOULS,
    player_games.PLUS_MINUS
)
"""Stats compared when matching players between archives. Minutes are left out because the two sources differ."""

GAME_KEY = "GAME_KEY"
"""Column with a game key built from the date and both team IDs, since game IDs differ between archives."""

LEGACY_PLAYER_ID = "LEGACY_PLAYER_ID"

PLAYER_ID = player_games.PLAYER_ID.category_name
GAME_ID = player_games.GAME_ID.category_name
TEAM_ID = player_games.TEAM_ID.category_name
GAME_DATE = player_games.GAME_DATE.category_name
SEASON_TYPE = player_games.SEASON_TYPE.category_name
MINUTES = player_games.MINUTES_PLAYED.category_name


@dataclass
class ImportReport():
    """Summary of an import run."""

    games: int = 0
    player_rows: int = 0
    team_rows: int = 0
    player_info_rows: int = 0
    refreshed_careers: int = 0
    joined_players: int = 0
    legacy_only_players: int = 0
    skipped_games: int = 0
    oldest_game: date | None = None
    newest_game: date | None = None
    unmapped_teams: tuple[int, ...] = field(default_factory=tuple)
    unjoined_players: tuple[int, ...] = field(default_factory=tuple)
    """Legacy players who played after the cutoff but could not be matched."""

    players_without_information: tuple[int, ...] = field(default_factory=tuple)
    """Imported players with no row in the player info store."""

    def describe(self) -> str:
        lines = [
            f"Imported {self.player_rows} player rows over {self.games} games, "
            f"{self.oldest_game} to {self.newest_game}, and rebuilt {self.team_rows} team rows.",
            f"Joined {self.joined_players} players onto identifiers already held and gave "
            f"{self.legacy_only_players} players of the older era one of their own.",
            f"Wrote {self.player_info_rows} player information rows and refreshed the career years "
            f"of {self.refreshed_careers} players.",
            f"Left out {self.skipped_games} legacy games as preseason, unmodelled or incomplete."
        ]
        if self.unmapped_teams:
            lines.append(f"No held team matched {len(self.unmapped_teams)} legacy team ids: {self.unmapped_teams}.")
        if self.unjoined_players:
            lines.append(
                f"{len(self.unjoined_players)} legacy players played after the cutoff and were not "
                f"recognised, so each reads as two careers: {self.unjoined_players[:20]}."
            )
        if self.players_without_information:
            lines.append(
                f"{len(self.players_without_information)} imported players have no information row, "
                "so their games will not be built. Run `nba-collect players` and import again."
            )
        return "\n".join(lines)


def _read_table(legacy_directory: Path, store: ModuleType) -> pd.DataFrame:
    """Reads a store's table from the legacy data directory in read-only mode."""

    database_file = legacy_directory / paths.DATABASE_DIRECTORY.name / store.FILEPATH.name
    if not database_file.exists():
        raise RuntimeError(f"The legacy archive at {legacy_directory} has no {store.FILEPATH.name}.")

    columns = ",".join(store.DATABASE.category_names)
    with closing(sqlite3.connect(f"{database_file.resolve().as_uri()}?mode=ro", uri=True)) as database:
        return pd.read_sql(f"SELECT {columns} FROM {store.NAME}", database)


def _team_id_mapping(legacy_directory: Path) -> dict[int, int]:
    """Maps legacy team IDs to current ones by abbreviation."""

    held = {team.abbreviation: team.id for team in teams.all_teams()}
    if not held:
        raise RuntimeError("Nothing to import onto. Collect the teams first with `nba-collect teams`.")

    legacy = _read_table(legacy_directory, teams)
    abbreviation = teams.ABBREVIATION.category_name
    matched = legacy[legacy[abbreviation].isin(held)]
    if matched[abbreviation].duplicated().any():
        raise RuntimeError("The legacy archive gives one tricode to more than one team.")

    return {
        int(team_id): held[tricode]
        for team_id, tricode in zip(matched[teams.TEAM_ID.category_name], matched[abbreviation])
    }


def _with_game_keys(rows: pd.DataFrame) -> pd.DataFrame:
    """Adds the GAME_KEY column and drops rows whose game has no unique key."""

    by_game = rows.groupby(GAME_ID, sort=False).agg(
        day=(GAME_DATE, "min"),
        first_team=(TEAM_ID, "min"),
        second_team=(TEAM_ID, "max")
    )
    named = by_game[by_game["first_team"] != by_game["second_team"]]
    keys = named["day"] + "|" + named["first_team"].astype(str) + "|" + named["second_team"].astype(str)
    keys = keys[~keys.duplicated(keep=False)]

    return rows.assign(**{GAME_KEY: rows[GAME_ID].map(keys)}).dropna(subset=[GAME_KEY])


def _recognisable_lines(rows: pd.DataFrame) -> pd.DataFrame:
    """Returns the rows whose stat line is unique within their team's game."""

    columns = [GAME_KEY, TEAM_ID, *(column.category_name for column in MATCHING_COLUMNS)]
    lines = _with_game_keys(rows)[[PLAYER_ID, *columns]]

    return lines[~lines.duplicated(columns, keep=False)]


def _player_id_mapping(
    legacy_overlap: pd.DataFrame,
    current_overlap: pd.DataFrame,
    minimum_matching_games: int
    ) -> dict[int, int]:
    """Maps legacy player IDs to current ones by matching stat lines in games both archives have."""

    if legacy_overlap.empty or current_overlap.empty:
        return {}

    paired = _recognisable_lines(legacy_overlap).merge(
        _recognisable_lines(current_overlap),
        on=[GAME_KEY, TEAM_ID, *(column.category_name for column in MATCHING_COLUMNS)],
        suffixes=("_legacy", "_current")
    )
    if paired.empty:
        return {}

    agreed = paired.value_counts([f"{PLAYER_ID}_legacy", f"{PLAYER_ID}_current"])
    mapping: dict[int, int] = {}
    claimed: set[int] = set()
    for (legacy_id, current_id), games_agreeing in agreed.items():
        if games_agreeing < minimum_matching_games or legacy_id in mapping or current_id in claimed:
            continue
        mapping[int(legacy_id)] = int(current_id)
        claimed.add(int(current_id))

    return mapping


def _played_rows(rows: pd.DataFrame, team_ids: dict[int, int]) -> pd.DataFrame:
    """Returns the rows from games that are complete and played between two known teams."""

    required = [name for name in player_games.DATABASE.category_names if name != SEASON_TYPE]
    played = rows[rows[MINUTES].fillna(0) > 0]
    by_game = played.groupby(GAME_ID, sort=False)

    usable = played[required].notna().all(axis=1) & played[TEAM_ID].isin(team_ids)
    whole = usable.groupby(played[GAME_ID], sort=False).transform("all")
    both_sides = by_game[TEAM_ID].transform("nunique") == 2

    return played[whole & both_sides]


def _imported_phases(rows: pd.DataFrame) -> pd.DataFrame:
    """Fills in each row's season type and drops season types that are not imported."""

    stored = rows[SEASON_TYPE].astype("string")
    phases = stored.fillna(rows[GAME_ID].astype(str).str[0]).map(IMPORTED_PHASES)
    kept = rows[phases.notna()].copy()
    kept[SEASON_TYPE] = phases[phases.notna()]

    return kept


def _batches(rows: pd.DataFrame, size: int = PLAYER_GAME_BATCH_SIZE) -> Iterator[pd.DataFrame]:
    """Yields the rows in batches of roughly `size` without splitting a game."""

    rows = rows.sort_values(GAME_ID)
    batch_of_game = (rows.groupby(GAME_ID, sort=False).size().cumsum() - 1) // size

    for _, batch in rows.groupby(rows[GAME_ID].map(batch_of_game), sort=True):
        yield batch


def _check_provider_ids(rows: pd.DataFrame):
    """Raises an error if a collected ID falls in the range reserved for imported rows."""

    for column, base in ((PLAYER_ID, LEGACY_PLAYER_ID_BASE), (GAME_ID, LEGACY_GAME_ID_BASE)):
        if not rows.empty and rows[column].max() >= base:
            raise RuntimeError(
                f"A collected {column} is at or above {base}, which is the range imported rows use. "
                "Raise the reserved base in nba_ml/data_collection/legacy_archive.py."
            )


def _import_player_information(
    legacy_directory: Path,
    player_ids: dict[int, int],
    played: set[int]
    ) -> int:
    """Stores player info for imported players that don't have any yet. Returns the number of rows written."""

    legacy = _read_table(legacy_directory, players)
    person_id = players.PLAYER_ID.category_name
    legacy[person_id] = legacy[person_id].map(player_ids)
    wanted = legacy[legacy[person_id].isin(played - players.stored_player_ids())]

    return 0 if wanted.empty else players.store(wanted)


def import_games(
    legacy_directory: Path,
    until: date = season.PLAYER_GAME_COLLECTION_START_DATE,
    minimum_matching_games: int = MINIMUM_MATCHING_GAMES,
    print_debug: bool = True
    ) -> ImportReport:
    """Imports legacy games played before the `until` date and returns a report."""

    def report_progress(message: str):
        if print_debug:
            print(message)

    cutoff = season.to_date_string(until)
    current_overlap = player_games.get_game_data_after_date(until)
    if current_overlap.empty:
        raise RuntimeError(
            f"Nothing is stored from {cutoff} onwards, so no legacy player can be recognised and "
            "every one of them would be imported as somebody the archive has never seen. Collect "
            "from the data source first."
        )
    _check_provider_ids(current_overlap)

    report = ImportReport()
    legacy_rows = _read_table(legacy_directory, player_games)
    if legacy_rows.empty:
        raise RuntimeError(f"The legacy archive at {legacy_directory} holds no player games.")

    before_cutoff = legacy_rows[GAME_DATE] < cutoff
    held_games = legacy_rows.loc[before_cutoff, GAME_ID].nunique()

    team_ids = _team_id_mapping(legacy_directory)
    report.unmapped_teams = tuple(sorted(set(legacy_rows[TEAM_ID].unique()) - set(team_ids)))
    report_progress(f"Matched {len(team_ids)} of the legacy archive's teams onto the ones held.")

    legacy_rows = _played_rows(legacy_rows, team_ids)
    legacy_rows[TEAM_ID] = legacy_rows[TEAM_ID].map(team_ids)
    overlap = legacy_rows[legacy_rows[GAME_DATE] >= cutoff]

    joined = _player_id_mapping(overlap, current_overlap, minimum_matching_games)
    report.joined_players = len(joined)
    report_progress(f"Recognised {len(joined)} legacy players in the games both archives hold.")

    imported = _imported_phases(legacy_rows[legacy_rows[GAME_DATE] < cutoff])
    if imported.empty:
        raise RuntimeError(f"The legacy archive holds no complete modelled game before {cutoff}.")

    report.unjoined_players = tuple(sorted(
        (set(imported[PLAYER_ID].unique()) & set(overlap[PLAYER_ID].unique())) - set(joined)
    ))

    player_ids = {
        int(legacy_id): joined.get(int(legacy_id), LEGACY_PLAYER_ID_BASE + int(legacy_id))
        for legacy_id in legacy_rows[PLAYER_ID].unique()
    }
    imported[PLAYER_ID] = imported[PLAYER_ID].map(player_ids)
    imported[GAME_ID] = LEGACY_GAME_ID_BASE + imported[GAME_ID]

    played = set(imported[PLAYER_ID].unique())
    report.games = imported[GAME_ID].nunique()
    report.skipped_games = held_games - report.games
    report.oldest_game = season.from_date_string(imported[GAME_DATE].min()).date()
    report.newest_game = season.from_date_string(imported[GAME_DATE].max()).date()
    report.legacy_only_players = sum(1 for player_id in played if player_id >= LEGACY_PLAYER_ID_BASE)

    for batch in _batches(imported):
        report.player_rows += player_games.store(batch)
        report_progress(f"legacy games: stored {report.player_rows} of {len(imported)} rows")

    report.player_info_rows = _import_player_information(legacy_directory, player_ids, played)
    report.refreshed_careers = player_collection.refresh_career_seasons(print_debug)
    report.players_without_information = tuple(sorted(played - players.stored_player_ids()))
    report.team_rows = games.collect_team_games(
        date_from=report.oldest_game,
        date_to=until - timedelta(days=1),
        print_debug=print_debug
    )

    return report
