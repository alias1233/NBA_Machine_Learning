import torch.nn as nn
from dataclasses import dataclass, fields
from typing import Any

from .savable_module import SavableModule

INPUT_DIM = 'input_dim'
OUTPUT_DIM = 'output_dim'
HIDDEN_LAYERS = 'hidden_layers'

@dataclass(frozen=True)
class LayerParameters():
    num_nodes: int
    activation_function: nn.Module | None = None
    layer_normalization: bool = False
    dropout_rate: float = 0

def encode_layer_parameters(hidden_layers: list[LayerParameters]) -> list[dict[str, Any]]:
    """
    Turns the layer settings into plain dictionaries, so a saved model keeps loading after this
    module moves.
    """

    return [
        {field.name: getattr(layer, field.name) for field in fields(layer)}
        for layer in hidden_layers
    ]

def decode_layer_parameters(saved_hidden_layers: list) -> list[LayerParameters]:
    return [
        layer if isinstance(layer, LayerParameters) else LayerParameters(**layer)
        for layer in saved_hidden_layers
    ]

LAYER_PARAMETERS_CODEC = {HIDDEN_LAYERS: (encode_layer_parameters, decode_layer_parameters)}

class FeedForward(SavableModule):
    """A configurable stack of fully connected layers."""

    SAVED_ARGUMENT_NAMES = (INPUT_DIM, OUTPUT_DIM, HIDDEN_LAYERS)
    SAVED_ARGUMENT_CODECS = LAYER_PARAMETERS_CODEC

    def __init__(
            self,
            input_dim: int,
            output_dim: int,
            hidden_layers: list[LayerParameters]
            ) -> None:
        """
        Args:
            hidden_layers: one entry per hidden layer, in order.
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

            if layer_parameters.layer_normalization:
                layers.append(nn.LayerNorm(layer_parameters.num_nodes))

            if layer_parameters.activation_function is not None:
                layers.append(layer_parameters.activation_function)

            if layer_parameters.dropout_rate > 0:
                layers.append(nn.Dropout(layer_parameters.dropout_rate))

            input_size = layer_parameters.num_nodes

        layers.append(nn.Linear(in_features=input_size, out_features=output_dim))

        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)
