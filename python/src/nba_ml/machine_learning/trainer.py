import time
import torch
import torch.nn as nn
from dataclasses import dataclass, field
from pathlib import Path
from torch.optim.lr_scheduler import LRScheduler, OneCycleLR, ReduceLROnPlateau
from torch.utils.data import DataLoader, Dataset
from typing import Callable, Protocol

def get_best_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")

class LossFunction(Protocol):
    def __call__(
        self,
        prediction: torch.Tensor,
        target: torch.Tensor
    ) -> torch.Tensor:
        ...

MetricFunction = Callable[[torch.Tensor, torch.Tensor], float]
"""Scores one batch of (predictions, targets). Batch scores are averaged over the whole dataset."""

SchedulerFactory = Callable[[torch.optim.Optimizer, int], LRScheduler]
"""Builds a learning rate scheduler from an optimizer and the total number of training steps."""

def one_cycle_scheduler_factory(
    peak_multiplier: float = 10.0,
    warmup_fraction: float = 0.3,
    final_divisor: float = 1000.0
    ) -> SchedulerFactory:
    """Returns the default scheduler factory. OneCycleLR warms up to a peak learning rate, then anneals down."""

    def build(optimizer: torch.optim.Optimizer, total_steps: int) -> LRScheduler:
        return OneCycleLR(
            optimizer,
            max_lr=[group["lr"] * peak_multiplier for group in optimizer.param_groups],
            total_steps=total_steps,
            pct_start=warmup_fraction,
            anneal_strategy="cos",
            div_factor=peak_multiplier,
            final_div_factor=final_divisor,
        )

    return build

@dataclass
class TrainingConfiguration():
    """Settings for a training run."""

    epochs: int
    batch_size: int = 256
    patience: int = 10
    """The number of evaluations without progress before training ends. Negative disables early stopping."""

    min_delta: float = 0
    """The smallest drop in validation loss that counts as progress."""

    evaluation_interval: int = 1
    """Number of epochs between validation evaluations. The last epoch is always evaluated."""

    log_interval: int = 1
    """Number of evaluations between log lines. Zero turns off per-epoch logging."""

    max_gradient_norm: float | None = None
    """If set, gradients are clipped to this norm, which keeps recurrent models stable."""

    device: torch.device = torch.device("cpu")
    scheduler_factory: SchedulerFactory = field(default_factory=one_cycle_scheduler_factory)
    scheduler_steps_per_batch: bool = True
    """True for schedulers that step every batch, like OneCycleLR. False for ones that step every evaluation."""

    data_loader_workers: int = 0

@dataclass
class EpochResult():
    epoch: int
    training_loss: float
    """Measured in training mode, so dropout and batch norm make it higher than the validation loss."""

    validation_loss: float
    learning_rate: float
    seconds: float
    samples_per_second: float
    gradient_norm: float | None = None
    metrics: dict[str, float] = field(default_factory=dict)

@dataclass
class TrainingRun():
    """Results of one call to train."""

    epoch_results: list[EpochResult]
    best_epoch: int
    best_validation_loss: float
    initial_training_loss: float
    initial_validation_loss: float
    final_training_loss: float
    """Measured with the best weights restored and the model in evaluation mode."""

    total_seconds: float
    stop_reason: str

    @property
    def epochs_completed(self) -> int:
        return self.epoch_results[-1].epoch if self.epoch_results else 0

    @property
    def best_metrics(self) -> dict[str, float]:
        for result in self.epoch_results:
            if result.epoch == self.best_epoch:
                return result.metrics

        return {}

class EarlyStopper():
    """Stops training when validation loss stops improving, and keeps the best weights seen so far."""

    def __init__(
        self,
        patience: int = 10,
        min_delta: float = 0.001
        ):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_loss = float('inf')
        self.best_epoch = 0
        self.best_weights: dict | None = None
        self._progress_loss = float('inf')

    def step(
        self,
        validation_loss: float,
        epoch: int,
        model: nn.Module
        ) -> bool:
        """Called after each validation evaluation. Returns False to end training early."""

        # Best weights follow the lowest loss. Patience only resets on an improvement larger than min_delta.
        if validation_loss < self.best_loss:
            self.best_loss = validation_loss
            self.best_epoch = epoch
            self.best_weights = {
                name: tensor.detach().cpu().clone()
                for name, tensor in model.state_dict().items()
            }

        if validation_loss < self._progress_loss - self.min_delta:
            self._progress_loss = validation_loss
            self.counter = 0

            return True

        self.counter += 1

        return self.counter < self.patience

    def restore_best_weights(
        self,
        model: nn.Module
        ):
        if self.best_weights is not None:
            model.load_state_dict(self.best_weights)

def _split_batch(
        batch: list[torch.Tensor],
        device: torch.device
    ) -> tuple[list[torch.Tensor], torch.Tensor]:
    """Moves a batch to the device and splits it into (inputs, target). The target is the last tensor."""

    tensors = [tensor.to(device, non_blocking=True) for tensor in batch]

    return (tensors[:-1], tensors[-1])

