"""Makes sure a data directory is only used with one data source, since IDs differ between sources."""

from nba_ml import paths

MARKER = paths.DATA_DIRECTORY / "data_source"
LEGACY_SOURCE = "nba_api"

def claim(source_name: str):
    """Marks the data directory as belonging to a source. Raises an error if it belongs to another one."""

    if MARKER.exists():
        held = MARKER.read_text(encoding="utf-8").strip()
        if held != source_name:
            raise RuntimeError(
                f"This data directory belongs to {held}, not {source_name}. "
                "Use a separate NBA_ML_DATA_DIR for each source."
            )
        return

    has_databases = paths.DATABASE_DIRECTORY.exists() and any(paths.DATABASE_DIRECTORY.glob("*.db"))
    if has_databases and source_name != LEGACY_SOURCE:
        raise RuntimeError(
            "This unmarked data directory contains legacy nba_api databases. "
            "Use an empty NBA_ML_DATA_DIR for balldontlie."
        )

    paths.DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)
    working = MARKER.with_suffix(".incomplete")
    working.write_text(source_name + "\n", encoding="utf-8")
    working.replace(MARKER)
