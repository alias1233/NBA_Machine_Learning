"""
Training one model, of any family.

Which model to fit is an argument and the family it belongs to decides how, so adding a model to a
family's specifications is all it takes to train it.

The trainers are listed here rather than in models/families.py because a trainer pulls in the whole
training loop and matplotlib, and the service reads that list.
"""

import argparse
from typing import Any, Callable

from nba_ml import season
from nba_ml.models import families
from nba_ml.models.game_stats import specifications as game_stat_specifications
from nba_ml.models.game_stats import training as game_stat_training
from nba_ml.models.player_stats import specifications as player_stat_specifications
from nba_ml.models.player_stats import training as player_stat_training
from nba_ml.models.team_stats import specifications as team_stat_specifications
from nba_ml.models.team_stats import training as team_stat_training

TRAINERS: dict[str, Callable[..., Any]] = {
    player_stat_specifications.MODEL_CATEGORY: player_stat_training.train,
    team_stat_specifications.MODEL_CATEGORY: team_stat_training.train,
    game_stat_specifications.MODEL_CATEGORY: game_stat_training.train
}
"""
What fits a model of each family, keyed by model category.

A trainer takes a specification and the keyword arguments below. A family missing from here has no
training module yet.
"""

def main():
    parser = argparse.ArgumentParser(description="Trains one model and saves it with a report of the run.")
    parser.add_argument(
        "--model",
        required=True,
        choices=families.ALL_MODEL_NAMES,
        help="Which model to train, named as it is in its family's specifications.py."
    )
    parser.add_argument(
        "--training-start-season",
        type=int,
        choices=season.TRAINING_START_SEASONS,
        default=season.COLLECTION_START_SEASON,
        help=f"First NBA season used for training. Defaults to {season.COLLECTION_START_SEASON}."
    )
    parser.add_argument(
        "--skip-evaluations",
        action="store_true",
        help="Train and save without scoring the finished model or writing graphs."
    )
    parser.add_argument(
        "--rebuild-cache",
        action="store_true",
        help="Ignore the saved preprocessed build and engineer the features again."
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Neither read nor write the preprocessed build, which is about a gigabyte per model."
    )
    parser.add_argument("--quiet", action="store_true", help="Only print what the training loop reports.")
    arguments = parser.parse_args()

    found = families.find_model(arguments.model)
    if found is None:
        raise SystemExit(f"No family holds a model named {arguments.model}.")

    _, specification = found
    train = TRAINERS.get(specification.model_category)
    if train is None:
        raise SystemExit(f"The {specification.model_category} family has no training module yet.")

    train(
        specification,
        training_start_date=season.season_start_date(arguments.training_start_season),
        output_evaluations=not arguments.skip_evaluations,
        use_cached_build=not (arguments.rebuild_cache or arguments.no_cache),
        save_cached_build=not arguments.no_cache,
        print_debug=not arguments.quiet
    )

if __name__ == '__main__':
    main()
