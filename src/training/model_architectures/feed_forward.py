import torch.nn as nn
from typing import Any

INPUT_DIM = 'input_dim'
OUTPUT_DIM = 'output_dim'
HIDDEN_LAYERS = 'hidden_layers'
MODEL_STATE = 'model_state'

class FeedForward(nn.Module):
    """
    Simple Feed Forward Model

    Uses RELU activation functions after each hidden layer.
    """

    def __init__(self, input_dim: int, output_dim: int, hidden_layers: list) -> None: 
        """
        Initializes the model.
        Args: 
            hidden_layers: holds the number of nodes for each layer, with each index corresponding to a hidden layer.
        """
        super().__init__()

        self.input_dim = input_dim
        self.output_dim = output_dim
        self.hidden_layers = hidden_layers

        layers = []
        input_size = input_dim

        for layer_size in hidden_layers:
            layers.append(nn.Linear(in_features=input_size, out_features=layer_size))
            layers.append(nn.ReLU())
            input_size = layer_size

        layers.append(nn.Linear(in_features=input_size, out_features=output_dim))

        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)
    
    def get_save_parameters_dict(self) -> dict[str, Any]:
        params = {
            INPUT_DIM : self.input_dim,
            OUTPUT_DIM : self.output_dim,
            HIDDEN_LAYERS : self.hidden_layers,
            MODEL_STATE : self.state_dict()
        }
        return params