def _build_loader(
        dataset: Dataset,
        configuration: TrainingConfiguration,
        shuffle: bool,
        collate_fn: Callable | None,
        drop_last: bool = False
    ) -> DataLoader:

    return DataLoader(
        dataset,
        batch_size=configuration.batch_size,
        shuffle=shuffle,
        drop_last=drop_last,
        collate_fn=collate_fn,
        num_workers=configuration.data_loader_workers,
        persistent_workers=configuration.data_loader_workers > 0,
        pin_memory=configuration.device.type == "cuda"
    )

def _evaluate(
        model: nn.Module,
        loss_function: LossFunction,
        loader: DataLoader,
        device: torch.device,
        metrics: dict[str, MetricFunction] | None = None
    ) -> tuple[float, dict[str, float]]:
    """Returns the mean loss and the mean of every metric over the whole loader."""

    metrics = metrics or {}

    total_loss: float = 0
    total_samples: int = 0
    metric_totals: dict[str, float] = {name: 0.0 for name in metrics}

    model.eval()
    with torch.no_grad():
        for batch in loader:
            inputs, target = _split_batch(batch, device)
            prediction = model(*inputs)
            samples = len(target)

            total_loss += loss_function(prediction, target).item() * samples
            total_samples += samples

            for name, metric in metrics.items():
                metric_totals[name] += metric(prediction, target) * samples

    total_samples = max(total_samples, 1)

    return (
        total_loss / total_samples,
        {name: total / total_samples for name, total in metric_totals.items()}
    )

def _format_epoch_line(
        result: EpochResult,
        total_epochs: int,
        best_validation_loss: float,
        patience_counter: int,
        patience: int
    ) -> str:

    parts = [
        f"Epoch: {result.epoch}/{total_epochs}",
        f"{result.seconds:6.1f}s",
        f"{result.samples_per_second:,.0f} samples/s",
        f"LR: {result.learning_rate:.3e}",
        f"Train Loss: {result.training_loss:.4f}",
        f"Val Loss: {result.validation_loss:.4f}",
        f"Best Loss: {best_validation_loss:.4f}"
    ]

    if result.gradient_norm is not None:
        parts.append(f"grad {result.gradient_norm:.3f}")

    parts += [f"{name} {value:.4f}" for name, value in result.metrics.items()]

    if patience >= 0 and patience_counter > 0:
        parts.append(f"stalled {patience_counter}/{patience}")

    return " | ".join(parts)

