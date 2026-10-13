"""Command for running a prediction with any model."""

import argparse
from argparse import Namespace
from typing import Callable

from nba_ml import season
from nba_ml.entities import Game, RosterScenario
from nba_ml.models import families
from nba_ml.models.errors import PredictionRefused
from nba_ml.models.game_stats import inference as game_stat_inference
from nba_ml.models.game_stats import specifications as game_stat_specifications
from nba_ml.models.outputs import ClassDistribution, Prediction
from nba_ml.models.player_stats import inference as player_stat_inference
from nba_ml.models.player_stats import specifications as player_stat_specifications
from nba_ml.models.specifications import ModelSpecification
from nba_ml.models.team_stats import inference as team_stat_inference
from nba_ml.models.team_stats import specifications as team_stat_specifications
from nba_ml.stores import player_games, players, teams

SEASON_TYPES = {season_type.name.lower(): season_type for season_type in season.SeasonType}

MOST_LIKELY_OUTCOMES_SHOWN = 5

def _player_id(name: str) -> int:
    found = players.find_by_name(name, limit=1)
    if not found:
        raise SystemExit(f"{name} does not correspond with a stored player. Run nba-collect players.")

    return found[0].id

def _team_id(abbreviation_or_name: str) -> int:
    team = teams.find(abbreviation_or_name)
    if team is None:
        raise SystemExit(f"{abbreviation_or_name} does not correspond with a stored team. Run nba-collect teams.")

    return team.id

def _predict_player_stat(
    specification: ModelSpecification,
    game: Game,
    arguments: Namespace
    ) -> Prediction:

    if arguments.player is None:
        raise SystemExit(f"The {specification.name} model predicts about a player, so it needs --player.")

    return player_stat_inference.predict(
        specification,
        _player_id(arguments.player),
        game,
        RosterScenario.of(
            (_player_id(name) for name in arguments.without),
            (_player_id(name) for name in arguments.returning)
        ),
        target_player_team_id=None if arguments.team is None else _team_id(arguments.team),
        print_debug=not arguments.quiet
    )

def _refuse_a_named_player(specification: ModelSpecification, arguments: Namespace):
    if arguments.player:
        raise SystemExit(
            f"--player is only read by a player game statistics model, not {specification.name}."
        )

def _side_of(player_id: int, name: str, game: Game) -> int:
    team_id = player_games.latest_team_id(player_id, before=game.date)

    if team_id not in game.team_ids:
        raise SystemExit(f"{name} did not last play for either team in this game.")

    return team_id

def _rosters(game: Game, arguments: Namespace) -> dict[int, RosterScenario]:
    """Returns each team's roster changes from the command line arguments, keyed by team ID."""

    without: dict[int, set[int]] = {team_id: set() for team_id in game.team_ids}
    returning: dict[int, set[int]] = {team_id: set() for team_id in game.team_ids}

    for names, named in ((arguments.without, without), (arguments.returning, returning)):
        for name in names:
            player_id = _player_id(name)
            named[_side_of(player_id, name, game)].add(player_id)

    return {
        team_id: RosterScenario.of(without[team_id], returning[team_id])
        for team_id in game.team_ids
    }

def _predict_team_stat(
    specification: ModelSpecification,
    game: Game,
    arguments: Namespace
    ) -> Prediction:

    if arguments.team is None:
        raise SystemExit(f"The {specification.name} model answers about one team, so it needs --team.")

    _refuse_a_named_player(specification, arguments)

    target_team_id = _team_id(arguments.team)
    if target_team_id not in (game.home_team_id, game.away_team_id):
        raise SystemExit(f"{arguments.team} is not playing in this game.")

    return team_stat_inference.predict(
        specification,
        target_team_id,
        game,
        _rosters(game, arguments),
        print_debug=not arguments.quiet
    )

def _predict_game_stat(
    specification: ModelSpecification,
    game: Game,
    arguments: Namespace
    ) -> Prediction:

    if arguments.team is not None:
        raise SystemExit(
            f"The {specification.name} model answers about the whole game, so it takes no --team. "
            "An answer with a direction, such as a point differential or a win, is the home team's."
        )

    _refuse_a_named_player(specification, arguments)

    return game_stat_inference.predict(
        specification,
        game,
        _rosters(game, arguments),
        print_debug=not arguments.quiet
    )

PREDICTORS: dict[str, Callable[[ModelSpecification, Game, Namespace], Prediction]] = {
    player_stat_specifications.MODEL_CATEGORY: _predict_player_stat,
    team_stat_specifications.MODEL_CATEGORY: _predict_team_stat,
    game_stat_specifications.MODEL_CATEGORY: _predict_game_stat
}

def _print_result(prediction: Prediction, output: ClassDistribution):
    outcomes = [
        (output.label(position), probability)
        for position, probability in enumerate(prediction.values)
    ]

    print(f"\nBuilt from {prediction.past_games} past games.")

    if output.ordered:
        expected_value = sum(
            output.value_of(position) * probability
            for position, probability in enumerate(prediction.values)
        )
        print(f"Expected value: {expected_value:.2f}")

    print("Most likely outcomes:")

    for label, probability in sorted(outcomes, key=lambda outcome: -outcome[1])[:MOST_LIKELY_OUTCOMES_SHOWN]:
        print(f"  {label:>4}  {probability:.4f}")

def main():
    parser = argparse.ArgumentParser(
        description="Predicts the chance of every outcome of one statistic in one game."
    )
    parser.add_argument(
        "--model",
        required=True,
        choices=families.ALL_MODEL_NAMES,
        help="Which model to predict with, named as it is in its family's specifications.py."
    )
    parser.add_argument("--home", required=True, help="The home team, by tricode or name.")
    parser.add_argument("--away", required=True, help="The away team, by tricode or name.")
    parser.add_argument("--date", required=True, help="Game date, as YYYY-MM-DD.")
    parser.add_argument("--season-type", default="regular_season", choices=sorted(SEASON_TYPES))
    parser.add_argument("--player", help="Full player name. Required by a player game statistics model.")
    parser.add_argument(
        "--team",
        help=(
            "A team, by tricode or name. A team statistics model answers about this team. A player "
            "game statistics model only needs it when the player has just moved and no game records "
            "it. A game statistics model takes none, because it answers about the whole game."
        )
    )
    parser.add_argument(
        "--without",
        nargs="*",
        default=[],
        metavar="PLAYER",
        help=(
            "Core players who played the last game and are out for this one. A player model reads "
            "the subject's own team. A team or game model reads both, and a name lands on whichever "
            "of the two sides that player last played for."
        )
    )
    parser.add_argument(
        "--returning",
        nargs="*",
        default=[],
        metavar="PLAYER",
        help="Core players who missed the last game and are expected to play this one."
    )
    parser.add_argument("--quiet", action="store_true", help="Only print the result.")
    arguments = parser.parse_args()

    found = families.find_model(arguments.model)
    if found is None:
        raise SystemExit(f"No family holds a model named {arguments.model}.")

    _, specification = found
    predict = PREDICTORS.get(specification.model_category)
    if predict is None:
        raise SystemExit(f"The {specification.model_category} family has no inference module yet.")

    game = Game(
        season.from_date_string(arguments.date).date(),
        _team_id(arguments.home),
        _team_id(arguments.away),
        SEASON_TYPES[arguments.season_type]
    )

    try:
        prediction = predict(specification, game, arguments)
    except PredictionRefused as refusal:
        raise SystemExit(str(refusal))

    _print_result(prediction, specification.output)

if __name__ == '__main__':
    main()
