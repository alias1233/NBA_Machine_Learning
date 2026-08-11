"""
Predicting one statistic in one game, with a model of any family.

Which model to use is an argument and the family it belongs to decides what else the request has to
name, so adding a family is one entry in PREDICTORS.

Every name typed in is resolved against the stores, so this reaches no data service and works
offline. Collect first, because a prediction is only as current as what is held.
"""

import argparse
from argparse import Namespace
from typing import Callable

from nba_ml import season
from nba_ml.entities import Game
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
from nba_ml.stores import players, teams

SEASON_TYPES = {season_type.name.lower(): season_type for season_type in season.SeasonType}

MOST_LIKELY_OUTCOMES_SHOWN = 5

def _player_id(name: str) -> int:
    found = players.find_by_name(name, limit=1)
    if not found:
        raise SystemExit(f"{name} does not correspond with a stored player. Run nba-collect players.")

    return found[0].id

def _team_id(abbreviation_or_name: str) -> int:
    """Accepts either a tricode such as LAL or a team name, since both are easy to type."""

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
        {_player_id(name) for name in arguments.without},
        {_player_id(name) for name in arguments.returning},
        target_player_team_id=None if arguments.team is None else _team_id(arguments.team),
        print_debug=not arguments.quiet
    )

def _refuse_player_arguments(specification: ModelSpecification, arguments: Namespace):
    """Neither family below reads a player, so naming one is a mistake worth saying out loud."""

    for value, name in (
        (arguments.player, "--player"),
        (arguments.without, "--without"),
        (arguments.returning, "--returning")
    ):
        if value:
            raise SystemExit(f"{name} is only read by a player game statistics model, not {specification.name}.")

def _predict_team_stat(
    specification: ModelSpecification,
    game: Game,
    arguments: Namespace
    ) -> Prediction:

    if arguments.team is None:
        raise SystemExit(f"The {specification.name} model answers about one team, so it needs --team.")

    _refuse_player_arguments(specification, arguments)

    target_team_id = _team_id(arguments.team)
    if target_team_id not in (game.home_team_id, game.away_team_id):
        raise SystemExit(f"{arguments.team} is not playing in this game.")

    return team_stat_inference.predict(
        specification,
        target_team_id,
        game,
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
            "A point differential is the home team's."
        )

    _refuse_player_arguments(specification, arguments)

    return game_stat_inference.predict(specification, game, print_debug=not arguments.quiet)

PREDICTORS: dict[str, Callable[[ModelSpecification, Game, Namespace], Prediction]] = {
    player_stat_specifications.MODEL_CATEGORY: _predict_player_stat,
    team_stat_specifications.MODEL_CATEGORY: _predict_team_stat,
    game_stat_specifications.MODEL_CATEGORY: _predict_game_stat
}
"""What answers with a model of each family, keyed by model category."""

def _print_result(prediction: Prediction, output: ClassDistribution):
    """
    Sixty probabilities are unreadable printed out, so this prints the summary of them.

    The output names every position, so this reads any answer shape. An expected value is only
    printed for an ordered one, since averaging named categories means nothing.
    """

    outcomes = [
        (output.label(position), probability)
        for position, probability in enumerate(prediction.values)
    ]

    print(f"\nBuilt from {prediction.past_games} past games.")

    if output.ordered:
        expected_value = sum(
            (output.first_value + position) * probability
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
        help="Core teammates who played the last game and are out for this one."
    )
    parser.add_argument(
        "--returning",
        nargs="*",
        default=[],
        metavar="PLAYER",
        help="Core teammates who missed the last game and are expected to play this one."
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
