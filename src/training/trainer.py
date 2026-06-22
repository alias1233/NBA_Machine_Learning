import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from typing import Protocol
import copy

class LossFunction(Protocol):
    def __call__(
        self, 
        prediction: torch.Tensor, 
        target: torch.Tensor
    ) -> torch.Tensor:
        ...

class EarlyStopper():
    """
    Handles ending training early if progress is slowing or reversing. 
    Holds the current best weights of the model for loading later.
    """

    def __init__(
        self, 
        patience: int = 10, 
        min_delta: float = 0.001
        ):
        """
        Args:
            patience is the number of times that the validation loss can stop making progress before training ends.
            min_delta is the minimum drop in loss to be considered making progress.
        """

        self.patience = patience
        self.min_delta = min_delta
        self._counter = 0
        self._min_loss = float('inf')
        self.best_weights: dict | None = None

    def step(
        self,
        validation_loss: float,
        model: nn.Module
        ) -> bool:
        """
        Called whenever the validation dataset is evaluated.
        Returns True to continue training, returns False to end early.
        """

        if validation_loss < self._min_loss:
            self.best_weights = copy.deepcopy(model.state_dict())

        if validation_loss < self._min_loss - self.min_delta:
            self._min_loss = validation_loss
            self._counter = 0

            return True
        
        self._counter += 1
        
        return self._counter < self.patience

    def restore_best_weights(
        self,
        model: nn.Module
        ):
        if self.best_weights is not None:
            model.load_state_dict(self.best_weights)

# TODO: Allow for custom schedulers
# TODO: Potentally use gradient clipping (?)
# TODO: Try ReduceLROnPlateau
def train(
    model: nn.Module,
    input_data: torch.Tensor, 
    output_data: torch.Tensor,
    validation_input_data: torch.Tensor, 
    validation_output_data: torch.Tensor,
    optimizer: torch.optim.Optimizer,
    loss_function: LossFunction,
    epochs: int,
    batch_size: int = 256,
    patience: int = 10,
    min_delta: float = 0.001,
    device: torch.device = torch.device("cpu"),
    evaluation_interval: int = 1,
    log_loss_interval: int = 0
    ):
    """
    Trains a given model with the given parameters.

    Args:
        If patience is set to a negative number, early stopping is disabled.
    """

    early_stop = patience >= 0
    log_loss = log_loss_interval > 0

    if epochs == 0:
        return

    model = model.to(device)
    val_x = validation_input_data.to(device)
    val_y = validation_output_data.to(device)
    train_x = input_data.to(device)
    train_y = output_data.to(device)

    training_dataset = TensorDataset(
        train_x,
        train_y
    )
    training_loader = DataLoader(
        training_dataset,
        batch_size=batch_size,
        shuffle=True,
        drop_last=False
    )

    early_stopper = EarlyStopper(
        patience,
        min_delta
    )

    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer,
        max_lr=optimizer.param_groups[0]["lr"] * 10,
        total_steps=epochs * len(training_loader),
        pct_start=0.3,
        anneal_strategy="cos",
        div_factor=25.0,
        final_div_factor=1000,
    )

    epoch: int = 0
    evaluations: int = 0
    for epoch in range(epochs):

        # Training
        model.train()
        total_loss: float = 0
        num_batches: int = 0

        for batch_x, batch_y in training_loader:
            optimizer.zero_grad()
            prediction = model(batch_x)
            loss = loss_function(prediction, batch_y)
            loss.backward()
            optimizer.step()
            scheduler.step()

            total_loss += loss.item()
            num_batches += 1

        mean_training_loss = total_loss / max(num_batches, 1)

        # Evaluation and validation
        if epoch % evaluation_interval == 0:
            model.eval()
            with torch.no_grad():
                val_prediction = model(val_x)
                val_loss = loss_function(val_prediction, val_y).item()

            if not early_stopper.step(val_loss, model):
                if early_stop:
                    print(f"No improvement for {early_stopper.patience} evaluations.")
                    break

            if log_loss and evaluations % log_loss_interval == 0:
                print(f'Epoch: {epoch} | Current lr: {optimizer.param_groups[0]["lr"]} | Train Loss: {mean_training_loss:.4f} | Val Loss: {val_loss:.4f}')
            evaluations += 1
    
    early_stopper.restore_best_weights(model)

    # Final Validation Evaluation
    model.eval()
    with torch.no_grad():
        val_prediction = model(val_x)
        val_loss = loss_function(val_prediction, val_y).item()

        total_loss: float = 0
        num_batches: int = 0
        for batch_x, batch_y in training_loader:
            train_prediction = model(batch_x)
            train_loss = loss_function(train_prediction, batch_y)

            total_loss += train_loss.item()
            num_batches += 1
        
        mean_training_loss = total_loss / max(num_batches, 1)

    if epoch:
        print(f"Stopping at epoch: {epoch}")

    print(f'Final Loss Values- | Train Loss: {mean_training_loss:.4f} | Val Loss: {val_loss:.4f}')