def train(
    model: nn.Module,
    training_dataset: Dataset,
    validation_dataset: Dataset,
    optimizer: torch.optim.Optimizer,
    loss_function: LossFunction,
    configuration: TrainingConfiguration,
    collate_fn: Callable | None = None,
    metrics: dict[str, MetricFunction] | None = None
    ) -> TrainingRun:
    """Trains a model. Each dataset item must be the model's inputs followed by the target."""

    if configuration.epochs < 1:
        raise ValueError(f"epochs must be at least 1, got {configuration.epochs}.")

    device = configuration.device
    early_stop = configuration.patience >= 0

    model = model.to(device)
    if isinstance(loss_function, nn.Module):
        # Some losses have buffers that need to be on the same device as the logits.
        loss_function = loss_function.to(device)

    # Drop the last batch, since a batch with one sample breaks batch normalization.
    training_loader = _build_loader(training_dataset, configuration, True, collate_fn, drop_last=True)
    if len(training_loader) == 0:
        training_loader = _build_loader(training_dataset, configuration, True, collate_fn)

    validation_loader = _build_loader(validation_dataset, configuration, False, collate_fn)

    early_stopper = EarlyStopper(
        configuration.patience,
        configuration.min_delta
    )

    scheduler = configuration.scheduler_factory(
        optimizer,
        configuration.epochs * len(training_loader)
    )

    initial_training_loss, _ = _evaluate(model, loss_function, training_loader, device)
    initial_validation_loss, _ = _evaluate(model, loss_function, validation_loader, device)

    if configuration.log_interval > 0:
        print(f"Before training: | Train Loss {initial_training_loss:.4f} | Val Loss {initial_validation_loss:.4f}")

    epoch_results: list[EpochResult] = []
    stop_reason = "completed every epoch"
    evaluations: int = 0
    run_start = time.perf_counter()

    for epoch in range(1, configuration.epochs + 1):
        epoch_start = time.perf_counter()
        epoch_learning_rate = optimizer.param_groups[0]["lr"]

        model.train()
        total_loss: float = 0
        total_samples: int = 0
        total_gradient_norm: float = 0
        steps: int = 0

        for batch in training_loader:
            inputs, target = _split_batch(batch, device)

            optimizer.zero_grad()
            prediction = model(*inputs)
            loss = loss_function(prediction, target)
            loss.backward()

            if configuration.max_gradient_norm is not None:
                total_gradient_norm += float(
                    nn.utils.clip_grad_norm_(model.parameters(), configuration.max_gradient_norm)
                )

            optimizer.step()
            if configuration.scheduler_steps_per_batch:
                scheduler.step()

            samples = len(target)
            total_loss += loss.item() * samples
            total_samples += samples
            steps += 1

        mean_training_loss = total_loss / max(total_samples, 1)
        training_seconds = time.perf_counter() - epoch_start

        if epoch % configuration.evaluation_interval != 0 and epoch != configuration.epochs:
            continue

        validation_loss, epoch_metrics = _evaluate(
            model, loss_function, validation_loader, device, metrics
        )

        if not configuration.scheduler_steps_per_batch:
            if isinstance(scheduler, ReduceLROnPlateau):
                scheduler.step(validation_loss)
            else:
                scheduler.step()

        keep_training = early_stopper.step(validation_loss, epoch, model)

        result = EpochResult(
            epoch=epoch,
            training_loss=mean_training_loss,
            validation_loss=validation_loss,
            learning_rate=epoch_learning_rate,
            seconds=time.perf_counter() - epoch_start,
            samples_per_second=total_samples / max(training_seconds, 1e-9),
            gradient_norm=total_gradient_norm / steps if configuration.max_gradient_norm is not None and steps else None,
            metrics=epoch_metrics
        )
        epoch_results.append(result)

        if configuration.log_interval > 0 and evaluations % configuration.log_interval == 0:
            print(_format_epoch_line(
                result,
                configuration.epochs,
                early_stopper.best_loss,
                early_stopper.counter,
                configuration.patience
            ))
        evaluations += 1

        if not keep_training and early_stop:
            stop_reason = f"no improvement for {early_stopper.patience} evaluations"
            break

    total_seconds = time.perf_counter() - run_start

    early_stopper.restore_best_weights(model)

    final_training_loss, _ = _evaluate(model, loss_function, training_loader, device)

    if configuration.log_interval > 0:
        print(f"Stopped at epoch {epoch_results[-1].epoch if epoch_results else 0} because: {stop_reason}.")
        print(
            f"Best weights from epoch {early_stopper.best_epoch} | "
            f"Train Loss: {final_training_loss:.4f} | Val Loss: {early_stopper.best_loss:.4f}"
        )

    return TrainingRun(
        epoch_results=epoch_results,
        best_epoch=early_stopper.best_epoch,
        best_validation_loss=early_stopper.best_loss,
        initial_training_loss=initial_training_loss,
        initial_validation_loss=initial_validation_loss,
        final_training_loss=final_training_loss,
        total_seconds=total_seconds,
        stop_reason=stop_reason
    )

def predict(
    model: nn.Module,
    dataset: Dataset,
    batch_size: int = 256,
    device: torch.device = torch.device("cpu"),
    collate_fn: Callable | None = None
    ) -> torch.Tensor:
    """Runs the model over every sample in order and returns the predictions on the cpu."""

    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=collate_fn
    )

    model = model.to(device)
    model.eval()

    predictions = []
    with torch.no_grad():
        for batch in loader:
            inputs, _ = _split_batch(batch, device)
            predictions.append(model(*inputs).cpu())

    return torch.cat(predictions)

def graph_loss_progress(
    training_run: TrainingRun,
    save_graph_directory_path: Path | None = None
    ):
    """Plots the loss curves and learning rate schedule of a training run."""

    import matplotlib.pyplot as plt

    epochs = [0] + [result.epoch for result in training_run.epoch_results]
    train_losses = [training_run.initial_training_loss] + [result.training_loss for result in training_run.epoch_results]
    validation_losses = [training_run.initial_validation_loss] + [result.validation_loss for result in training_run.epoch_results]

    figure, (loss_axes, learning_rate_axes) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

    loss_axes.plot(
        epochs,
        train_losses,
        label = 'Training Loss (measured while training)',
        color = 'blue',
        marker = 'o'
        )
    loss_axes.plot(
        epochs,
        validation_losses,
        label = 'Validation Loss',
        color = 'red',
        marker = 'v'
        )
    loss_axes.axvline(
        x=training_run.best_epoch,
        color='green',
        linestyle='--',
        label=f'Best Epoch: {training_run.best_epoch}'
        )
    loss_axes.set_title("Training Loss Progress")
    loss_axes.set_ylabel("Loss")
    loss_axes.legend()
    loss_axes.grid(True, linestyle='--', alpha=0.7)

    learning_rate_axes.plot(
        [result.epoch for result in training_run.epoch_results],
        [result.learning_rate for result in training_run.epoch_results],
        color='purple',
        marker='.'
        )
    learning_rate_axes.set_ylabel("Learning Rate")
    learning_rate_axes.set_xlabel("Epochs")
    learning_rate_axes.grid(True, linestyle='--', alpha=0.7)

    figure.tight_layout()

    if save_graph_directory_path is not None:
        save_graph_directory_path.mkdir(parents=True, exist_ok=True)
        figure.savefig(save_graph_directory_path / "training_progress.png")

    else:
        plt.show()

    plt.close(figure)
