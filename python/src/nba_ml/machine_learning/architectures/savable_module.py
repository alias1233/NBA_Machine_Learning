import torch.nn as nn
from typing import Any, Callable, Self

MODEL_STATE = 'model_state'

class SavableModule(nn.Module):
    """A module that can be saved to a dictionary and rebuilt from it."""

    SAVED_ARGUMENT_NAMES: tuple[str, ...] = ()
    SAVED_ARGUMENT_CODECS: dict[str, tuple[Callable[[Any], Any], Callable[[Any], Any]]] = {}
    """Maps an argument name to its (encode, decode) functions for saving and loading."""

    @classmethod
    def load_from_saved_parameters_dict(cls, parameters_dict: dict[str, Any]) -> Self:
        arguments = {}
        for name in cls.SAVED_ARGUMENT_NAMES:
            if name not in parameters_dict:
                continue

            decode = cls.SAVED_ARGUMENT_CODECS.get(name)
            arguments[name] = decode[1](parameters_dict[name]) if decode else parameters_dict[name]

        instance = cls(**arguments)
        instance.load_state_dict(parameters_dict[MODEL_STATE])

        return instance

    def get_save_parameters_dict(self) -> dict[str, Any]:
        """Returns the constructor arguments and weights needed to rebuild this model."""

        saved: dict[str, Any] = {}
        for name in self.SAVED_ARGUMENT_NAMES:
            value = getattr(self, name)
            encode = self.SAVED_ARGUMENT_CODECS.get(name)
            saved[name] = encode[0](value) if encode else value

        saved[MODEL_STATE] = self.state_dict()

        return saved
