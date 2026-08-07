"""
Fitting a player game statistics model and recording what the run did.

This never runs on the server. Training happens on the developer machine and the model file is
published from there.
"""

from datetime import datetime

import numpy as np
import pandas as pd
import torch, torch.nn as nn

from nba_ml.machine_learning import datasets, evaluation, report, serialization, trainer
from nba_ml.machine_learning.architectures.gru_feed_forward import GRUFeedForward
from nba_ml.machine_learning.datasets import SequenceGameDataset
from nba_ml.models.player_stats import features as stat_features
from nba_ml.models.player_stats.features import FeatureSet
from nba_ml.models.player_stats.specifications import (
    GRU_DROPOUT_RATE,
    GRU_HIDDEN_DIM,
    GRU_LAYERS,
    MAX_SEQUENCE_LENGTH,
    SEQUENCE_SCALER,
    STATIC_SCALER,
    ModelSpecification
)

CACHED_DATASETS = 'datasets'
CACHED_COLUMNS = 'columns'

RANDOM_SEED = 12156666

CHUNK_STEP_SIZE = 1

# Games are split by date, so a model is always scored on games played after the ones it learned
# from. A game on a start date belongs to the earlier split.
VALIDATION_START_DATE = datetime(2025, 8, 1)
TEST_START_DATE = datetime(2026, 6, 8)

EVALUATE_ON_VALIDATION_SET = True
"""
Scores the finished model on the validation set rather than the test set, which is far larger and so
a steadier reading while tuning. That score is not held out, because the run already used those games
to pick its stopping epoch. Turn this off before publishing an accuracy anywhere it matters.
"""

HELD_OUT_LABEL = "Test set"
VALIDATION_LABEL = "Validation set, not held out"

def _build_datasets(
        model_specs: ModelSpecification,
        feature_set: FeatureSet,
        use_cached_build: bool = True,
        save_cached_build: bool = True,
        print_debug: bool = False
        ) -> tuple[SequenceGameDataset, SequenceGameDataset, SequenceGameDataset, dict]:
    """
    Builds the three splits and the scalers fitted on the training one.

    A cached build is only reused when it was made from the columns the model asks for today, so a
    feature set change rebuilds instead of silently training on the previous one.

    Returns:
        (training, validation, test, scaler name to fitted scaler)
    """

    file_path = model_specs.training_cache_file()
    columns = (feature_set.sequence_columns, feature_set.static_columns)
    cached = None

    if use_cached_build and file_path.exists():
        if print_debug:
            print("Loading in preprocessed data...")

        saved = serialization.load_data_from_file(file_path)

        # A build saved before this check existed holds no column list, so it counts as a mismatch.
        if isinstance(saved, dict) and saved.get(CACHED_COLUMNS) == columns:
            cached = saved[CACHED_DATASETS]

        elif print_debug:
            print("The saved data was built from different columns, so it is being rebuilt...")

    if cached is None:
        labeled_data = stat_features.get_all_labeled_data(
            feature_set,
            VALIDATION_START_DATE,
            TEST_START_DATE,
            CHUNK_STEP_SIZE,
            print_debug
        )

        cached = datasets.build_classification_datasets(
            *labeled_data,
            max_sequence_length=MAX_SEQUENCE_LENGTH,
            min_output_value=model_specs.minimum_of_stat,
            num_classifications=model_specs.number_of_stat_classifications,
            standardize_input=True
        )

        if save_cached_build:
            if print_debug:
                print("Saving preprocessed data...")

            serialization.save_data_to_file(file_path, {CACHED_DATASETS: cached, CACHED_COLUMNS: columns})

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

def _describe_features(feature_set: FeatureSet) -> dict:
    return {
        "predicted value": " + ".join(feature_set.output_columns),
        "past games read": MAX_SEQUENCE_LENGTH if MAX_SEQUENCE_LENGTH is not None else "every game",
        "past games required": stat_features.MINIMUM_PAST_GAMES,
        "columns per past game": len(feature_set.sequence_columns),
        "columns on the game being predicted": len(feature_set.static_columns)
    }

