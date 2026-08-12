"""
Reading the schedule, and putting mock games on it.

Collecting the schedule is `nba-collect schedule`. This command is the other half: seeing which
upcoming games can be predicted and why, and adding games by hand so that the whole path can be
exercised out of season, when the real schedule has nothing on it.

A mock game is stored beside the real ones and is treated exactly like one, including by the
readiness rule in nba_ml/upcoming.py. It carries a flag, so `clear-mock` removes every one of them
in a single step and leaves the collected schedule untouched.
"""

import argparse
from datetime import date, timedelta

from nba_ml import season, upcoming
from nba_ml.entities import Game, GameStatus, ScheduledGame
from nba_ml.stores import schedule, teams

SEASON_TYPES = {season_type.name.lower(): season_type for season_type in season.SeasonType}

DEFAULT_DAYS_LISTED = 7

def _date(text: str) -> date:
    return season.from_date_string(text).date()

def _team_id(abbreviation_or_name: str) -> int:
    team = teams.find(abbreviation_or_name)
    if team is None:
        raise SystemExit(f"{abbreviation_or_name} does not correspond with a stored team. Run nba-collect teams.")

    return team.id

def _abbreviations() -> dict[int, str]:
    return {team.id: team.abbreviation for team in teams.all_teams()}

def _describe(game: ScheduledGame, abbreviations: dict[int, str]) -> str:
    away = abbreviations.get(game.game.away_team_id, str(game.game.away_team_id))
    home = abbreviations.get(game.game.home_team_id, str(game.game.home_team_id))

    return f"{season.to_date_string(game.game.date)}  {away} at {home}"

def _list(arguments: argparse.Namespace):
    games = upcoming.upcoming_games(until=season.today() + timedelta(days=arguments.days))

    if not games:
        print(f"No games scheduled in the next {arguments.days} days. Run nba-collect schedule, or add a mock game.")
        return

    abbreviations = _abbreviations()

    for upcoming_game in games:
        scheduled = upcoming_game.game
        state = "ready" if upcoming_game.ready else f"waiting on {season.to_date_string(upcoming_game.waiting_on)}"
        phase = scheduled.game.season_type.value.replace("_", " ").lower()
        mock = "  (mock)" if scheduled.is_mock else ""

        print(f"{_describe(scheduled, abbreviations)}  {phase:<15} {state}{mock}")

    print(f"\n{sum(upcoming_game.ready for upcoming_game in games)} of {len(games)} can be predicted now.")

def _add_mock(arguments: argparse.Namespace):
    home_team_id = _team_id(arguments.home)
    away_team_id = _team_id(arguments.away)

    if home_team_id == away_team_id:
        raise SystemExit("A game needs two different teams.")

    season_type = SEASON_TYPES[arguments.season_type]
    game = ScheduledGame(
        id=schedule.next_mock_game_id(season_type),
        game=Game(arguments.date, home_team_id, away_team_id, season_type),
        status=GameStatus.SCHEDULED,
        is_mock=True
    )

    schedule.store([game])

    print(f"Added mock game {game.id}: {_describe(game, _abbreviations())}")

def _clear_mock():
    print(f"Removed {schedule.remove_mock_games()} mock games.")

def main():
    parser = argparse.ArgumentParser(description="Reads the schedule and manages mock games for testing.")
    commands = parser.add_subparsers(dest="command", required=True)

    list_command = commands.add_parser("list", help="Show the upcoming games and whether each one can be predicted.")
    list_command.add_argument("--days", type=int, default=DEFAULT_DAYS_LISTED, metavar="N", help="How far ahead to look.")

    add_command = commands.add_parser("add-mock", help="Put one made up game on the schedule.")
    add_command.add_argument("--home", required=True, help="The home team, by tricode or name.")
    add_command.add_argument("--away", required=True, help="The away team, by tricode or name.")
    add_command.add_argument(
        "--date",
        type=_date,
        default=season.today() + timedelta(days=1),
        metavar="YYYY-MM-DD",
        help="Game date. Defaults to tomorrow."
    )
    add_command.add_argument("--season-type", default="regular_season", choices=sorted(SEASON_TYPES))

    commands.add_parser("clear-mock", help="Remove every mock game, leaving the collected schedule alone.")

    arguments = parser.parse_args()

    match arguments.command:
        case "add-mock":
            _add_mock(arguments)
        case "clear-mock":
            _clear_mock()
        case _:
            _list(arguments)

if __name__ == "__main__":
    main()
