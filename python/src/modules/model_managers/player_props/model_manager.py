from dataclasses import dataclass
from datetime import datetime
from typing import Callable

import numpy as np
import torch, torch.nn as nn
import pandas as pd

from . import data_processor
from .. import directories
from src.components.data_preprocessing import training_data_processing
from src.components.data_preprocessing.training_data_processing import SequenceGameDataset
from src.components.data_preparation import nba_data_helpers
from src.components.machine_learning import helpers
from src.components.machine_learning import evaluation
from src.components.machine_learning import training_report
from src.components.machine_learning import trainer
from src.components.machine_learning.loss_functions.gaussian_smoothed_cross_entropy_loss import GaussianSmoothedCrossEntropyLoss
from src.components.machine_learning.model_architectures.feed_forward import LayerParameters
from src.components.machine_learning.model_architectures.gru_feed_forward import GRUFeedForward

MODEL_CATEGORY = "player_prop"

SEQUENCE_SCALER = 'sequence_scaler'
STATIC_SCALER = 'static_scaler'

# Data
# Note: Whenever data processing changes, the cached processed data not updated until
# the data is reprocessed and saved while LOAD_SAVED_PROCESSED_TRAINING_DATA is false. 
SAVE_PROCESSED_TRAINING_DATA = True
LOAD_SAVED_PROCESSED_TRAINING_DATA = True

RANDOM_SEED = 12156666

CHUNK_STEP_SIZE = 1
VALIDATION_START_DATE = datetime(2026, 1, 1)
TEST_START_DATE = datetime(2026, 3, 1)

DEVICE = helpers.get_best_device()

# How many of the most recent games the GRU reads per prediction, or None for a player's entire history.
MAX_SEQUENCE_LENGTH: int | None = 50

# Training
LossFunctionFactory = Callable[[int], trainer.LossFunction]
"""Builds a loss function once the number of classes is known."""

def cross_entropy_loss(num_classifications: int) -> trainer.LossFunction:
    return nn.CrossEntropyLoss()

def gaussian_smoothed_cross_entropy_loss(sigma: float) -> LossFunctionFactory:
    """
    Spreads each label over its neighbouring classes, so guessing 21 points when 20 happened costs
    less than guessing 40. Set this on a model spec to train against it instead of plain cross entropy.

    Args:
        sigma is how far the label spreads, measured in classes.
    """

    return lambda num_classifications: GaussianSmoothedCrossEntropyLoss(num_classifications, sigma)

@dataclass(frozen=True)
class TrainingParameters():
    """
    Everything that decides how a model is fit, grouped so a run can be logged and repeated as a unit.
    """

    configuration: trainer.TrainingConfiguration
    hidden_layers: list[LayerParameters]
    learning_rate: float
    weight_decay: float = 0.01
    build_loss_function: LossFunctionFactory = cross_entropy_loss

GRU_HIDDEN_DIM = 128
GRU_LAYERS = 1
GRU_DROPOUT_RATE = 0.0

DEFAULT_TRAINING_PARAMETERS = TrainingParameters(
    configuration=trainer.TrainingConfiguration(
        epochs=20,
        batch_size=128,
        patience=7,
        min_delta=0,
        max_gradient_norm=1.0,
        device=DEVICE
    ),
    hidden_layers=[
        LayerParameters(256, nn.ReLU(), True, 0.20),
        LayerParameters(128, nn.ReLU(), True, 0.15),
    ],
    learning_rate=0.000015
)

# Models
@dataclass
class ModelSpecification():
    name: str
    target_stats: list[data_processor.TargetStat]
    minimum_of_stat: int
    number_of_stat_classifications: int
    training_parameters: TrainingParameters = DEFAULT_TRAINING_PARAMETERS
    """Set this to train the stat with parameters other than the shared defaults."""

    def get_feature_set(self) -> data_processor.FeatureSet:
        """
        Resolves which columns this model reads. Resolve it once per run and pass it down, so that
        two models being built at the same time never share column state.
        """

        return data_processor.build_feature_set(self.target_stats)

    def get_save_model_file_path(self) -> str:
        return directories.get_model_save_path(self.name, MODEL_CATEGORY)

    def get_save_training_report_file_path(self) -> str:
        return directories.get_model_save_training_report_path(self.name, MODEL_CATEGORY)

    def get_save_training_data_file_path(self) -> str:
        return directories.get_model_save_training_data_path(self.name, MODEL_CATEGORY)

    def get_save_graphs_directory_path(self) -> str:
        return directories.get_model_save_graphs_directory_path(self.name, MODEL_CATEGORY)

