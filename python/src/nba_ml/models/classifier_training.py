"""
Fitting a classifier of any family, and recording what the run did.

Every model here reads a sequence of past games and answers with a probability per class, so the run
itself is the same whoever it is about. A family brings the samples and the words to describe them,
in TrainingInputs, and nothing else.

This never runs on the server. Training happens on the developer machine and the model file is
published from there.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
import torch, torch.nn as nn

from nba_ml import season
from nba_ml.machine_learning import datasets, evaluation, report, serialization, trainer
from nba_ml.machine_learning.architectures.gru_feed_forward import GRUFeedForward
from nba_ml.machine_learning.datasets import GameSequences, SequenceGameDataset, SequenceInputSamples
from nba_ml.models import loading
from nba_ml.models.classifiers import ClassifierModelSpecification

CACHED_DATASETS = 'datasets'
CACHED_BUILD = 'build'

RANDOM_SEED = 12156666

CHUNK_STEP_SIZE = 1
"""How many of a subject's games are stepped over between samples. One keeps every game."""

# Games are split by date, so a model is always scored on games played after the ones it learned
# from. A game on a start date belongs to the earlier split. Every family splits on the same dates,
# so two models are scored on the same games however different they are.
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

LabeledData = tuple[GameSequences, SequenceInputSamples, SequenceInputSamples, SequenceInputSamples]
"""Every sample the family holds: the games, then the training, validation and test splits."""

LabeledDataBuilder = Callable[[datetime, datetime, datetime, int, bool], LabeledData]
"""Builds samples from a training start, split starts, a sample step size and a debug flag."""

@dataclass(frozen=True)
class TrainingResult():
    """
    What one finished run produced.

    A caller comparing two runs reads this rather than the report the run also wrote, so a sweep of
    settings never has to parse its own output back.
    """

    run: trainer.TrainingRun
    scores: dict[str, float]
    """How the saved model scored, or empty when the run was told not to score it."""

@dataclass(frozen=True)
class TrainingInputs():
    """What one family brings to a run: how to build its samples, and how to describe them."""

    build_labeled_data: LabeledDataBuilder
    predicted_value: str
    """What the model is fit against, in enough detail to tell two builds apart."""

    sequence_columns: list[str]
    static_columns: list[str]
    minimum_past_games: int
    max_sequence_length: int | None
    """How many of the most recent games the network reads, or None for every one of them."""

    build_description: tuple = ()
    """Anything else deciding what a build holds, beyond the columns and the output shape."""

def _describe_build(
    model_specs: ClassifierModelSpecification,
    inputs: TrainingInputs,
    training_start_date: datetime
    ) -> tuple:
    """
    Everything that decides what a build holds, written as plain data so it can be saved beside one.

    A saved build is reused only while this still matches, so changing a column, the value being
    predicted, the class range or how much history a sample needs rebuilds rather than silently
    training on the last one.
    """

    return (
        inputs.sequence_columns,
        inputs.static_columns,
        inputs.predicted_value,
        inputs.minimum_past_games,
        model_specs.output.first_value,
        model_specs.output.length,
        model_specs.output.value_step,
        model_specs.output.impossible_value,
        inputs.build_description,
        training_start_date
    )

def _load_cached_build(file_path: Path, description: tuple, print_debug: bool):
    """
    The saved build, or None when there is not one this run can use.

    A build written by older code can fail to read at all, which is a rebuild rather than an error,
    since the file is a saved copy of work this run can simply do again.
    """

    try:
        saved = serialization.load_data_from_file(file_path)
    except Exception as error:
        if print_debug:
            print(f"The saved data could not be read ({error}), so it is being rebuilt...")

        return None

    # A build saved before this check existed carries no description, so it counts as a mismatch.
    if isinstance(saved, dict) and saved.get(CACHED_BUILD) == description:
        return saved[CACHED_DATASETS]

    if print_debug:
        print("The saved data was built differently, so it is being rebuilt...")

    return None

