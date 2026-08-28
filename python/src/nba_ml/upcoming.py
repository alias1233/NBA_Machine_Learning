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
from datetime import date, datetime, timedelta, timezone

from nba_ml import season
from nba_ml.entities import GameStatus, ScheduledGame
from nba_ml.stores import schedule, team_games, teams

CANDIDATE_LOOKBACK = timedelta(days=1)
"""
How far back a game still to be played can be dated.

A game's date is a United States eastern date and its tipoff is stored in UTC, so the two can name
different days and a game dated yesterday can still be ahead. A day of slack covers that. See
_candidate_ids.
"""

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
    games: list[schedule.TeamGameDate],
    stored_game_ids: set[int]
    ) -> dict[int, str]:
    """
    Per team, the date of the earliest scheduled game that has no box score stored.

    Dates stay as the text they are stored as, which sorts the same way the days do, so a season of
    games is compared without a date being parsed. See stores/schedule.py.
    """

    oldest: dict[int, str] = {}

    for game_id, game_date, home_team_id, away_team_id in games:
        if game_id in stored_game_ids:
            continue

        for team_id in (home_team_id, away_team_id):
            held = oldest.get(team_id)
            if held is None or game_date < held:
                oldest[team_id] = game_date

    return oldest

def _candidate_ids(
    games: list[schedule.TeamGameDate],
    stored_game_ids: set[int],
    today: date,
    until: date | None
    ) -> list[int]:
    """
    Which games could still be ahead, decided on the stored columns alone.

    Narrowing here rather than after the games are built is what keeps the whole archive from being
    turned into objects, and naming the answer by id is what stops a second read seeing a game the
    rule above was never told about. Dates are compared as the text they are stored as.
    """

    earliest = season.to_date_string(today - CANDIDATE_LOOKBACK)
    latest = None if until is None else season.to_date_string(until)

    return [
        game_id
        for game_id, game_date, _, _ in games
        if game_id not in stored_game_ids
        and game_date >= earliest
        and (latest is None or game_date <= latest)
    ]

def _still_to_play(scheduled: ScheduledGame, now: datetime, today: date) -> bool:
    """
    Whether a game has yet to start.

    The tipoff is the exact answer and is stored in UTC, so it is read first. A game published
    without one falls back to its date, which is a United States eastern date and never the server's.
    """

    if scheduled.tipoff is None:
        return scheduled.game.date >= today

    tipoff = scheduled.tipoff
    if tipoff.tzinfo is None:
        tipoff = tipoff.replace(tzinfo=timezone.utc)

    return tipoff >= now

def upcoming_games(until: date | None = None) -> list[UpcomingGame]:
    """
    Every game still to be played from today onwards, each marked ready or held back.

    Two reads rather than one, and the second asks for exactly what the first picked. The rule needs
    every game the season holds, so that is read as four stored columns and nothing else. Only the
    candidates are read whole, which keeps the archive from being built into objects and keeps both
    reads describing the same set of games however the table moves between them.

    Args:
        until keeps the answer to games on or before a date. Leave it unset for all of them.
    """

    scheduled_dates = schedule.team_game_dates()
    if not scheduled_dates:
        return []

    earliest = min(game_date for _, game_date, _, _ in scheduled_dates)
    stored_game_ids = team_games.stored_game_ids(season.from_date_string(earliest).date())
    oldest_missing = _oldest_missing_game_dates(scheduled_dates, stored_game_ids)
    now = datetime.now(timezone.utc)
    today = season.today()
    candidates = _candidate_ids(scheduled_dates, stored_game_ids, today, until)

    still_to_play = []
    for scheduled in schedule.games_with_ids(candidates):
        if scheduled.status is not GameStatus.SCHEDULED:
            continue

        if not _still_to_play(scheduled, now, today):
            continue

        game_date = season.to_date_string(scheduled.game.date)

        # Both teams are in oldest_missing, since this game has no box score and the read that
        # picked it is the read that built them.
        holding_back = [
            oldest_missing[team_id]
            for team_id in scheduled.team_ids
            if oldest_missing[team_id] < game_date
        ]

        still_to_play.append(
            UpcomingGame(
                scheduled,
                season.from_date_string(min(holding_back)).date() if holding_back else None
            )
        )

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
