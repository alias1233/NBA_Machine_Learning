"""
Predicting one player's stat in one game.

Every name typed in is resolved against the stores, so this reaches no data service and works
offline. Collect first, because a prediction is only as current as what is held.
"""

import argparse

from nba_ml import season
from nba_ml.entities import Game
from nba_ml.models.errors import PredictionRefused
from nba_ml.models.outputs import ClassDistribution, Prediction
from nba_ml.models.player_stats import inference, specifications
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
        print(f"  {label:>3}  {probability:.4f}")

def main():
    parser = argparse.ArgumentParser(
        description="Predicts the chance of every outcome of one player's statistic in one game."
    )
    parser.add_argument("--model", required=True, choices=specifications.MODEL_NAMES, help="Which model to predict with.")
    parser.add_argument("--player", required=True, help="Full player name.")
    parser.add_argument("--home", required=True, help="The home team, by tricode or name.")
    parser.add_argument("--away", required=True, help="The away team, by tricode or name.")
    parser.add_argument("--date", required=True, help="Game date, as YYYY-MM-DD.")
    parser.add_argument("--season-type", default="regular_season", choices=sorted(SEASON_TYPES))
    parser.add_argument(
        "--team",
        help="The player's team, by tricode or name. Only needed when they have just moved and no game records it."
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

    specification = specifications.ALL_MODEL_SPECIFICATIONS[arguments.model]

    game = Game(
        season.from_date_string(arguments.date).date(),
        _team_id(arguments.home),
        _team_id(arguments.away),
        SEASON_TYPES[arguments.season_type]
    )

    try:
        prediction = inference.predict(
            specification,
            _player_id(arguments.player),
            game,
            {_player_id(name) for name in arguments.without},
            {_player_id(name) for name in arguments.returning},
            target_player_team_id=None if arguments.team is None else _team_id(arguments.team),
            print_debug=not arguments.quiet
        )
    except PredictionRefused as refusal:
        raise SystemExit(str(refusal))

    _print_result(prediction, specification.output)

if __name__ == '__main__':
    main()
