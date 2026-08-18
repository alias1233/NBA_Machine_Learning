"""
Training models, of any family.

Which models to fit is an argument and the family each belongs to decides how, so adding a model to a
family's specifications is all it takes to train it. One run fits one named model, or every model that
has not been trained since a given day.

The trainers are listed here rather than in models/families.py because a trainer pulls in the whole
training loop and matplotlib, and the service reads that list.
"""

import argparse
import traceback
from dataclasses import replace
from datetime import datetime
from typing import Any, Callable

from nba_ml import season
from nba_ml.feature_engineering.samples import EvaluationSplit
from nba_ml.models import classifier_training, families, loading
from nba_ml.models.game_stats import specifications as game_stat_specifications
from nba_ml.models.game_stats import training as game_stat_training
from nba_ml.models.player_stats import specifications as player_stat_specifications
from nba_ml.models.player_stats import training as player_stat_training
from nba_ml.models.specifications import ModelSpecification
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

def models_trained_before(day: datetime) -> list[ModelSpecification]:
    """
    Every model whose saved file was written before this day, in the order the families list them.

    A model with no file, or with one that can no longer answer what its specification promises, is
    included however old it is. Those are the models nothing can serve, so they are the ones a
    retraining run is usually after. Pass a day far in the past to get exactly those and nothing else.
    """

    stale = []

    for family in families.ALL_FAMILIES:
        for specification in family.specifications.values():
            trained = loading.trained_at(specification)

            if trained is None or trained < day:
                stale.append(specification)

    return stale

def _selected_models(arguments: argparse.Namespace) -> list[ModelSpecification]:
    """The models this run fits, in the order it fits them."""

    if arguments.retrain_since is not None:
        selected = []

        for specification in models_trained_before(arguments.retrain_since):
            if specification.model_category in TRAINERS:
                selected.append(specification)
            else:
                # Skipped rather than fatal, so one family without a training module yet does not
                # stop the families that have one.
                print(
                    f"Skipping {specification.name}, because the "
                    f"{specification.model_category} family has no training module yet."
                )

        return selected

    found = families.find_model(arguments.model)
    if found is None:
        raise SystemExit(f"No family holds a model named {arguments.model}.")

    _, specification = found
    if specification.model_category not in TRAINERS:
        raise SystemExit(f"The {specification.model_category} family has no training module yet.")

    return [specification]

def _train_one(
    specification: ModelSpecification,
    arguments: argparse.Namespace,
    evaluation_split: EvaluationSplit
    ):
    TRAINERS[specification.model_category](
        specification,
        training_start_date=season.season_start_date(arguments.training_start_season),
        output_evaluations=not arguments.skip_evaluations,
        use_cached_build=not (arguments.rebuild_cache or arguments.no_cache),
        save_cached_build=not arguments.no_cache,
        print_debug=not arguments.quiet,
        evaluation_split=evaluation_split
    )

def main():
    parser = argparse.ArgumentParser(
        description="Trains one model, or every model that has not been trained since a given day, "
                    "and saves each with a report of its run."
    )
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument(
        "--model",
        choices=families.ALL_MODEL_NAMES,
        help="Which model to train, named as it is in its family's specifications.py."
    )
    selection.add_argument(
        "--retrain-since",
        type=datetime.fromisoformat,
        metavar="YYYY-MM-DD",
        help=(
            "Train every model whose saved file was written before this day, one after another, "
            "instead of naming one. A model with no file, or with one that can no longer answer, is "
            "always included, so a day far in the past trains only what nothing can serve today. "
            "Pass --no-cache with this, since each player model would otherwise leave about a "
            "gigabyte of preprocessed build behind."
        )
    )
    parser.add_argument(
        "--training-start-season",
        type=int,
        choices=season.TRAINING_START_SEASONS,
        default=season.ARCHIVE_START_SEASON,
        help=(
            f"First NBA season used for training. Defaults to {season.ARCHIVE_START_SEASON}, which "
            f"is everything held. Seasons before {season.COLLECTION_START_SEASON} are only held "
            "once nba-import-legacy has filled them in."
        )
    )
    parser.add_argument(
        "--evaluation-start",
        type=datetime.fromisoformat,
        metavar="YYYY-MM-DD",
        help=(
            "First day of the games held back for validation and testing. Defaults to a year back "
            "from today. Pin it to score several models on exactly the same games across more than "
            "one day."
        )
    )
    parser.add_argument(
        "--validation-fraction",
        type=float,
        default=classifier_training.VALIDATION_FRACTION,
        metavar="SHARE",
        help=(
            "How much of the held-back period picks the stopping epoch, the rest being the held-out "
            f"test set. Defaults to {classifier_training.VALIDATION_FRACTION}."
        )
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

    selected = _selected_models(arguments)

    if not selected:
        print(f"No model is waiting to be trained since {arguments.retrain_since.date()}.")

        return

    default_split = classifier_training.default_evaluation_split()

    try:
        # Worked out once, so every model of a batch is scored on exactly the same games even where
        # the run crosses midnight.
        evaluation_split = replace(
            default_split,
            start_date=arguments.evaluation_start or default_split.start_date,
            validation_fraction=arguments.validation_fraction
        )
    except ValueError as error:
        raise SystemExit(str(error))

    if len(selected) > 1:
        print(f"Training {len(selected)} models: {', '.join(model.name for model in selected)}.")

    failed = []

    for position, specification in enumerate(selected, start=1):
        if len(selected) > 1:
            print(f"\n===== MODEL {position} OF {len(selected)}: {specification.name} =====")

        try:
            _train_one(specification, arguments, evaluation_split)
        except Exception:
            # A batch carries on, because one family failing is no reason to leave the rest unfitted.
            # The traceback is printed rather than swallowed, and the run still ends in a failure.
            traceback.print_exc()
            failed.append(specification.name)

    if failed:
        raise SystemExit(
            f"\n{len(failed)} of {len(selected)} models failed to train: {', '.join(failed)}. "
            "Each traceback is above."
        )

    if len(selected) > 1:
        print(f"\nTrained all {len(selected)} models.")

if __name__ == '__main__':
    main()
