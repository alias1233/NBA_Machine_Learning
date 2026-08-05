"""
Collecting NBA data into the local stores.

Every choice is a command line argument and nothing is asked for at a prompt, so the command a
person runs by hand is the same command a scheduled job runs.
"""

import argparse
from datetime import date

from nba_ml import season, sources
from nba_ml.data_collection import games, players, teams
from nba_ml.season import SeasonType
from nba_ml.sources.base import DataSource
from nba_ml.stores import player_games

SEASON_TYPES = {season_type.name.lower(): season_type for season_type in SeasonType}

def _date(text: str) -> date:
    return season.from_date_string(text).date()

def _season_types(names: list[str]) -> list[SeasonType] | None:
    return [SEASON_TYPES[name] for name in names] if names else None

def _add_game_arguments(parser: argparse.ArgumentParser):
    parser.add_argument(
        "--since",
        type=_date,
        metavar="YYYY-MM-DD",
        help="Only games played on or after this date. Defaults to the newest game already stored."
    )
    parser.add_argument("--until", type=_date, metavar="YYYY-MM-DD", help="Only games played on or before this date.")
    parser.add_argument(
        "--seasons",
        nargs="+",
        type=int,
        metavar="YEAR",
        help="Seasons to collect, each named by the year it starts in."
    )
    parser.add_argument("--season-types", nargs="+", default=[], choices=sorted(SEASON_TYPES))
    parser.add_argument("--all-seasons", action="store_true", help="Collect every season the source has.")

def _collect_games(
    source: DataSource,
    arguments: argparse.Namespace,
    for_teams: bool
    ) -> int:
    collect = games.collect_team_games if for_teams else games.collect_player_games
    update = games.update_team_games if for_teams else games.update_player_games
    chose_what_to_collect = arguments.all_seasons or arguments.seasons or arguments.since or arguments.until

    if not chose_what_to_collect:
        return update(source, print_debug=not arguments.quiet)

    return collect(
        source,
        seasons=arguments.seasons,
        season_types=_season_types(arguments.season_types),
        date_from=arguments.since,
        date_to=arguments.until,
        print_debug=not arguments.quiet
    )

def _collect_players(source: DataSource, arguments: argparse.Namespace) -> int:
    print_debug = not arguments.quiet

    if arguments.ids:
        player_ids = arguments.ids
    elif arguments.since:
        player_ids = player_games.player_ids_since(arguments.since)
    elif arguments.all:
        player_ids = None
    else:
        player_ids = players.missing_player_ids(source)

    return players.collect(source, player_ids, arguments.start_index, print_debug)

def main():
    parser = argparse.ArgumentParser(description="Collects NBA data into the local stores.")
    parser.add_argument("--source", default=sources.DEFAULT_SOURCE, choices=sorted(sources.ALL_SOURCES))
    parser.add_argument(
        "--wait",
        type=float,
        metavar="SECONDS",
        help="How long to leave between two requests. Defaults to the pacing the source asks for."
    )
    parser.add_argument("--quiet", action="store_true", help="Only print the total collected.")

    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("all", help="Collect every team, player and game that is not stored yet.")

    commands.add_parser("teams", help="Collect the thirty teams and their tricodes.")

    players_command = commands.add_parser("players", help="Collect player information, one request per player.")
    players_command.add_argument("--all", action="store_true", help="Collect every player the source knows of.")
    players_command.add_argument(
        "--since",
        type=_date,
        metavar="YYYY-MM-DD",
        help="Collect the players who have played a game on or after this date."
    )
    players_command.add_argument("--ids", nargs="+", type=int, metavar="ID", help="Collect these players.")
    players_command.add_argument(
        "--start-index",
        type=int,
        default=0,
        metavar="N",
        help="Skip to this position in the list, which picks a stopped run back up."
    )

    player_games_command = commands.add_parser("player-games", help="Collect finished player box scores.")
    _add_game_arguments(player_games_command)

    team_games_command = commands.add_parser("team-games", help="Collect finished team box scores.")
    _add_game_arguments(team_games_command)

    arguments = parser.parse_args()
    source = sources.get_source(arguments.source, arguments.wait)
    print_debug = not arguments.quiet

    match arguments.command:
        case "teams":
            rows_written = teams.collect(source, print_debug)
        case "players":
            rows_written = _collect_players(source, arguments)
        case "player-games":
            rows_written = _collect_games(source, arguments, for_teams=False)
        case "team-games":
            rows_written = _collect_games(source, arguments, for_teams=True)
        case _:
            rows_written = (
                teams.collect(source, print_debug)
                + games.update_player_games(source, print_debug)
                + games.update_team_games(source, print_debug)
                + players.update(source, print_debug)
            )

    print(f"Wrote {rows_written} rows.")

if __name__ == "__main__":
    main()
