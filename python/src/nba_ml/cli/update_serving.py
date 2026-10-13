"""Command for the server's hourly update. It only collects and rebuilds when scheduled games need it."""

from datetime import date, timedelta

from nba_ml import season, sources
from nba_ml.cli import build_features, collect
from nba_ml.data_collection import rosters, source_identity
from nba_ml.entities import ScheduledGame
from nba_ml.stores import schedule

def _games_still_to_come(earliest: date) -> list[ScheduledGame]:
    return [
        scheduled
        for scheduled in schedule.games_on_or_after(earliest)
        if not scheduled.is_mock
    ]


def is_game_window() -> bool:
    """Returns True if a real game is scheduled for yesterday or today."""

    today = season.today()

    return any(
        scheduled.game.date <= today
        for scheduled in _games_still_to_come(today - timedelta(days=1))
    )


def is_roster_window() -> bool:
    """Returns True if the schedule has a real game from yesterday onwards."""

    return bool(_games_still_to_come(season.today() - timedelta(days=1)))


def main():
    if not is_roster_window():
        print("The schedule holds no game still to be played. Nothing collected or rebuilt.")
        return

    source = sources.get_source()
    source_identity.claim(source.name)
    source.set_progress_reporter(print)

    if not is_game_window():
        rosters.collect(source)
        return

    collect.games.require_resumable_player_archive()
    collect.collect_all(source, refresh_schedule=False)
    build_features.build()


if __name__ == "__main__":
    main()
