"""Shared training code for the classifier models of every family."""

from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
import re
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import pandas as pd
import torch, torch.nn as nn
from dateutil.relativedelta import relativedelta

from nba_ml import season
from nba_ml.feature_engineering.samples import SPLIT_NAMES, EvaluationSplit, SplitKey
from nba_ml.machine_learning import datasets, evaluation, report, serialization, trainer
from nba_ml.machine_learning.architectures.gru_feed_forward import GRUFeedForward
from nba_ml.machine_learning.datasets import GameSequences, SequenceGameDataset, SequenceInputSamples
from nba_ml.models import loading, metrics
from nba_ml.models.classifiers import ClassifierModelSpecification

CACHED_DATASETS = 'datasets'
CACHED_BUILD = 'build'

RANDOM_SEED = 12156666

CHUNK_STEP_SIZE = 1
"""Step between a subject's games when building samples. 1 uses every game."""

EVALUATION_LENGTH_YEARS = 1
"""Length of the evaluation period, counted back from the day training runs."""

VALIDATION_FRACTION = 0.5
"""Fraction of the evaluation period used for validation. The rest is the test set."""

SPLIT_SEED = 5891244
"""Seed for assigning evaluation samples to validation or test."""

def default_evaluation_start_date() -> datetime:
    """Returns the default evaluation start date, EVALUATION_LENGTH_YEARS before today."""

    return datetime.combine(
        season.today() - relativedelta(years=EVALUATION_LENGTH_YEARS),
        datetime.min.time()
    )

def default_evaluation_split() -> EvaluationSplit:
    """Returns the evaluation split used when none is given."""

    return EvaluationSplit(
        start_date=default_evaluation_start_date(),
        validation_fraction=VALIDATION_FRACTION,
        seed=SPLIT_SEED
    )

LabeledData = tuple[GameSequences, SequenceInputSamples, SequenceInputSamples, SequenceInputSamples]
"""The game sequences, followed by the training, validation and test samples."""

LabeledDataBuilder = Callable[[datetime, EvaluationSplit, int, bool], LabeledData]
"""Builds the labeled data from a training start date, an evaluation split, a step size and a debug flag."""

@dataclass(frozen=True)
class TrainingResult():
    """Results of a training run."""

    run: trainer.TrainingRun
    scores: dict[str, float]
    """The model's metrics on the test set. Empty if it was not evaluated."""

    evaluation: metrics.ModelEvaluation | None = None
    """The evaluation saved next to the model. None if it was not evaluated."""

@dataclass(frozen=True)
class TrainingInputs():
    """The inputs a model family provides for a training run."""

    build_labeled_data: LabeledDataBuilder
    predicted_value: str
    """Describes the target value. Used to tell cached builds apart."""

    sequence_columns: list[str]
    static_columns: list[str]
    minimum_past_games: int
    max_sequence_length: int | None
    """Number of most recent games the model uses, or None for all of them."""

    split_on: SplitKey = SplitKey.SUBJECT
    """The key this family's validation and test samples are split by."""

    build_description: tuple = ()
    """Any other settings that change the built data, besides the columns and the output."""

@dataclass(frozen=True)
class EvaluationSettings():
    """The settings needed to rebuild the same splits a model was evaluated on."""

    training_start_date: datetime
    evaluation_split: EvaluationSplit
    chunk_step_size: int = CHUNK_STEP_SIZE

def _saved_evaluation_settings(settings: EvaluationSettings) -> dict[str, str | float | int]:
    split = settings.evaluation_split

    return {
        "training_start_date": settings.training_start_date.isoformat(),
        "evaluation_start_date": split.start_date.isoformat(),
        "validation_fraction": split.validation_fraction,
        "split_on": split.split_on.value,
        "split_seed": split.seed,
        "chunk_step_size": settings.chunk_step_size
    }

