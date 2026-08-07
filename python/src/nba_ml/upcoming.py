"""
Which upcoming games can be predicted right now.

A prediction reads both teams' recent form, so a game is only answerable once every game either
team played before it has been collected. Take a game on the 3rd between the Lakers and the
Clippers. If the Clippers also play on the 2nd, then the 3rd cannot be predicted on the 1st,
because the model would be reading a Clippers team that is one game out of date. It becomes
answerable once the game on the 2nd has been played and collected.

That reduces to one rule. For each team, find the earliest game on its schedule that has no box
score stored. A game is ready when neither of its two teams has one of those before it. A team
whose oldest missing game is the game itself is fully collected up to that point.

The rule doubles as a staleness guard. A finished game nobody collected holds back every later
game of both teams, which is exactly what should happen, because predicting against a database
that has not caught up reads a played game as a layoff.
"""

from dataclasses import dataclass
from datetime import date

from nba_ml.entities import GameStatus, ScheduledGame
from nba_ml.stores import schedule, team_games, teams

@dataclass(frozen=True)
class UpcomingGame():
    """A game still to be played, and whether everything needed to predict it is held."""

    game: ScheduledGame
    waiting_on: date | None = None
    """The date of the earliest game still to be collected that holds this one back."""

    @property
    def ready(self) -> bool:
        return self.waiting_on is None

def _oldest_missing_game_dates(
    games: list[ScheduledGame],
    stored_game_ids: set[int]
    ) -> dict[int, date]:
    """Per team, the date of the earliest scheduled game that has no box score stored."""

    oldest: dict[int, date] = {}

    for scheduled in games:
        if scheduled.id in stored_game_ids:
            continue

        for team_id in scheduled.team_ids:
            if scheduled.game.date < oldest.get(team_id, date.max):
                oldest[team_id] = scheduled.game.date

    return oldest

def upcoming_games(until: date | None = None) -> list[UpcomingGame]:
    """
    Every game still to be played from today onwards, each marked ready or held back.

    Args:
        until keeps the answer to games on or before a date. Leave it unset for all of them, which
        costs nothing extra since the whole schedule is read either way.
    """

    games = schedule.all_games()
    if not games:
        return []

    stored_game_ids = team_games.stored_game_ids(min(scheduled.game.date for scheduled in games))
    oldest_missing = _oldest_missing_game_dates(games, stored_game_ids)
    today = date.today()

    still_to_play = []
    for scheduled in games:
        if scheduled.status is not GameStatus.SCHEDULED or scheduled.id in stored_game_ids:
            continue

        if scheduled.game.date < today or (until is not None and scheduled.game.date > until):
            continue

        # Both teams are in oldest_missing, since this game itself has no box score.
        holding_back = [
            oldest_missing[team_id]
            for team_id in scheduled.team_ids
            if oldest_missing[team_id] < scheduled.game.date
        ]

        still_to_play.append(UpcomingGame(scheduled, min(holding_back) if holding_back else None))

    return still_to_play

def predictable_games() -> list[ScheduledGame]:
    """
    The games that can be predicted right now, soonest first.

    Only a team's very next game can qualify, so this is a short list even mid season. Games against
    a team the pipeline holds nothing for are left out, which is what a preseason game against an
    international club looks like. upcoming_games keeps them, since they still count towards the
    rule for the NBA team playing in them.
    """

    known_team_ids = {team.id for team in teams.all_teams()}

    return [
        upcoming_game.game
        for upcoming_game in upcoming_games()
        if upcoming_game.ready and known_team_ids.issuperset(upcoming_game.game.team_ids)
    ]
