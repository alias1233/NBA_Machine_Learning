"""Data sources and the lookup for choosing one by name."""

from nba_ml.sources.base import DataSource
from nba_ml.sources.balldontlie_source import BallDontLieSource
from nba_ml.sources.nba_api_source import NBAApiSource

ALL_SOURCES: dict[str, type[DataSource]] = {
    BallDontLieSource.name: BallDontLieSource,
    NBAApiSource.name: NBAApiSource
}

DEFAULT_SOURCE = BallDontLieSource.name

def get_source(name: str = DEFAULT_SOURCE, request_interval: float | None = None) -> DataSource:
    if name not in ALL_SOURCES:
        raise ValueError(f"{name} is not a known data source. Known sources: {', '.join(ALL_SOURCES)}.")

    return ALL_SOURCES[name](request_interval)
