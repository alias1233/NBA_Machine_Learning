"""
Fitting a game statistics model.

Everything about the run itself is shared, in models/classifier_training.py. What is here is what
only this family knows: how its samples are built, and how to describe what one reads.
"""

from datetime import datetime
from functools import partial

from nba_ml import season
from nba_ml.feature_engineering import team_game_rows
from nba_ml.models import classifier_training
from nba_ml.models.classifier_training import TrainingInputs
from nba_ml.models.game_stats import features
from nba_ml.models.game_stats.specifications import MAX_SEQUENCE_LENGTH, GameStatModelSpecification

def _training_inputs(model_specs: GameStatModelSpecification) -> TrainingInputs:
    feature_set = model_specs.get_feature_set()

    return TrainingInputs(
        build_labeled_data=partial(features.get_all_labeled_data, feature_set),
        predicted_value=feature_set.output_column,
        sequence_columns=feature_set.sequence_columns,
        static_columns=feature_set.static_columns,
        minimum_past_games=team_game_rows.MINIMUM_PAST_GAMES,
        max_sequence_length=MAX_SEQUENCE_LENGTH,
        # One sample per game reading both sides, which no column name says, so a build made any
        # other way has to be rebuilt rather than reused.
        build_description=("home rows only", features.SEQUENCES_READ)
    )

def train(
        model_specs: GameStatModelSpecification,
        output_evaluations: bool = True,
        use_cached_build: bool = True,
        save_cached_build: bool = True,
        print_debug: bool = True,
        print_all_debug: bool = False,
        training_start_date: datetime = season.season_start_date(season.COLLECTION_START_SEASON)
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
        training_start_date
    )
