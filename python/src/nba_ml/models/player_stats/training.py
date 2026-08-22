"""
Fitting a player game statistics model.

Everything about the run itself is shared, in models/classifier_training.py. What is here is what
only this family knows: how its samples are built, and how to describe what a model of it reads.
"""

from datetime import datetime
from functools import partial

from nba_ml import season
from nba_ml.feature_engineering.samples import EvaluationSplit, SplitKey
from nba_ml.models import classifier_training, metrics
from nba_ml.models.classifier_training import TrainingInputs
from nba_ml.models.player_stats import features as stat_features
from nba_ml.models.player_stats.specifications import (
    MAX_SEQUENCE_LENGTH,
    PlayerStatModelSpecification
)

def _training_inputs(model_specs: PlayerStatModelSpecification) -> TrainingInputs:
    feature_set = model_specs.get_feature_set()

    return TrainingInputs(
        build_labeled_data=partial(stat_features.get_all_labeled_data, feature_set),
        predicted_value=feature_set.combination.describe(feature_set.output_columns),
        sequence_columns=feature_set.sequence_columns,
        static_columns=feature_set.static_columns,
        minimum_past_games=stat_features.MINIMUM_PAST_GAMES,
        max_sequence_length=MAX_SEQUENCE_LENGTH,
        # A thousand players halve cleanly, so validation and test share nobody and the epoch a run
        # stops on cannot have been picked on the players it is then scored against.
        split_on=SplitKey.SUBJECT
    )

def train(
        model_specs: PlayerStatModelSpecification,
        output_evaluations: bool = True,
        use_cached_build: bool = True,
        save_cached_build: bool = True,
        print_debug: bool = True,
        print_all_debug: bool = False,
        training_start_date: datetime = season.season_start_date(season.ARCHIVE_START_SEASON),
        evaluation_split: EvaluationSplit | None = None
        ) -> classifier_training.TrainingResult:
    """Fits one model spec, saves it, and writes a report of the run next to it."""

    return classifier_training.train(
        model_specs,
        _training_inputs(model_specs),
        output_evaluations,
        use_cached_build,
        save_cached_build,
        print_debug,
        print_all_debug,
        training_start_date,
        evaluation_split
    )

def rescore(
        model_specs: PlayerStatModelSpecification,
        print_debug: bool = True
        ) -> metrics.ModelEvaluation:
    """Rewrites a saved model's held-out evaluation without fitting it again."""

    return classifier_training.rescore(model_specs, _training_inputs(model_specs), print_debug)