PLAYER_PROPS_POINTS_MODEL = ModelSpecification(
    "points",
    [data_processor.TargetStat.POINTS],
    0,
    60
    )

PLAYER_PROPS_REBOUNDS_MODEL = ModelSpecification(
    "rebounds",
    [data_processor.TargetStat.REBOUNDS],
    0,
    25
    )

PLAYER_PROPS_ASSISTS_MODEL = ModelSpecification(
    "assists",
    [data_processor.TargetStat.ASSISTS],
    0,
    20
    )

PLAYER_PROPS_POINTS_REBOUNDS_ASSISTS_MODEL = ModelSpecification(
    "points_rebounds_assists",
    [data_processor.TargetStat.POINTS,
    data_processor.TargetStat.REBOUNDS,
    data_processor.TargetStat.ASSISTS],
    0,
    80
    )

ALL_MODEL_SPECIFICATIONS = {
    specification.name: specification
    for specification in (
        PLAYER_PROPS_POINTS_MODEL,
        PLAYER_PROPS_REBOUNDS_MODEL,
        PLAYER_PROPS_ASSISTS_MODEL,
        PLAYER_PROPS_POINTS_REBOUNDS_ASSISTS_MODEL
    )
}

def _build_datasets(
        model_specs: ModelSpecification,
        print_debug: bool = False
        ) -> tuple[SequenceGameDataset, SequenceGameDataset, SequenceGameDataset, dict]:
    """
    Builds the three splits and the scalers fitted on the training one, reusing the last run's
    build when it is being loaded and caching it when it is not.

    Returns:
        (training, validation, test, scaler name to fitted scaler)
    """

    file_path = model_specs.get_save_training_data_file_path()

    if LOAD_SAVED_PROCESSED_TRAINING_DATA:
        if print_debug:
            print("Loading in preprocessed data...")

        cached = helpers.load_data_from_file(file_path)

    else:
        labeled_data = data_processor.get_all_player_props_labeled_data(
            model_specs.get_feature_set(),
            VALIDATION_START_DATE,
            TEST_START_DATE,
            CHUNK_STEP_SIZE,
            print_debug
        )

        cached = training_data_processing.build_classification_datasets(
            *labeled_data,
            max_sequence_length=MAX_SEQUENCE_LENGTH,
            min_output_value=model_specs.minimum_of_stat,
            num_classifications=model_specs.number_of_stat_classifications,
            standardize_input=True
        )

        if SAVE_PROCESSED_TRAINING_DATA:
            if print_debug:
                print("Saving preprocessed data...")

            helpers.save_data_to_file(file_path, cached)

    training_dataset, validation_dataset, test_dataset, sequence_scaler, static_scaler = cached

    # Set again after loading so that the window can be changed without rebuilding the cached data.
    for dataset in (training_dataset, validation_dataset, test_dataset):
        dataset.max_sequence_length = MAX_SEQUENCE_LENGTH

    return (
        training_dataset,
        validation_dataset,
        test_dataset,
        {SEQUENCE_SCALER : sequence_scaler, STATIC_SCALER : static_scaler}
    )

def _describe_features(features: data_processor.FeatureSet) -> dict:
    return {
        "predicted value": " + ".join(features.output_columns),
        "past games read": MAX_SEQUENCE_LENGTH if MAX_SEQUENCE_LENGTH is not None else "every game",
        "past games required": data_processor.MINIMUM_PAST_GAMES,
        "columns per past game": len(features.sequence_columns),
        "columns on the game being predicted": len(features.static_columns)
    }

