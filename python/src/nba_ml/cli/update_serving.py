"""
Collect and rebuild only while the stored schedule gives the server something to do.

Two windows, because the job answers two questions. The archive catches up on games that have
finished, so it waits for one. The roster describes games that have not, and the site offers those
the whole year round, so it does not.
"""

from datetime import date, timedelta

from nba_ml import season, sources
from nba_ml.cli import build_features, collect
from nba_ml.data_collection import rosters, source_identity
from nba_ml.entities import ScheduledGame
from nba_ml.stores import schedule

def _games_still_to_come(earliest: date) -> list[ScheduledGame]:
    """The real scheduled games from a date onwards. Mock games are added by hand for testing."""

    return [
        scheduled
        for scheduled in schedule.games_on_or_after(earliest)
        if not scheduled.is_mock
    ]


def is_game_window() -> bool:
    """Whether a box score could have finalized since the last hourly run."""

    today = season.today()

    return any(
        scheduled.game.date <= today
        for scheduled in _games_still_to_come(today - timedelta(days=1))
    )


def is_roster_window() -> bool:
    """
    Whether the site is offering a game at all, which is when who will play it is worth knowing.

    Unbounded ahead, unlike the game window. The site offers each team's very next game whenever the
    schedule holds one, and its player pickers are filled from the roster snapshot, so a snapshot
    left to go stale out of season would go on offering players who have since been traded. A
    refresh is a handful of requests and no feature build, so there is nothing to save by waiting
    for the game to come near. Only a schedule that is empty or entirely played stands the job down.
    """

    return bool(_games_still_to_come(season.today() - timedelta(days=1)))


def main():
    if not is_roster_window():
        print("The schedule holds no game still to be played. Nothing collected or rebuilt.")
        return

    source = sources.get_source()
    source_identity.claim(source.name)
    source.set_progress_reporter(print)

    if not is_game_window():
        # Nothing has finished, so nothing to collect or rebuild. Who plays the games in front of us
        # still changes, and that is a handful of requests rather than a feature build.
        rosters.collect(source)
        return

    collect.games.require_resumable_player_archive()
    collect.collect_all(source, refresh_schedule=False)
    build_features.build()


if __name__ == "__main__":
    main()
