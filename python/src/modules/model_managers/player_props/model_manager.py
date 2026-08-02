from dataclasses import dataclass, field
import numpy as np
import torch, torch.nn as nn
import pandas as pd
from datetime import datetime
from enum import Enum
from sklearn.preprocessing import StandardScaler
from torch.utils.data import Dataset, TensorDataset
from typing import Callable
import math

from src.components.machine_learning import helpers
from src.components.machine_learning import evaluation
from src.components.machine_learning import training_report

from . import data_processor
from .. import directories
from src.components.data_preprocessing import training_data_processing
from src.components.data_preparation import nba_data_helpers
from src.components.machine_learning import trainer
from src.components.machine_learning.loss_functions.gaussian_smoothed_cross_entropy_loss import GaussianSmoothedCrossEntropyLoss
from src.components.machine_learning.model_architectures.feed_forward import FeedForward, LayerParameters
from src.components.machine_learning.model_architectures.gru_feed_forward import GRUFeedForward
from src.components.machine_learning.model_architectures.savable_module import SavableModule

MODEL_CATEGORY = "player_prop"

INPUT_SCALER = 'input_scaler'
SEQUENCE_SCALER = 'sequence_scaler'
STATIC_SCALER = 'static_scaler'

class Architecture(Enum):
    """
    FEED_FORWARD flattens a fixed window of past games into one input vector.
    GRU reads the past games as a sequence and pairs its final hidden state with the static data.
    """

    FEED_FORWARD = "feed_forward"
    GRU = "gru"

# Data
SAVE_PROCESSED_TRAINING_DATA = True
LOAD_SAVED_PROCESSED_TRAINING_DATA = True

RANDOM_SEED = 12156666

CHUNK_STEP_SIZE = 1
VALIDATION_START_DATE = datetime(2026, 1, 1)
TEST_START_DATE = datetime(2026, 3, 1)

DEVICE = helpers.get_best_device()

# How many of the most recent games the GRU reads per prediction, or None for a player's entire history.
MAX_SEQUENCE_LENGTH: int | None = 100

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

FEED_FORWARD_TRAINING_PARAMETERS = TrainingParameters(
    configuration=trainer.TrainingConfiguration(
        epochs=25,
        batch_size=128,
        patience=9,
        min_delta=0.001,
        device=DEVICE
    ),
    hidden_layers=[
        LayerParameters(512, nn.ReLU(), True, 0.4),
        LayerParameters(256, nn.ReLU(), True, 0.3),
        LayerParameters(256, nn.ReLU(), True, 0.3),
        LayerParameters(128, nn.ReLU(), True, 0.2),
    ],
    learning_rate=0.000005
)

GRU_HIDDEN_DIM = 128
GRU_LAYERS = 1
GRU_DROPOUT_RATE = 0.0

GRU_TRAINING_PARAMETERS = TrainingParameters(
    configuration=trainer.TrainingConfiguration(
        epochs=25,
        batch_size=128,
        patience=7,
        min_delta=0.001,
        max_gradient_norm=1.0,
        device=DEVICE
    ),
    hidden_layers=[
        LayerParameters(256, nn.ReLU(), True, 0.3),
        LayerParameters(128, nn.ReLU(), True, 0.2),
    ],
    learning_rate=0.000033
)

DEFAULT_TRAINING_PARAMETERS = {
    Architecture.FEED_FORWARD: FEED_FORWARD_TRAINING_PARAMETERS,
    Architecture.GRU: GRU_TRAINING_PARAMETERS
}