def _list_feature_columns(features: data_processor.FeatureSet) -> str:
    """The exact columns a run consumed, so a saved report can be matched back to its inputs."""

    return "\n\n".join(
        f"{label} ({len(columns)}):\n" + "\n".join(columns)
        for label, columns in (
            ("Past game columns", features.sequence_columns),
            ("Predicted game columns", features.static_columns)
        )
    )

def _describe_data(
    training_dataset: SequenceGameDataset,
    validation_dataset: SequenceGameDataset,
    test_dataset: SequenceGameDataset
    ) -> dict:
    return {
        "training samples": len(training_dataset),
        "validation samples": len(validation_dataset),
        "test samples": len(test_dataset),
        "validation starts": VALIDATION_START_DATE.date(),
        "test starts": TEST_START_DATE.date(),
        "sample step size": CHUNK_STEP_SIZE,
        "random seed": str(RANDOM_SEED)
    }

def _describe_run(training_run: trainer.TrainingRun) -> dict:
    return {
        "epochs completed": training_run.epochs_completed,
        "stopped because it": training_run.stop_reason,
        "best epoch": training_run.best_epoch,
        "best validation loss": training_run.best_validation_loss,
        "loss before training": training_run.initial_validation_loss,
        "training loss at best weights": training_run.final_training_loss,
        "total minutes": training_run.total_seconds / 60,
        **training_run.best_metrics
    }

def _evaluate_saved_model(
        model_specs: ModelSpecification,
        test_dataset: SequenceGameDataset,
        loss_function: trainer.LossFunction,
        training_run: trainer.TrainingRun
    ) -> dict:
    """
    Reloads the model that was just saved and scores it on the held out test set, which also
    proves that the saved file round trips back into a working model.
    """

    save_graphs_directory_path = model_specs.get_save_graphs_directory_path()

    trainer.graph_loss_progress(training_run, save_graphs_directory_path)

    saved_parameters = helpers.load_data_from_file(model_specs.get_save_model_file_path())
    model = GRUFeedForward.load_from_saved_parameters_dict(saved_parameters)

    configuration = model_specs.training_parameters.configuration
    predictions = trainer.predict(
        model,
        test_dataset,
        configuration.batch_size,
        configuration.device,
        training_data_processing.collate_sequence_batch
    )

    # The trainer moved the loss onto the training device, and the predictions come back on the cpu.
    if isinstance(loss_function, nn.Module):
        loss_function = loss_function.cpu()

    test_outputs = test_dataset.outputs
    metrics = {
        "test loss": float(loss_function(predictions, test_outputs)),
        "test cross entropy": float(nn.functional.cross_entropy(predictions, test_outputs))
    }
    metrics.update(evaluation.output_test_evaluation_classification(
        predictions.numpy(),
        test_outputs.numpy(),
        label=model_specs.name,
        ordinal=True,
        output_size=20,
        save_graph_directory_path=save_graphs_directory_path
    ))

    return metrics