def _build_datasets(
        model_specs: ClassifierModelSpecification,
        inputs: TrainingInputs,
        use_cached_build: bool = True,
        save_cached_build: bool = True,
        print_debug: bool = False,
        training_start_date: datetime = season.season_start_date(season.COLLECTION_START_SEASON)
        ) -> tuple[SequenceGameDataset, SequenceGameDataset, SequenceGameDataset, dict]:
    """
    Builds the three splits and the scalers fitted on the training one.

    Returns:
        (training, validation, test, scaler name to fitted scaler)
    """

    file_path = model_specs.training_cache_file()
    description = _describe_build(model_specs, inputs, training_start_date)
    cached = None

    if use_cached_build and file_path.exists():
        if print_debug:
            print("Loading in preprocessed data...")

        cached = _load_cached_build(file_path, description, print_debug)

    if cached is None:
        labeled_data = inputs.build_labeled_data(
            training_start_date,
            VALIDATION_START_DATE,
            TEST_START_DATE,
            CHUNK_STEP_SIZE,
            print_debug
        )

        cached = datasets.build_classification_datasets(
            *labeled_data,
            max_sequence_length=inputs.max_sequence_length,
            min_output_value=model_specs.output.first_value,
            num_classifications=model_specs.output.length,
            output_value_step=model_specs.output.value_step,
            impossible_value=model_specs.output.impossible_value,
            standardize_input=True
        )

        if save_cached_build:
            if print_debug:
                print("Saving preprocessed data...")

            serialization.save_data_to_file(file_path, {CACHED_DATASETS: cached, CACHED_BUILD: description})

    training_dataset, validation_dataset, test_dataset, sequence_scaler, static_scaler = cached

    # Set again after loading so that the window can be changed without rebuilding the cached data.
    for dataset in (training_dataset, validation_dataset, test_dataset):
        dataset.max_sequence_length = inputs.max_sequence_length

    return (
        training_dataset,
        validation_dataset,
        test_dataset,
        {loading.SEQUENCE_SCALER : sequence_scaler, loading.STATIC_SCALER : static_scaler}
    )

def _describe_features(inputs: TrainingInputs, training_dataset: SequenceGameDataset) -> dict:
    return {
        "predicted value": inputs.predicted_value,
        "game histories read": training_dataset.sequence_count,
        "past games read": inputs.max_sequence_length if inputs.max_sequence_length is not None else "every game",
        "past games required": inputs.minimum_past_games,
        "columns per past game": len(inputs.sequence_columns),
        "columns on the game being predicted": len(inputs.static_columns)
    }

def _list_feature_columns(inputs: TrainingInputs) -> str:
    """The exact columns a run consumed, so a saved report can be matched back to its inputs."""

    return "\n\n".join(
        f"{label} ({len(columns)}):\n" + "\n".join(columns)
        for label, columns in (
            ("Past game columns", inputs.sequence_columns),
            ("Predicted game columns", inputs.static_columns)
        )
    )

