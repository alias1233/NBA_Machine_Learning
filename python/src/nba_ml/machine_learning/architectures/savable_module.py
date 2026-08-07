import torch.nn as nn
from typing import Any, Callable, Self

MODEL_STATE = 'model_state'

class SavableModule(nn.Module):
    """
    A model that can rebuild itself from a saved dictionary.

    A subclass lists the constructor arguments that define its shape in SAVED_ARGUMENT_NAMES and
    stores each of them on itself under the same name. The saved dictionary then holds those
    arguments plus the learned weights, which is everything needed to load the model back.

    An argument that is not a plain value needs an entry in SAVED_ARGUMENT_CODECS. Python saves a
    custom class by writing down where its module lives, so a saved model that holds one stops
    loading the moment that module moves. Codecs turn those arguments into plain data first.
    """

    SAVED_ARGUMENT_NAMES: tuple[str, ...] = ()
    SAVED_ARGUMENT_CODECS: dict[str, tuple[Callable[[Any], Any], Callable[[Any], Any]]] = {}
    """Argument name to (encode for saving, decode after loading)."""

    @classmethod
    def load_from_saved_parameters_dict(cls, parameters_dict: dict[str, Any]) -> Self:
        arguments = {}
        for name in cls.SAVED_ARGUMENT_NAMES:
            value = parameters_dict[name]
            decode = cls.SAVED_ARGUMENT_CODECS.get(name)
            arguments[name] = decode[1](value) if decode else value

        instance = cls(**arguments)
        instance.load_state_dict(parameters_dict[MODEL_STATE])

        return instance

    def get_save_parameters_dict(self) -> dict[str, Any]:
        """Everything needed to rebuild this model: its shape arguments and its weights."""

        saved: dict[str, Any] = {}
        for name in self.SAVED_ARGUMENT_NAMES:
            value = getattr(self, name)
            encode = self.SAVED_ARGUMENT_CODECS.get(name)
            saved[name] = encode[0](value) if encode else value

        saved[MODEL_STATE] = self.state_dict()

        return saved