def train(
        model_specs: ModelSpecification,
        output_evaluations: bool = True,
        print_debug: bool = True,
        print_all_debug: bool = False,
        ):
    """
    Fits one model spec, saves it, and writes a report of the run next to it.
    """

    if print_all_debug:
        pd.set_option("display.max_rows", 10)
        pd.set_option("display.max_columns", 1000)

    torch.manual_seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    parameters = model_specs.training_parameters

    training_dataset, validation_dataset, test_dataset, scaler_parameters = _build_datasets(
        model_specs,
        print_debug
    )

    model = GRUFeedForward(
        training_dataset.sequence_input_dim,
        training_dataset.static_input_dim,
        model_specs.number_of_stat_classifications,
        parameters.hidden_layers,
        GRU_HIDDEN_DIM,
        GRU_LAYERS,
        GRU_DROPOUT_RATE
    )

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=parameters.learning_rate,
        weight_decay=parameters.weight_decay
    )
    loss_function = parameters.build_loss_function(model_specs.number_of_stat_classifications)

    model_description = training_report.describe_model(model)
    feature_description = _describe_features(model_specs.get_feature_set())
    data_description = _describe_data(training_dataset, validation_dataset, test_dataset)
    label_description = training_data_processing.summarize_classification_outputs(
        training_dataset.outputs,
        model_specs.number_of_stat_classifications
    )
    hyperparameters = {
        "optimizer": type(optimizer).__name__,
        "learning rate": parameters.learning_rate,
        "weight decay": parameters.weight_decay,
        "loss function": loss_function,
        **training_report.values_of(parameters.configuration)
    }

    report = (
        training_report.TrainingReport(f"{model_specs.name} model")
        .add("Model", model_description)
        .add("Features", feature_description)
        .add("Data", data_description)
        .add("Training labels", label_description)
        .add("Hyperparameters", hyperparameters)
        .add_text("Architecture", str(model))
        .add_text("Feature columns", _list_feature_columns(model_specs.get_feature_set()))
    )

    if print_debug:
        print(f"\n===== TRAINING THE {model_specs.name.upper()} MODEL =====")
        training_report.print_values("Model", model_description)
        training_report.print_values("Features", feature_description)
        training_report.print_values("Data", data_description)
        training_report.print_values("Training labels", label_description)
        training_report.print_values("Hyperparameters", hyperparameters)
        print("")

    if print_all_debug:
        print(_list_feature_columns(model_specs.get_feature_set()))
        print("")

    training_run = trainer.train(
        model,
        training_dataset,
        validation_dataset,
        optimizer,
        loss_function,
        parameters.configuration,
        collate_fn=training_data_processing.collate_sequence_batch,
        metrics=evaluation.get_ordinal_classification_metrics()
    )

    report.add("Result", _describe_run(training_run))
    report.add("Epochs", {
        f"epoch {result.epoch}": (
            f"train {result.training_loss:.4f} | val {result.validation_loss:.4f} | "
            + " | ".join(f"{name} {value:.4f}" for name, value in result.metrics.items())
        )
        for result in training_run.epoch_results
    })

    # Saving model data
    save_model_file_path = model_specs.get_save_model_file_path()

    helpers.save_dictionary_data_to_file(
        save_model_file_path,
        [model.get_save_parameters_dict(), scaler_parameters]
    )

    if output_evaluations:
        report.add("Test set", _evaluate_saved_model(
            model_specs,
            test_dataset,
            loss_function,
            training_run
        ))

    report_path = report.write(model_specs.get_save_training_report_file_path())

    if print_debug:
        print(f"\nSaved the model to {save_model_file_path} and its report to {report_path}.")

# Predicting
def predict(
    model_specs: ModelSpecification,
    target_player_id: int,
    target_player_team_id: int,
    target_player_opponent_team_id: int,
    target_game_date: datetime,
    target_game_season_type: nba_data_helpers.SeasonTypes,
    target_game_at_home: bool,
    target_player_removed_core_teammate_player_ids: set[int],
    target_player_added_core_teammate_player_ids: set[int],
    ) -> list[float]:
    """
    Returns the probability of every whole number outcome of the stat this model predicts, from the
    lowest class up.

    See data_processor._get_inference_player_game_data for what the target game arguments mean.
    """

    parameters_dict = helpers.load_data_from_file(model_specs.get_save_model_file_path())
    model = GRUFeedForward.load_from_saved_parameters_dict(parameters_dict)

    player_game_sequences, samples = data_processor.get_player_prop_inference_data(
        model_specs.get_feature_set(),
        target_player_id,
        target_player_team_id,
        target_player_opponent_team_id,
        target_game_date,
        target_game_season_type,
        target_game_at_home,
        target_player_removed_core_teammate_player_ids,
        target_player_added_core_teammate_player_ids,
        print_debug=True
    )

    dataset = training_data_processing.build_inference_dataset(
        player_game_sequences,
        samples,
        MAX_SEQUENCE_LENGTH,
        parameters_dict[SEQUENCE_SCALER],
        parameters_dict[STATIC_SCALER]
    )

    predictions = trainer.predict(
        model,
        dataset,
        collate_fn=training_data_processing.collate_sequence_batch
    )

    predicted_probabilities = torch.softmax(predictions, 1)

    return predicted_probabilities.tolist()[0]