def _describe_data(
    training_dataset: SequenceGameDataset,
    validation_dataset: SequenceGameDataset,
    test_dataset: SequenceGameDataset,
    training_start_date: datetime
    ) -> dict:
    return {
        "training samples": len(training_dataset),
        "validation samples": len(validation_dataset),
        "test samples": len(test_dataset),
        "training starts": training_start_date.date(),
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

def _value_scale(
        model_specs: ClassifierModelSpecification,
        dataset: SequenceGameDataset
    ) -> evaluation.ValueScale | None:
    """
    The number line this model's classes sit on, or None for an answer that has no line.

    Without it every figure would be worked out over positions in an array, which are the outcomes
    themselves only where a range starts at zero and a class covers one value.
    """

    output = model_specs.output
    values = dataset.samples.values

    if not output.ordered or values is None:
        return None

    return evaluation.ValueScale(
        class_values=np.array([output.value_of(position) for position in range(output.length)]),
        actual_values=values,
        first_value=output.first_value,
        value_step=output.value_step,
        impossible_value=output.impossible_value
    )

def _evaluate_saved_model(
        model_specs: ClassifierModelSpecification,
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

    output = model_specs.output
    outputs = evaluation_dataset.outputs
    metrics = {
        "loss": float(loss_function(predictions, outputs)),
        "cross entropy": float(nn.functional.cross_entropy(predictions, outputs))
    }

    metrics.update(evaluation.output_test_evaluation_classification(
        predictions.numpy(),
        outputs.numpy(),
        label=model_specs.name,
        class_labels=[output.label(position) for position in range(output.length)],
        values=_value_scale(model_specs, evaluation_dataset),
        output_size=20,
        save_graph_directory_path=graphs_directory
    ))

    return metrics

def train(
        model_specs: ClassifierModelSpecification,
        inputs: TrainingInputs,
        output_evaluations: bool = True,
        use_cached_build: bool = True,
        save_cached_build: bool = True,
        print_debug: bool = True,
        print_all_debug: bool = False,
        training_start_date: datetime = season.season_start_date(season.COLLECTION_START_SEASON)
        ) -> TrainingResult:
    """
    Fits one model spec, saves it, and writes a report of the run next to it.

    Args:
        use_cached_build reuses the last run's preprocessed build when it was made from the same
        columns. save_cached_build writes this run's build for the next one to reuse.

    Returns:
        The record of the run and the scores of the saved model, so a caller comparing two of them
        does not have to read a report back.
    """

    if print_all_debug:
        pd.set_option("display.max_rows", 10)
        pd.set_option("display.max_columns", 1000)

    torch.manual_seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    parameters = model_specs.training_parameters

    training_dataset, validation_dataset, test_dataset, scaler_parameters = _build_datasets(
        model_specs,
        inputs,
        use_cached_build,
        save_cached_build,
        print_debug,
        training_start_date
    )

    evaluation_dataset = validation_dataset if EVALUATE_ON_VALIDATION_SET else test_dataset

    model = GRUFeedForward(
        training_dataset.sequence_input_dim,
        training_dataset.static_input_dim,
        model_specs.output.length,
        parameters.hidden_layers,
        parameters.gru_hidden_dim,
        parameters.gru_layers,
        parameters.gru_dropout_rate,
        training_dataset.sequence_count
    )

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=parameters.learning_rate,
        weight_decay=parameters.weight_decay
    )
    loss_function = parameters.build_loss_function(model_specs.output.length)

    value_scale = _value_scale(model_specs, training_dataset)

    model_description = report.describe_model(model)
    feature_description = _describe_features(inputs, training_dataset)
    data_description = _describe_data(training_dataset, validation_dataset, test_dataset, training_start_date)
    label_description = datasets.summarize_classification_outputs(
        training_dataset.outputs,
        model_specs.output.length,
        model_specs.output.value_step
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
        .add_text("Feature columns", _list_feature_columns(inputs))
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
        print(_list_feature_columns(inputs))
        print("")

    training_run = trainer.train(
        model,
        training_dataset,
        validation_dataset,
        optimizer,
        loss_function,
        parameters.configuration,
        collate_fn=datasets.collate_sequence_batch,
        metrics=(
            evaluation.get_classification_metrics() if value_scale is None
            else evaluation.get_ordinal_classification_metrics(value_scale.class_values)
        )
    )

    training_report.add("Result", _describe_run(training_run))
    training_report.add("Epochs", {
        f"epoch {result.epoch}": (
            f"train {result.training_loss:.4f} | val {result.validation_loss:.4f} | "
            + " | ".join(f"{name} {value:.4f}" for name, value in result.metrics.items())
        )
        for result in training_run.epoch_results
    })

    # The columns are saved beside the weights so that a model fit before a column moved reports as
    # unpublishable rather than failing at the first matrix multiply. See models/loading.py.
    model_file = model_specs.model_file()
    serialization.save_data_to_file(
        model_file,
        {
            **model.get_save_parameters_dict(),
            **scaler_parameters,
            loading.SEQUENCE_COLUMNS: list(inputs.sequence_columns),
            loading.STATIC_COLUMNS: list(inputs.static_columns)
        }
    )

    scores: dict[str, float] = {}
    if output_evaluations:
        scores = _evaluate_saved_model(model_specs, evaluation_dataset, loss_function, training_run)
        training_report.add(VALIDATION_LABEL if EVALUATE_ON_VALIDATION_SET else HELD_OUT_LABEL, scores)

    report_path = training_report.write(model_specs.training_report_file())

    if print_debug:
        print(f"\nSaved the model to {model_file} and its report to {report_path}.")

    return TrainingResult(training_run, scores)