# Models
@dataclass
class ModelSpecification():
    name: str
    target_stats: list[data_processor.TargetStat]
    minimum_of_stat: int
    number_of_stat_classifications: int
    training_parameter_overrides: dict[Architecture, TrainingParameters] = field(default_factory=dict)
    """Set an architecture here to train this stat with parameters other than the shared defaults."""

    def get_training_parameters(self, architecture: Architecture) -> TrainingParameters:
        return self.training_parameter_overrides.get(architecture, DEFAULT_TRAINING_PARAMETERS[architecture])

    def _get_path_name(self, architecture: Architecture) -> str:
        # The feed forward keeps the unsuffixed path so that already saved files still load.
        if architecture is Architecture.FEED_FORWARD:
            return self.name

        return self.name + "/" + architecture.value

    def get_save_model_file_path(self, architecture: Architecture) -> str:
        return directories.get_model_save_path(self._get_path_name(architecture), MODEL_CATEGORY)

    def get_save_training_report_file_path(self, architecture: Architecture) -> str:
        return directories.get_model_save_training_report_path(self._get_path_name(architecture), MODEL_CATEGORY)

    def get_save_training_data_file_path(self, architecture: Architecture) -> str:
        return directories.get_model_save_training_data_path(self._get_path_name(architecture), MODEL_CATEGORY)

    def get_save_graphs_directory_path(self, architecture: Architecture) -> str:
        return directories.get_model_save_graphs_directory_path(self._get_path_name(architecture), MODEL_CATEGORY)

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

@dataclass
class _ArchitectureTrainingSetup():
    """
    Everything that differs between architectures once their data has been prepared.
    """

    model: SavableModule
    training_dataset: Dataset
    training_outputs: torch.Tensor
    validation_dataset: Dataset
    validation_outputs: torch.Tensor
    test_dataset: Dataset
    test_outputs: torch.Tensor
    scaler_parameters: dict
    collate_fn: Callable | None = None

def _get_preprocessed_training_data(
        model_specs: ModelSpecification,
        architecture: Architecture,
        process_data: Callable[[], tuple],
        print_debug: bool = False
        ) -> tuple:
    """
    Returns the cached preprocessed data if it is being loaded, otherwise builds it with
    process_data and caches it.
    """

    file_path = model_specs.get_save_training_data_file_path(architecture)

    if LOAD_SAVED_PROCESSED_TRAINING_DATA:
        if print_debug:
            print("Loading in preprocessed data...")

        return helpers.load_data_from_file(file_path)

    datasets = process_data()

    if SAVE_PROCESSED_TRAINING_DATA:
        if print_debug:
            print("Saving preprocessed data...")

        helpers.save_data_to_file(file_path, datasets)

    return datasets

def _build_feed_forward_setup(
        model_specs: ModelSpecification,
        parameters: TrainingParameters,
        print_debug: bool = False,
        print_all_debug: bool = False
        ) -> _ArchitectureTrainingSetup:

    def process_data() -> tuple:
        labeled_datasets = data_processor.get_all_player_props_input_output_labeled_data(
            model_specs.target_stats,
            VALIDATION_START_DATE,
            TEST_START_DATE,
            CHUNK_STEP_SIZE,
            print_debug
        )

        helpers.print_labeled_dataset(
            labeled_datasets,
            print_values=print_all_debug,
            print_summary=print_debug
        )

        datasets = training_data_processing.process_labeled_data_for_classification_training(
            *labeled_datasets,
            flatten=True,
            standardize_input=True,
            min_output_value=model_specs.minimum_of_stat,
            num_classifications=model_specs.number_of_stat_classifications
            )

        # The last entry is the fitted scaler rather than a dataset.
        helpers.print_datasets(datasets[:-1], 1, print_all_debug, print_debug)

        return datasets

    (input_train, output_train,
     input_val, output_val,
     input_test, output_test,
     input_scaler
     ) = _get_preprocessed_training_data(
         model_specs,
         Architecture.FEED_FORWARD,
         process_data,
         print_debug
         )

    model = FeedForward(
        input_train.shape[1],
        model_specs.number_of_stat_classifications,
        parameters.hidden_layers
    )

    return _ArchitectureTrainingSetup(
        model=model,
        training_dataset=TensorDataset(input_train, output_train),
        training_outputs=output_train,
        validation_dataset=TensorDataset(input_val, output_val),
        validation_outputs=output_val,
        test_dataset=TensorDataset(input_test, output_test),
        test_outputs=output_test,
        scaler_parameters={INPUT_SCALER : input_scaler}
    )

