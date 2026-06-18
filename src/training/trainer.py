import torch
import torch.nn as nn

def train(
        model: nn.Module,
        optimizer: torch.optim.Optimizer,
        epochs: int, 
        input_data: torch.Tensor, 
        output_data: torch.Tensor,
        validation_input_data: torch.Tensor, 
        validation_output_data: torch.Tensor,
        loss_function,
        log_loss_interval: int = 0
        ):
    
    # TODO: Implement using a data loader for batching to have SGD
    # TODO: Use a scheduler
    # TODO: Implement an early stopper
    # TODO: Use GPU to train instead of CPU
    
    log_loss = log_loss_interval != 0

    for i in range(epochs):

        # Training
        model.train()
        optimizer.zero_grad()
        prediction = model(input_data)
        loss = loss_function(prediction, output_data)
        loss.backward()
        optimizer.step()

        # Validation
        if log_loss and i % log_loss_interval == 0:
            model.eval()
            with torch.no_grad():
                val_prediction = model(validation_input_data)
                val_loss = loss_function(val_prediction, validation_output_data)

            print(f'Epoch: {i} | Train Loss: {loss.item():.4f} | Val Loss: {val_loss.item():.4f}')
    
    model.eval()
    with torch.no_grad():
        val_prediction = model(validation_input_data)
        val_loss = loss_function(val_prediction, validation_output_data)

    print(f'Final Loss Values- | Train Loss: {loss.item():.4f} | Val Loss: {val_loss.item():.4f}')