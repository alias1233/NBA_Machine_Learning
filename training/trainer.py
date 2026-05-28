import torch
import torch.nn as nn

# Simple Trainer Using Adam Optimizer
class Trainer():
    def __init__(self, learning_rate: float, model: nn.Module):
        self.optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
        self.model = model

    def train(
            self,
            epochs: int, 
            input_data: torch.Tensor, 
            output_data: torch.Tensor,
            loss_function,
            save_model_path: str, 
            log_loss_interval: int = 0
            ):
        
        self.model.train()
        log_loss = log_loss_interval != 0

        for i in range(epochs):
            self.optimizer.zero_grad()
            prediction = self.model(input_data)
            loss = loss_function(prediction, output_data)

            if log_loss and i % log_loss_interval == 0:
                print(f'Epoch: {i} Loss: {loss.item()}')

            loss.backward()
            self.optimizer.step()

        torch.save(self.model.state_dict(), save_model_path)