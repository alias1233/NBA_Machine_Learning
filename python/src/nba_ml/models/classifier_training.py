"""
Fitting a classifier of any family, and recording what the run did.

Every model here reads a sequence of past games and answers with a probability per class, so the run
itself is the same whoever it is about. A family brings the samples and the words to describe them,
in TrainingInputs, and nothing else.

This never runs on the server. Training happens on the developer machine and the model file is
published from there.
"""

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
"""How many of a subject's games are stepped over between samples. One keeps every game."""

EVALUATION_LENGTH_YEARS = 1
"""
How far back the games a model is scored on reach, counted from the day the run starts.

A year is the shortest window that holds a whole season, which is the point. Validation and test are
told apart by something other than the date, so both of them hold the opening weeks, the closing
weeks and the playoffs. Scoring a model on a fortnight in June said nothing about any of those.
"""

VALIDATION_FRACTION = 0.5
"""
The share of the evaluation period that picks the stopping epoch, the rest being held out.

A half leaves the two the same size, which is what makes the published figure as steady as the one
the run tuned against.
"""

SPLIT_SEED = 5891244
"""
Decides which keys land in validation and which in test.

Its own number rather than RANDOM_SEED, so a run can be repeated with different weights on exactly
the same games, which is the only way to tell a change in the model from a change in the split.
"""

def default_evaluation_start_date() -> datetime:
    """
    The first day of the evaluation period, which is a year back from today.

    Read off today rather than written down, so a run started next season scores that season rather
    than a stretch of calendar somebody has to remember to move. `--evaluation-start` pins it where
    several models have to be scored on exactly the same games across more than one day.
    """

    return datetime.combine(
        season.today() - relativedelta(years=EVALUATION_LENGTH_YEARS),
        datetime.min.time()
    )

def default_evaluation_split() -> EvaluationSplit:
    """
    What a run holds back unless a caller says otherwise.

    What the two splits are told apart by is left at its default here, because that is the family's
    answer rather than the run's. train replaces it with whatever the family brought.
    """

    return EvaluationSplit(
        start_date=default_evaluation_start_date(),
        validation_fraction=VALIDATION_FRACTION,
        seed=SPLIT_SEED
    )

LabeledData = tuple[GameSequences, SequenceInputSamples, SequenceInputSamples, SequenceInputSamples]
"""Every sample the family holds: the games, then the training, validation and test splits."""

LabeledDataBuilder = Callable[[datetime, EvaluationSplit, int, bool], LabeledData]
"""Builds samples from a training start, an evaluation split, a sample step size and a debug flag."""

@dataclass(frozen=True)
class TrainingResult():
    """
    What one finished run produced.

    A caller comparing two runs reads this rather than the report the run also wrote, so a sweep of
    settings never has to parse its own output back.
    """

    run: trainer.TrainingRun
    scores: dict[str, float]
    """How the saved model scored on its held-out games, or empty when it was not scored."""

    evaluation: metrics.ModelEvaluation | None = None
    """What was written beside the model, which is what the site reads. None when it was not scored."""

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

    split_on: SplitKey = SplitKey.SUBJECT
    """
    What tells this family's validation and test samples apart. See samples.EvaluationSplit.

    The subject unless a family says otherwise, because a league of players halves cleanly and a
    player then appears in one split only. A family whose subjects are its thirty teams says the
    game instead, since halving those would measure a model on fifteen of them.
    """

    build_description: tuple = ()
    """Anything else deciding what a build holds, beyond the columns and the output shape."""

@dataclass(frozen=True)
class EvaluationSettings():
    """The settings needed to rebuild exactly the splits a model was originally scored on."""

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
    """Reads a model's recorded split settings, when its file was saved after this was added."""

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
    """Reads split settings from reports written before model files recorded them directly."""

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
    """
    Everything that decides what a build holds, written as plain data so it can be saved beside one.

    A saved build is reused only while this still matches, so changing a column, the value being
    predicted, the class range, how much history a sample needs, how the splits are drawn or how
    many games are stepped over rebuilds rather than silently training on the last one.

    The splits belong here because a saved build holds the finished splits and nothing about them
    can be recovered from it afterwards. Left out, a run under a new split would quietly fit and
    score itself on the old one.
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
        training_start_date,
        evaluation_split,
        chunk_step_size
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

def _check_splits_hold_something(
    split_samples: Sequence[SequenceInputSamples],
    evaluation_split: EvaluationSplit
    ):
    """
    Stops a run whose splits are not all there.

    An empty validation split picks the stopping epoch out of nothing and an empty test split scores
    the finished model on nothing, and neither says a word about it. Both mean the evaluation period
    reaches past the games held, or that a fraction of nought or one emptied one of them.
    """

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
    """
    Builds the three splits and the scalers fitted on the training one.

    Returns:
        (training, validation, test, scaler name to fitted scaler)
    """

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

        # Before the scalers are fitted, which is where an empty split would otherwise stop the run
        # with a message about array shapes rather than about the dates that caused it.
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

def _covered(dataset: SequenceGameDataset) -> str:
    """Which games one split holds, written so that two splits can be read against each other."""

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
    """
    Every scored figure in the words a reader knows, each beside the floor it is read against.

    A figure with no floor is one the floor cannot be scored on, so it is shown on its own rather
    than beside a blank.
    """

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

FLOOR_WINDOW_DAYS = 365
"""
How much of the training era the floor below is worked out over.

The last season before the evaluation period rather than all thirty of them. Scoring changed enough
across the archive that a floor read off the whole of it would be far worse than one anybody would
actually use, which would flatter the model standing beside it.
"""

def _floor_probabilities(
        training_dataset: SequenceGameDataset,
        evaluation_split: EvaluationSplit,
        classes: int,
        samples: int
    ) -> np.ndarray:
    """
    The answer a model that reads nothing would give every game: how often each outcome happened in
    the season before the evaluation period.

    This is what turns a figure into a claim. An average miss of eleven points says nothing on its
    own, and says a great deal beside the thirteen that answering with last season's spread scores
    on the same games.
    """

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
    """
    Scores a saved model on the held-out games. Training uses this after saving, so it also proves
    that the saved file round trips back into a working model.

    Returns:
        (every figure scored, the record written beside the model)
    """

    configuration = model_specs.training_parameters.configuration
    predictions = trainer.predict(
        model,
        test_dataset,
        configuration.batch_size,
        configuration.device,
        datasets.collate_sequence_batch
    )

    # The trainer moved the loss onto the training device, and the predictions come back on the cpu.
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
    """Rewrites a saved model's held-out evaluation without fitting or changing the model itself."""

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
    """
    Fits one model spec, saves it, and writes a report and a score of the run next to it.

    The finished model is scored on the test split, which the run never read, so what it writes is
    the only figure worth publishing. Validation picks the stopping epoch and is reported as part of
    the run rather than as an accuracy.

    Args:
        use_cached_build reuses the last run's preprocessed build when it was made the same way.
        save_cached_build writes this run's build for the next one to reuse.
        evaluation_split says which games are held back and how they are divided. It defaults to the
        last year, halved by whatever this family splits on.

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

    # What the splits are told apart by belongs to the family, not to the run, so a caller pinning
    # the dates cannot accidentally halve thirty teams.
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

    # The columns are saved beside the weights so that a model fit before a column moved reports as
    # unpublishable rather than failing at the first matrix multiply. See models/loading.py.
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
