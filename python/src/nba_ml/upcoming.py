"""Finds the upcoming games that can be predicted."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from nba_ml import season
from nba_ml.entities import GameStatus, ScheduledGame
from nba_ml.stores import schedule, team_games, teams

CANDIDATE_LOOKBACK = timedelta(days=1)
"""Unplayed games dated up to this long before today still count as upcoming."""

@dataclass(frozen=True)
class UpcomingGame():
    """An unplayed game and whether the data needed to predict it has been collected."""

    game: ScheduledGame
    waiting_on: date | None = None
    """Date of the earliest uncollected game this one is waiting on. None if it is ready."""

    @property
    def ready(self) -> bool:
        return self.waiting_on is None

def _oldest_missing_game_dates(
    games: list[schedule.TeamGameDate],
    stored_game_ids: set[int]
    ) -> dict[int, str]:
    """Returns each team's earliest scheduled game date that has no stored box score."""

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
    """Returns the IDs of games with no box score, dated from the lookback start up to `until`."""

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
    """Returns True if the game has not started yet."""

    if scheduled.tipoff is None:
        return scheduled.game.date >= today

    tipoff = scheduled.tipoff
    if tipoff.tzinfo is None:
        tipoff = tipoff.replace(tzinfo=timezone.utc)

    return tipoff >= now

def upcoming_games(until: date | None = None) -> list[UpcomingGame]:
    """Returns every unplayed game from today onwards, with the date each is waiting on, if any."""

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
    """Returns the upcoming games that are ready to predict, earliest first."""

    known_team_ids = {team.id for team in teams.all_teams()}

    return [
        upcoming_game.game
        for upcoming_game in upcoming_games()
        if upcoming_game.ready and known_team_ids.issuperset(upcoming_game.game.team_ids)
    ]
