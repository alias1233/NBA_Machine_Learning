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

def _get_training_validation_loss(
        model: torch.nn.Module,
        loss_function: LossFunction,
        training_loader: DataLoader,
        val_x: torch.Tensor,
        val_y: torch.Tensor,
    ):
    """
    Evaluates losses on the model.

    Returns:
        (mean training lsos, validation loss)
    """

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

    return (mean_training_loss, val_loss)

# TODO: Allow for custom schedulers
# TODO: Potentally use gradient clipping (?)
# TODO: Try ReduceLROnPlateau
# TODO: Incorporate gradient limiting
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
    ) -> list[tuple[int, tuple[float, float]]] | None:
    """
    Trains a given model with the given parameters.

    Args:
        If patience is set to a negative number, early stopping is disabled.

    Returns:
        None if the training fails
        Otherwise: 
        list (epoch ,(training loss at epoch, validation loss at epoch))
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

    losses_over_epoch_evaluations: list[tuple[int, tuple[float, float]]] = []

    initial_train_loss, initial_validation_loss = _get_training_validation_loss(
            model,
            loss_function,
            training_loader,
            val_x,
            val_y
        )
    if log_loss:
        print(f'Initial Loss Values- | Train Loss: {initial_train_loss:.4f} | Val Loss: {initial_validation_loss:.4f}')
    
    losses_over_epoch_evaluations.append(
        (0, (initial_train_loss, initial_validation_loss))
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
            
            losses_over_epoch_evaluations.append(
                (epoch + 1, (mean_training_loss, val_loss))
            )

            if log_loss and evaluations % log_loss_interval == 0:
                print(f'Epoch: {epoch} | Current lr: {optimizer.param_groups[0]["lr"]} | Train Loss: {mean_training_loss:.4f} | Val Loss: {val_loss:.4f}')
            evaluations += 1
    
    early_stopper.restore_best_weights(model)

    if epoch:
        print(f"Stopping at epoch: {epoch}")

    # Final Validation Evaluation
    if log_loss:
        final_train_loss, final_validation_loss = _get_training_validation_loss(
            model,
            loss_function,
            training_loader,
            val_x,
            val_y
        )
        print(f'Final Loss Values- | Train Loss: {final_train_loss:.4f} | Val Loss: {final_validation_loss:.4f}')

    return losses_over_epoch_evaluations

def graph_loss_progress(
    losses_over_epochs: list[tuple[int, tuple[float, float]]],
    save_graph_directory_path: str | None = None
    ):
    """
    Args:
        losses_over_epochs must be a list (epoch, (train loss, validation loss)).
    """

    import os
    import matplotlib.pyplot as plt

    epochs, losses = zip(*losses_over_epochs)
    train_losses, validation_losses = zip(*losses)
    
    plt.figure(figsize=(10, 4))
    plt.plot(
        epochs,
        train_losses,
        label = 'Training Loss',
        color = 'blue',
        marker = 'o'
        )
    plt.plot(
        epochs,
        validation_losses,
        label = 'Validation Loss',
        color = 'red',
        marker = 'v'
        )
    plt.title("Training Loss Progress")
    plt.xlabel("Epochs")
    plt.ylabel("Loss")
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)

    if save_graph_directory_path is not None:
        os.makedirs(save_graph_directory_path, exist_ok=True)
        plt.savefig(save_graph_directory_path.rstrip('/') + "/training_progress.png")
        plt.close()
        
    else:
        plt.show()