def _list_feature_columns(feature_set: FeatureSet) -> str:
    """The exact columns a run consumed, so a saved report can be matched back to its inputs."""

    return "\n\n".join(
        f"{label} ({len(columns)}):\n" + "\n".join(columns)
        for label, columns in (
            ("Past game columns", feature_set.sequence_columns),
            ("Predicted game columns", feature_set.static_columns)
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
        "scored on": VALIDATION_LABEL if EVALUATE_ON_VALIDATION_SET else HELD_OUT_LABEL,
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
        evaluation_dataset: SequenceGameDataset,
        loss_function: trainer.LossFunction,
        training_run: trainer.TrainingRun
    ) -> dict:
    """
    Reloads the model that was just saved and scores it, which also proves that the saved file round
    trips back into a working model.
    """

    graphs_directory = model_specs.graphs_directory()

    trainer.graph_loss_progress(training_run, graphs_directory)

    saved_parameters = serialization.load_data_from_file(model_specs.model_file())
    model = GRUFeedForward.load_from_saved_parameters_dict(saved_parameters)

    configuration = model_specs.training_parameters.configuration
    predictions = trainer.predict(
        model,
        evaluation_dataset,
        configuration.batch_size,
        configuration.device,
        datasets.collate_sequence_batch
    )

    # The trainer moved the loss onto the training device, and the predictions come back on the cpu.
    if isinstance(loss_function, nn.Module):
        loss_function = loss_function.cpu()

    outputs = evaluation_dataset.outputs
    metrics = {
        "loss": float(loss_function(predictions, outputs)),
        "cross entropy": float(nn.functional.cross_entropy(predictions, outputs))
    }
    metrics.update(evaluation.output_test_evaluation_classification(
        predictions.numpy(),
        outputs.numpy(),
        label=model_specs.name,
        ordinal=True,
        output_size=20,
        save_graph_directory_path=graphs_directory
    ))

    return metrics

def train(
        model_specs: ModelSpecification,
        output_evaluations: bool = True,
        use_cached_build: bool = True,
        save_cached_build: bool = True,
        print_debug: bool = True,
        print_all_debug: bool = False,
        ):
    """
    Fits one model spec, saves it, and writes a report of the run next to it.

    Args:
        use_cached_build reuses the last run's preprocessed build when it was made from the same
        columns. save_cached_build writes this run's build for the next one to reuse.
    """

    if print_all_debug:
        pd.set_option("display.max_rows", 10)
        pd.set_option("display.max_columns", 1000)

    torch.manual_seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    parameters = model_specs.training_parameters

    feature_set = model_specs.get_feature_set()
    training_dataset, validation_dataset, test_dataset, scaler_parameters = _build_datasets(
        model_specs,
        feature_set,
        use_cached_build,
        save_cached_build,
        print_debug
    )

    evaluation_dataset = validation_dataset if EVALUATE_ON_VALIDATION_SET else test_dataset

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

    model_description = report.describe_model(model)
    feature_description = _describe_features(feature_set)
    data_description = _describe_data(training_dataset, validation_dataset, test_dataset)
    label_description = datasets.summarize_classification_outputs(
        training_dataset.outputs,
        model_specs.number_of_stat_classifications
    )
    hyperparameters = {
        "optimizer": type(optimizer).__name__,
        "learning rate": parameters.learning_rate,
        "weight decay": parameters.weight_decay,
        "loss function": loss_function,
        **report.values_of(parameters.configuration)
    }

    training_report = (
        report.TrainingReport(f"{model_specs.name} model")
        .add("Model", model_description)
        .add("Features", feature_description)
        .add("Data", data_description)
        .add("Training labels", label_description)
        .add("Hyperparameters", hyperparameters)
        .add_text("Architecture", str(model))
        .add_text("Feature columns", _list_feature_columns(feature_set))
    )

    if print_debug:
        print(f"\n===== TRAINING THE {model_specs.name.upper()} MODEL =====")
        report.print_values("Model", model_description)
        report.print_values("Features", feature_description)
        report.print_values("Data", data_description)
        report.print_values("Training labels", label_description)
        report.print_values("Hyperparameters", hyperparameters)
        print("")

    if print_all_debug:
        print(_list_feature_columns(feature_set))
        print("")

    training_run = trainer.train(
        model,
        training_dataset,
        validation_dataset,
        optimizer,
        loss_function,
        parameters.configuration,
        collate_fn=datasets.collate_sequence_batch,
        metrics=evaluation.get_ordinal_classification_metrics()
    )

    training_report.add("Result", _describe_run(training_run))
    training_report.add("Epochs", {
        f"epoch {result.epoch}": (
            f"train {result.training_loss:.4f} | val {result.validation_loss:.4f} | "
            + " | ".join(f"{name} {value:.4f}" for name, value in result.metrics.items())
        )
        for result in training_run.epoch_results
    })

    model_file = model_specs.model_file()
    serialization.save_data_to_file(
        model_file,
        {**model.get_save_parameters_dict(), **scaler_parameters}
    )

    if output_evaluations:
        training_report.add(
            VALIDATION_LABEL if EVALUATE_ON_VALIDATION_SET else HELD_OUT_LABEL,
            _evaluate_saved_model(model_specs, evaluation_dataset, loss_function, training_run)
        )

    report_path = training_report.write(model_specs.training_report_file())

    if print_debug:
        print(f"\nSaved the model to {model_file} and its report to {report_path}.")
