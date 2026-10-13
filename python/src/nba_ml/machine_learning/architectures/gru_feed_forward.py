import torch
import torch.nn as nn

from .feed_forward import LAYER_PARAMETERS_CODEC, FeedForward, LayerParameters
from .savable_module import SavableModule

SEQUENCE_INPUT_DIM = 'sequence_input_dim'
STATIC_INPUT_DIM = 'static_input_dim'
OUTPUT_DIM = 'output_dim'
HIDDEN_LAYERS = 'hidden_layers'
GRU_HIDDEN_DIM = 'gru_hidden_dim'
GRU_LAYERS = 'gru_layers'
GRU_DROPOUT_RATE = 'gru_dropout_rate'
SEQUENCE_COUNT = 'sequence_count'

class GRUFeedForward(SavableModule):
    """Runs a GRU over the past game sequences, then passes its output and the static input to a feed forward network."""

    SAVED_ARGUMENT_NAMES = (
        SEQUENCE_INPUT_DIM,
        STATIC_INPUT_DIM,
        OUTPUT_DIM,
        HIDDEN_LAYERS,
        GRU_HIDDEN_DIM,
        GRU_LAYERS,
        GRU_DROPOUT_RATE,
        SEQUENCE_COUNT
    )
    SAVED_ARGUMENT_CODECS = LAYER_PARAMETERS_CODEC

    def __init__(
            self,
            sequence_input_dim: int,
            static_input_dim: int,
            output_dim: int,
            hidden_layers: list[LayerParameters],
            gru_hidden_dim: int,
            gru_layers: int = 1,
            gru_dropout_rate: float = 0,
            sequence_count: int = 1
            ) -> None:
        """gru_dropout_rate only applies between GRU layers, so it is ignored when gru_layers is 1."""
        super().__init__()

        self.sequence_input_dim = sequence_input_dim
        self.static_input_dim = static_input_dim
        self.output_dim = output_dim
        self.hidden_layers = hidden_layers
        self.gru_hidden_dim = gru_hidden_dim
        self.gru_layers = gru_layers
        self.gru_dropout_rate = gru_dropout_rate
        self.sequence_count = sequence_count

        self.gru = nn.GRU(
            input_size=sequence_input_dim,
            hidden_size=gru_hidden_dim,
            num_layers=gru_layers,
            batch_first=True,
            dropout=gru_dropout_rate if gru_layers > 1 else 0
        )

        self.network = FeedForward(
            gru_hidden_dim * sequence_count + static_input_dim,
            output_dim,
            hidden_layers
        )

    def forward(
            self,
            sequences: torch.Tensor,
            sequence_lengths: torch.Tensor,
            static_input: torch.Tensor
            ) -> torch.Tensor:
        """sequences has shape (batch * sequence_count, longest sequence, sequence features)."""

        packed_sequences = nn.utils.rnn.pack_padded_sequence(
            sequences,
            sequence_lengths.cpu(),
            batch_first=True,
            enforce_sorted=False
        )

        _, hidden_states = self.gru(packed_sequences)

        # Reshape to one row per sample, with the hidden states of all its sequences side by side.
        memory = hidden_states[-1].reshape(len(static_input), -1)

        return self.network(torch.cat((memory, static_input), dim=1))