def _read_saved_evaluation_settings(saved: Mapping[str, Any]) -> EvaluationSettings | None:
    """Reads the split settings from a saved model file. Returns None if it has none."""

    settings = saved.get(loading.EVALUATION_SETTINGS)

    if not isinstance(settings, dict):
        return None

    try:
        return EvaluationSettings(
            training_start_date=datetime.fromisoformat(settings["training_start_date"]),
            evaluation_split=EvaluationSplit(
                start_date=datetime.fromisoformat(settings["evaluation_start_date"]),
                validation_fraction=float(settings["validation_fraction"]),
                split_on=SplitKey(settings["split_on"]),
                seed=int(settings["split_seed"])
            ),
            chunk_step_size=int(settings["chunk_step_size"])
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("The saved evaluation settings are unreadable.") from error

def _read_reported_evaluation_settings(model_specs: ClassifierModelSpecification) -> EvaluationSettings | None:
    """Reads the split settings from a training report, for older models that don't store them in the model file."""

    try:
        report_text = model_specs.training_report_file().read_text(encoding="utf-8")
    except OSError:
        return None

    names = (
        "training starts",
        "evaluation starts",
        "validation fraction",
        "split apart by",
        "split seed",
        "sample step size"
    )
    values = {
        name: match.group(1)
        for name in names
        if (match := re.search(rf"^{re.escape(name)}\s{{2,}}(.+)$", report_text, re.MULTILINE))
    }

    if len(values) != len(names):
        return None

    try:
        return EvaluationSettings(
            training_start_date=datetime.fromisoformat(values["training starts"]),
            evaluation_split=EvaluationSplit(
                start_date=datetime.fromisoformat(values["evaluation starts"]),
                validation_fraction=float(values["validation fraction"]),
                split_on=SplitKey(values["split apart by"]),
                seed=int(values["split seed"])
            ),
            chunk_step_size=int(values["sample step size"])
        )
    except ValueError:
        return None

def _describe_build(
    model_specs: ClassifierModelSpecification,
    inputs: TrainingInputs,
    training_start_date: datetime,
    evaluation_split: EvaluationSplit,
    chunk_step_size: int = CHUNK_STEP_SIZE
    ) -> tuple:
    """Returns every setting that affects the built data. It is saved with a cached build to check it still matches."""

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
        training_start_date,
        evaluation_split,
        chunk_step_size
    )

def _load_cached_build(file_path: Path, description: tuple, print_debug: bool):
    """Returns the cached build, or None if it can't be read or was built with different settings."""

    try:
        saved = serialization.load_data_from_file(file_path)
    except Exception as error:
        if print_debug:
            print(f"The saved data could not be read ({error}), so it is being rebuilt...")

        return None

    # Builds cached before this check existed have no description, so they never match.
    if isinstance(saved, dict) and saved.get(CACHED_BUILD) == description:
        return saved[CACHED_DATASETS]

    if print_debug:
        print("The saved data was built differently, so it is being rebuilt...")

    return None

def _check_splits_hold_something(
    split_samples: Sequence[SequenceInputSamples],
    evaluation_split: EvaluationSplit
    ):
    """Raises an error if any split has no samples."""

    empty = [name for name, samples in zip(SPLIT_NAMES, split_samples) if len(samples.outputs) == 0]

    if empty:
        raise ValueError(
            f"The {' and '.join(empty)} split holds no samples, so this run would report nothing. "
            f"The evaluation period opens on {evaluation_split.start_date.date()} and takes "
            f"{evaluation_split.validation_fraction:.0%} of it for validation. Move it back to "
            "where games are held."
        )

def _build_datasets(
        model_specs: ClassifierModelSpecification,
        inputs: TrainingInputs,
        evaluation_split: EvaluationSplit,
        use_cached_build: bool = True,
        save_cached_build: bool = True,
        print_debug: bool = False,
        training_start_date: datetime = season.season_start_date(season.ARCHIVE_START_SEASON),
        chunk_step_size: int = CHUNK_STEP_SIZE,
        input_scalers: Mapping[str, Any] | None = None
        ) -> tuple[SequenceGameDataset, SequenceGameDataset, SequenceGameDataset, dict]:
    """Builds the training, validation and test datasets, plus the scalers fit on the training data."""

    file_path = model_specs.training_cache_file()
    description = _describe_build(
        model_specs, inputs, training_start_date, evaluation_split, chunk_step_size
    )
    cached = None

    if use_cached_build and file_path.exists():
        if print_debug:
            print("Loading in preprocessed data...")

        cached = _load_cached_build(file_path, description, print_debug)

    if cached is None:
        labeled_data = inputs.build_labeled_data(
            training_start_date,
            evaluation_split,
            chunk_step_size,
            print_debug
        )

        _check_splits_hold_something(labeled_data[1:], evaluation_split)

        cached = datasets.build_classification_datasets(
            *labeled_data,
            max_sequence_length=inputs.max_sequence_length,
            min_output_value=model_specs.output.first_value,
            num_classifications=model_specs.output.length,
            output_value_step=model_specs.output.value_step,
            impossible_value=model_specs.output.impossible_value,
            standardize_input=True,
            input_scalers=(
                None if input_scalers is None else (
                    input_scalers[loading.SEQUENCE_SCALER], input_scalers[loading.STATIC_SCALER]
                )
            )
        )

        if save_cached_build:
            if print_debug:
                print("Saving preprocessed data...")

            serialization.save_data_to_file(file_path, {CACHED_DATASETS: cached, CACHED_BUILD: description})

    training_dataset, validation_dataset, test_dataset, sequence_scaler, static_scaler = cached

    # Set after loading so the sequence length can change without rebuilding the cached data.
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
    """Returns the feature columns used by a run as text for the report."""

    return "\n\n".join(
        f"{label} ({len(columns)}):\n" + "\n".join(columns)
        for label, columns in (
            ("Past game columns", inputs.sequence_columns),
            ("Predicted game columns", inputs.static_columns)
        )
    )

