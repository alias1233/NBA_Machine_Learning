"""Collect and rebuild only while the stored schedule says NBA games are near."""

from datetime import date, timedelta

from nba_ml import season, sources
from nba_ml.cli import build_features, collect
from nba_ml.data_collection import rosters, source_identity
from nba_ml.stores import schedule

ROSTER_LOOKAHEAD = timedelta(days=2)
"""
How far ahead a game has to be before who is playing in it stops being worth refreshing.

The site only offers each team's very next game, and an injury report is announced on the day, so
this has only to reach the games a reader can actually ask about. It exists because the two halves
of this job answer different questions: the archive catches up on games that have finished, and the
roster describes games that have not.
"""


def _game_scheduled_between(earliest: date, latest: date) -> bool:
    return any(
        not scheduled.is_mock and earliest <= scheduled.game.date <= latest
        for scheduled in schedule.games_on_or_after(earliest)
    )


def is_game_window() -> bool:
    """Whether a box score could have finalized since the last hourly run."""

    today = season.today()
    return _game_scheduled_between(today - timedelta(days=1), today)


def is_roster_window() -> bool:
    """Whether a game near enough to be predicted is worth knowing the rosters for."""

    today = season.today()
    return _game_scheduled_between(today - timedelta(days=1), today + ROSTER_LOOKAHEAD)


def main():
    if not is_roster_window():
        print("No games are scheduled nearby. Nothing collected or rebuilt.")
        return

    source = sources.get_source()
    source_identity.claim(source.name)
    source.set_progress_reporter(print)

    if not is_game_window():
        # Nothing has finished, so nothing to collect or rebuild. Who plays the games in front of us
        # still changes hour by hour, and that is a handful of requests rather than a feature build.
        rosters.collect(source)
        return

    collect.games.require_resumable_player_archive()
    collect.collect_all(source, refresh_schedule=False)
    build_features.build()


if __name__ == "__main__":
    main()
