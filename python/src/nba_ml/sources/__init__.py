"""
Choosing which service the data comes from.

Adding a source means writing one module beside this one and adding a line to ALL_SOURCES. Nothing
else in the pipeline names a provider.
"""

from nba_ml.sources.base import DataSource
from nba_ml.sources.nba_api_source import NBAApiSource

ALL_SOURCES: dict[str, type[DataSource]] = {
    NBAApiSource.name: NBAApiSource
}

DEFAULT_SOURCE = NBAApiSource.name

def get_source(name: str = DEFAULT_SOURCE, request_interval: float | None = None) -> DataSource:
    """
    Args:
        request_interval overrides how long the source waits between two requests. Leave it unset
        to use the pacing the source asks for.
    """

    if name not in ALL_SOURCES:
        raise ValueError(f"{name} is not a known data source. Known sources: {', '.join(ALL_SOURCES)}.")

    return ALL_SOURCES[name](request_interval)