def _covered(dataset: SequenceGameDataset) -> str:
    """Returns the sample count and date range of a split as text."""

    first, last = metrics.dates_covered(dataset.samples.game_dates)

    return f"{len(dataset):,} samples" + (f", {first} to {last}" if first else "")

def _describe_data(
    training_dataset: SequenceGameDataset,
    validation_dataset: SequenceGameDataset,
    test_dataset: SequenceGameDataset,
    training_start_date: datetime,
    evaluation_split: EvaluationSplit
    ) -> dict:
    return {
        "training": _covered(training_dataset),
        "validation": _covered(validation_dataset),
        "test": _covered(test_dataset),
        "training starts": training_start_date.date(),
        "evaluation starts": evaluation_split.start_date.date(),
        "validation fraction": evaluation_split.validation_fraction,
        "split apart by": evaluation_split.split_on.value,
        "split seed": str(evaluation_split.seed),
        "scored on": metrics.TEST_SPLIT_LABEL,
        "sample step size": CHUNK_STEP_SIZE,
        "random seed": str(RANDOM_SEED)
    }

def _report_scores(scores: dict[str, float], floor: dict[str, float]) -> dict[str, str]:
    """Returns each metric by its label, with the baseline value next to it."""

    return {
        metrics.label_of(key): (
            f"{value:.6g}" if key not in floor else f"{value:.6g}  (floor {floor[key]:.6g})"
        )
        for key, value in scores.items()
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
    """Returns the ValueScale for the model's classes, or None if its output isn't ordered."""

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

FLOOR_WINDOW_DAYS = 365
"""Days of training data before the evaluation period used for the baseline."""

def _floor_probabilities(
        training_dataset: SequenceGameDataset,
        evaluation_split: EvaluationSplit,
        classes: int,
        samples: int
    ) -> np.ndarray:
    """Returns the baseline prediction for every sample: the frequency of each class in recent training data."""

    outputs = training_dataset.samples.outputs
    game_dates = training_dataset.samples.game_dates

    if game_dates is not None and len(game_dates) > 0:
        recent = game_dates >= np.datetime64(evaluation_split.start_date) - np.timedelta64(
            FLOOR_WINDOW_DAYS, 'D'
        )

        if recent.any():
            outputs = outputs[recent]

    return np.tile(evaluation.class_prior(outputs, classes), (samples, 1))

def _evaluate_model(
        model_specs: ClassifierModelSpecification,
        model: GRUFeedForward,
        training_dataset: SequenceGameDataset,
        test_dataset: SequenceGameDataset,
        evaluation_split: EvaluationSplit,
        loss_function: trainer.LossFunction,
        write_graphs: bool = False
    ) -> tuple[dict[str, float], metrics.ModelEvaluation]:
    """Evaluates a trained model on the test set."""

    configuration = model_specs.training_parameters.configuration
    predictions = trainer.predict(
        model,
        test_dataset,
        configuration.batch_size,
        configuration.device,
        datasets.collate_sequence_batch
    )

    # Predictions come back on the CPU, so move the loss there too.
    if isinstance(loss_function, nn.Module):
        loss_function = loss_function.cpu()

    output = model_specs.output
    outputs = test_dataset.outputs
    value_scale = _value_scale(model_specs, test_dataset)
    probabilities = torch.softmax(predictions, dim=1).numpy()
    actuals = outputs.numpy()

    scores = {
        evaluation.LOSS: float(loss_function(predictions, outputs)),
        evaluation.CROSS_ENTROPY: float(nn.functional.cross_entropy(predictions, outputs)),
        **evaluation.score_classification(probabilities, actuals, value_scale)
    }

    floor = evaluation.score_classification(
        _floor_probabilities(training_dataset, evaluation_split, output.length, len(actuals)),
        actuals,
        value_scale
    )

    if write_graphs:
        evaluation.graph_classification(
            probabilities,
            actuals,
            label=model_specs.name,
            class_labels=[output.label(position) for position in range(output.length)],
            values=value_scale,
            output_size=20,
            save_graph_directory_path=model_specs.graphs_directory()
        )

    first_game, last_game = metrics.dates_covered(test_dataset.samples.game_dates)

    return (
        scores,
        metrics.ModelEvaluation(
            model=model_specs.name,
            scored_on=metrics.TEST_SPLIT_LABEL,
            samples=len(actuals),
            first_game=first_game,
            last_game=last_game,
            evaluated=datetime.now().isoformat(timespec="seconds"),
            metrics=scores,
            floor=floor
        )
    )

def rescore(
        model_specs: ClassifierModelSpecification,
        inputs: TrainingInputs,
        print_debug: bool = True
    ) -> metrics.ModelEvaluation:
    """Re-evaluates a saved model on its test set without retraining it."""

    model, saved = loading.load(model_specs.model_file())
    settings = _read_saved_evaluation_settings(saved) or _read_reported_evaluation_settings(model_specs)

    if settings is None:
        raise ValueError(
            f"{model_specs.name} has no recorded split settings. Train it again before rescoring it."
        )

    try:
        training_dataset, _, test_dataset, _ = _build_datasets(
            model_specs,
            inputs,
            settings.evaluation_split,
            use_cached_build=False,
            save_cached_build=False,
            print_debug=print_debug,
            training_start_date=settings.training_start_date,
            chunk_step_size=settings.chunk_step_size,
            input_scalers=saved
        )
    except KeyError as error:
        raise ValueError(
            f"{model_specs.name} has no saved input scalers, so it cannot be rescored."
        ) from error

    loss_function = model_specs.training_parameters.build_loss_function(model_specs.output.length)
    _, model_evaluation = _evaluate_model(
        model_specs,
        model,
        training_dataset,
        test_dataset,
        settings.evaluation_split,
        loss_function
    )
    evaluation_path = metrics.write(model_specs.evaluation_file(), model_evaluation)

    if print_debug:
        print(f"Saved the scores to {evaluation_path}.")

    return model_evaluation

def train(
        model_specs: ClassifierModelSpecification,
        inputs: TrainingInputs,
        output_evaluations: bool = True,
        use_cached_build: bool = True,
        save_cached_build: bool = True,
        print_debug: bool = True,
        print_all_debug: bool = False,
        training_start_date: datetime = season.season_start_date(season.ARCHIVE_START_SEASON),
        evaluation_split: EvaluationSplit | None = None
        ) -> TrainingResult:
    """Trains a model, saves it, and writes a training report and evaluation next to it."""

    if print_all_debug:
        pd.set_option("display.max_rows", 10)
        pd.set_option("display.max_columns", 1000)

    torch.manual_seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    parameters = model_specs.training_parameters

    evaluation_split = replace(
        evaluation_split if evaluation_split is not None else default_evaluation_split(),
        split_on=inputs.split_on
    )
    evaluation_settings = EvaluationSettings(training_start_date, evaluation_split)

    training_dataset, validation_dataset, test_dataset, scaler_parameters = _build_datasets(
        model_specs,
        inputs,
        evaluation_split,
        use_cached_build,
        save_cached_build,
        print_debug,
        training_start_date
    )

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
    data_description = _describe_data(
        training_dataset, validation_dataset, test_dataset, training_start_date, evaluation_split
    )
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

    # The feature columns are saved with the weights so an outdated model can be detected.
    model_file = model_specs.model_file()
    serialization.save_data_to_file(
        model_file,
        {
            **model.get_save_parameters_dict(),
            **scaler_parameters,
            loading.SEQUENCE_COLUMNS: list(inputs.sequence_columns),
            loading.STATIC_COLUMNS: list(inputs.static_columns),
            loading.EVALUATION_SETTINGS: _saved_evaluation_settings(evaluation_settings)
        }
    )

    scores: dict[str, float] = {}
    model_evaluation: metrics.ModelEvaluation | None = None

    if output_evaluations:
        trainer.graph_loss_progress(training_run, model_specs.graphs_directory())
        saved_model, _ = loading.load(model_file)
        scores, model_evaluation = _evaluate_model(
            model_specs,
            saved_model,
            training_dataset,
            test_dataset,
            evaluation_split,
            loss_function,
            write_graphs=True
        )
        evaluation_path = metrics.write(model_specs.evaluation_file(), model_evaluation)

        training_report.add(
            f"Held-out test set, {model_evaluation.samples:,} games",
            _report_scores(scores, model_evaluation.floor)
        )

        if print_debug:
            print(f"\n===== SCORES FOR {model_specs.name.upper()} =====")
            report.print_values("Held-out test set", _report_scores(scores, model_evaluation.floor))
            print(f"\nSaved the scores to {evaluation_path}.")

    report_path = training_report.write(model_specs.training_report_file())

    if print_debug:
        print(f"\nSaved the model to {model_file} and its report to {report_path}.")

    return TrainingResult(training_run, scores, model_evaluation)