def _build_gru_setup(
        model_specs: ModelSpecification,
        parameters: TrainingParameters,
        print_debug: bool = False
        ) -> _ArchitectureTrainingSetup:

    def process_data() -> tuple:
        labeled_data = data_processor.get_all_player_props_sequence_input_output_labeled_data(
            model_specs.target_stats,
            VALIDATION_START_DATE,
            TEST_START_DATE,
            CHUNK_STEP_SIZE,
            print_debug
        )

        return training_data_processing.process_sequence_labeled_data_for_classification_training(
            *labeled_data,
            max_sequence_length=MAX_SEQUENCE_LENGTH,
            min_output_value=model_specs.minimum_of_stat,
            num_classifications=model_specs.number_of_stat_classifications,
            standardize_input=True
            )

    (training_dataset, validation_dataset, test_dataset,
     sequence_scaler, static_scaler
     ) = _get_preprocessed_training_data(
         model_specs,
         Architecture.GRU,
         process_data,
         print_debug
         )

    # Set again after loading so that the window can be changed without rebuilding the cached data.
    for dataset in (training_dataset, validation_dataset, test_dataset):
        dataset.max_sequence_length = MAX_SEQUENCE_LENGTH

    model = GRUFeedForward(
        training_dataset.sequence_input_dim,
        training_dataset.static_input_dim,
        model_specs.number_of_stat_classifications,
        parameters.hidden_layers,
        GRU_HIDDEN_DIM,
        GRU_LAYERS,
        GRU_DROPOUT_RATE
    )

    return _ArchitectureTrainingSetup(
        model=model,
        training_dataset=training_dataset,
        training_outputs=training_dataset.outputs,
        validation_dataset=validation_dataset,
        validation_outputs=validation_dataset.outputs,
        test_dataset=test_dataset,
        test_outputs=test_dataset.outputs,
        scaler_parameters={SEQUENCE_SCALER : sequence_scaler, STATIC_SCALER : static_scaler},
        collate_fn=training_data_processing.collate_sequence_batch
    )

def _load_model(
        architecture: Architecture,
        parameters_dict: dict
        ) -> SavableModule:

    if architecture is Architecture.GRU:
        return GRUFeedForward.load_from_saved_parameters_dict(parameters_dict)

    return FeedForward.load_from_saved_parameters_dict(parameters_dict)

def _describe_data(setup: _ArchitectureTrainingSetup) -> dict:
    return {
        "training samples": len(setup.training_outputs),
        "validation samples": len(setup.validation_outputs),
        "test samples": len(setup.test_outputs),
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
        architecture: Architecture,
        parameters: TrainingParameters,
        setup: _ArchitectureTrainingSetup,
        loss_function: trainer.LossFunction,
        training_run: trainer.TrainingRun
    ) -> dict:
    """
    Reloads the model that was just saved and scores it on the held out test set, which also
    proves that the saved file round trips back into a working model.
    """

    save_graphs_directory_path = model_specs.get_save_graphs_directory_path(architecture)

    trainer.graph_loss_progress(training_run, save_graphs_directory_path)

    saved_parameters = helpers.load_data_from_file(model_specs.get_save_model_file_path(architecture))
    model = _load_model(architecture, saved_parameters)

    predictions = trainer.predict(
        model,
        setup.test_dataset,
        parameters.configuration.batch_size,
        parameters.configuration.device,
        setup.collate_fn
    )

    # The trainer moved the loss onto the training device, and the predictions come back on the cpu.
    if isinstance(loss_function, nn.Module):
        loss_function = loss_function.cpu()

    metrics = {
        "test loss": float(loss_function(predictions, setup.test_outputs)),
        "test cross entropy": float(nn.functional.cross_entropy(predictions, setup.test_outputs))
    }
    metrics.update(evaluation.output_test_evaluation_classification(
        predictions.numpy(),
        setup.test_outputs.numpy(),
        label=model_specs.name,
        ordinal=True,
        output_size=20,
        save_graph_directory_path=save_graphs_directory_path
    ))

    return metrics

