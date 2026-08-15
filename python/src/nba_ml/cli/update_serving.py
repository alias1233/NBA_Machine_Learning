"""Collect and rebuild only while the stored schedule says NBA games are in progress."""

from datetime import timedelta

from nba_ml import season, sources
from nba_ml.cli import build_features, collect
from nba_ml.data_collection import source_identity
from nba_ml.stores import schedule


def is_game_window() -> bool:
    """Whether a box score could have finalized since the last hourly run."""

    today = season.today()
    earliest = today - timedelta(days=1)
    return any(
        not scheduled.is_mock and earliest <= scheduled.game.date <= today
        for scheduled in schedule.games_on_or_after(earliest)
    )


def main():
    if not is_game_window():
        print("No games are scheduled today or yesterday. Nothing collected or rebuilt.")
        return

    collect.games.require_resumable_player_archive()
    source = sources.get_source()
    source_identity.claim(source.name)
    source.set_progress_reporter(print)
    collect.collect_all(source, refresh_schedule=False)
    build_features.build()


if __name__ == "__main__":
    main()
