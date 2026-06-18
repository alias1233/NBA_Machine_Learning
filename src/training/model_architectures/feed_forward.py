import torch.nn as nn
from typing import Any, Type
from dataclasses import dataclass

INPUT_DIM = 'input_dim'
OUTPUT_DIM = 'output_dim'
HIDDEN_LAYERS = 'hidden_layers'
MODEL_STATE = 'model_state'

@dataclass(frozen=True)
class LayerParameters():
    num_nodes: int
    activation_function: Type[nn.Module] | None = None
    batch_normalization: bool = False
    dropout_rate: float = 0

class FeedForward(nn.Module):
    """
    Simple Configurable Feed Forward Model
    """

    def __init__(self, input_dim: int, output_dim: int, hidden_layers: list[LayerParameters]) -> None: 
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

        for layer_parameters in hidden_layers:
            layers.append(
                nn.Linear(
                    in_features=input_size, 
                    out_features=layer_parameters.num_nodes
                    )
                    )

            if layer_parameters.batch_normalization:
                layers.append(nn.BatchNorm1d(layer_parameters.num_nodes))
            
            if layer_parameters.activation_function:
                layers.append(layer_parameters.activation_function())

            if layer_parameters.dropout_rate > 0:
                layers.append(nn.Dropout(layer_parameters.dropout_rate))

            input_size = layer_parameters.num_nodes

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