def train(
        model_specs: ModelSpecification,
        architecture: Architecture = Architecture.FEED_FORWARD,
        output_evaluations: bool = True,
        print_debug: bool = True,
        print_all_debug: bool = False,
        ):
    """
    Fits one model spec with one architecture, saves it, and writes a report of the run next to it.
    """

    if print_all_debug:
        pd.set_option("display.max_rows", 10)
        pd.set_option("display.max_columns", 1000)

    torch.manual_seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    parameters = model_specs.get_training_parameters(architecture)

    if architecture is Architecture.GRU:
        setup = _build_gru_setup(model_specs, parameters, print_debug)
    else:
        setup = _build_feed_forward_setup(model_specs, parameters, print_debug, print_all_debug)

    optimizer = torch.optim.AdamW(
        setup.model.parameters(),
        lr=parameters.learning_rate,
        weight_decay=parameters.weight_decay
    )
    loss_function = parameters.build_loss_function(model_specs.number_of_stat_classifications)

    model_description = training_report.describe_model(setup.model)
    data_description = _describe_data(setup)
    label_description = training_data_processing.summarize_classification_outputs(
        setup.training_outputs,
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
        training_report.TrainingReport(f"{model_specs.name} trained as a {architecture.value} model")
        .add("Model", model_description)
        .add("Data", data_description)
        .add("Training labels", label_description)
        .add("Hyperparameters", hyperparameters)
        .add_text("Architecture", str(setup.model))
    )

    if print_debug:
        print(f"\n===== TRAINING {model_specs.name} AS A {architecture.value.upper()} MODEL =====")
        training_report.print_values("Model", model_description)
        training_report.print_values("Data", data_description)
        training_report.print_values("Training labels", label_description)
        training_report.print_values("Hyperparameters", hyperparameters)
        print("")

    training_run = trainer.train(
        setup.model,
        setup.training_dataset,
        setup.validation_dataset,
        optimizer,
        loss_function,
        parameters.configuration,
        collate_fn=setup.collate_fn,
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
    save_model_file_path = model_specs.get_save_model_file_path(architecture)
    model_params = setup.model.get_save_parameters_dict()

    helpers.save_dictionary_data_to_file(save_model_file_path, [model_params, setup.scaler_parameters])

    if output_evaluations:
        report.add("Test set", _evaluate_saved_model(
            model_specs,
            architecture,
            parameters,
            setup,
            loss_function,
            training_run
        ))

    report_path = report.write(model_specs.get_save_training_report_file_path(architecture))

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
    architecture: Architecture = Architecture.FEED_FORWARD,
    ) -> list[float]:

    parameters_dict = helpers.load_data_from_file(model_specs.get_save_model_file_path(architecture))
    model = _load_model(architecture, parameters_dict)

    inference_arguments = (
        model_specs.target_stats,
        target_player_id,
        target_player_team_id,
        target_player_opponent_team_id,
        target_game_date,
        target_game_season_type,
        target_game_at_home,
        target_player_removed_core_teammate_player_ids,
        target_player_added_core_teammate_player_ids
    )

    if architecture is Architecture.GRU:
        player_game_sequences, samples = data_processor.get_player_prop_inference_sequence_input_data(
            *inference_arguments,
            print_debug=True
        )

        dataset = training_data_processing.process_sequence_labeled_input(
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

    else:
        input_labeled = data_processor.get_player_prop_inference_labeled_input_data(
            *inference_arguments,
            print_debug=True
        )

        input_processed = training_data_processing.process_labeled_input(
            input_labeled,
            True
        )

        input_scaler: StandardScaler = parameters_dict[INPUT_SCALER]
        input_scaled = input_scaler.transform(input_processed)
        input: torch.Tensor = training_data_processing.to_tensor(input_scaled)

        model.eval()
        with torch.no_grad():
            predictions = model(input).cpu()

    predicted_probabilities = torch.softmax(predictions, 1)

    return predicted_probabilities.tolist()[0]

def calculate_odds_over_line(
    predicted_probabilities: list[float],
    over_under_line: float,
    minimum_value: int = 0
    ) -> float:
    """
    Calculates the probability given the probability distribution of a value to be higher than the
    given over_under_line.

    Args:
        predicted_probabilities is a list of floats where the value at each index represents the predicted probabilty of
        the value represented by that index of occuring. Each value is assumed to be ordered and in increments of exactly 1.

        over_under_line is a threshold set that a given value has a chance of exceeding.

        minimum_value is the value that the index at 0 of the predicted_probability represents.
    """

    above_line_threshold = math.ceil(over_under_line) - minimum_value

    probability_exceeds_over_under: float = 0.0
    for value in range(above_line_threshold, len(predicted_probabilities)):
        probability_exceeds_over_under += predicted_probabilities[value]

    return probability_exceeds_over_under
