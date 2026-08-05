import torch.nn as nn
from dataclasses import fields, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Self

def count_parameters(model: nn.Module) -> tuple[int, int]:
    """
    Returns (total parameters, trainable parameters).
    """

    total = sum(parameter.numel() for parameter in model.parameters())
    trainable = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)

    return (total, trainable)

def describe_model(model: nn.Module) -> dict[str, Any]:
    """
    Summarizes a model's size, with a parameter count for each of its direct submodules.
    """

    total, trainable = count_parameters(model)

    description: dict[str, Any] = {
        "class": type(model).__name__,
        "total parameters": total,
        "trainable parameters": trainable
    }
    description.update({
        f"parameters in {name}": sum(parameter.numel() for parameter in submodule.parameters())
        for name, submodule in model.named_children()
    })

    return description

def values_of(instance: Any) -> dict[str, Any]:
    """
    Flattens a dataclass into a name to value mapping so it can be reported field by field.
    """

    if not is_dataclass(instance):
        raise TypeError(f"Expected a dataclass, got {type(instance).__name__}.")

    return {field.name.replace('_', ' '): getattr(instance, field.name) for field in fields(instance)}

def format_value(value: Any) -> str:
    """
    Renders one reported value as a short line of text.
    """

    if isinstance(value, bool):
        return str(value)

    if isinstance(value, float):
        return f"{value:.6g}"

    if isinstance(value, int):
        return f"{value:,}"

    if isinstance(value, nn.Module):
        settings = value.extra_repr()
        return f"{type(value).__name__}({settings})" if settings else type(value).__name__

    if callable(value):
        return getattr(value, "__qualname__", repr(value))

    if isinstance(value, (list, tuple)) and value and is_dataclass(value[0]):
        return "\n" + "\n".join(f"    {item}" for item in value)

    return str(value)

def print_values(heading: str, values: Mapping[str, Any]):
    """
    Prints one reported section to the console in the same shape the report file uses.
    """

    print(f"\n--- {heading} ---")
    for name, value in values.items():
        print(f"{name}: {format_value(value)}")

class TrainingReport():
    """
    Collects labeled sections of a training run and writes them to a plain text file.
    """

    def __init__(self, title: str):
        self.title = title
        self._sections: list[tuple[str, dict[str, Any] | str]] = []

    def add(self, heading: str, values: Mapping[str, Any]) -> Self:
        self._sections.append((heading, dict(values)))

        return self

    def add_text(self, heading: str, text: str) -> Self:
        """
        Adds a section that is already formatted, such as a model printed layer by layer.
        """

        self._sections.append((heading, text))

        return self

    def render(self) -> str:
        lines = [
            "=" * 79,
            self.title,
            f"Written {datetime.now().isoformat(timespec='seconds')}",
            "=" * 79
        ]

        for heading, section in self._sections:
            lines += ["", heading, "-" * len(heading)]

            if isinstance(section, str):
                lines.append(section)
                continue

            width = max((len(name) for name in section), default=0)
            lines += [f"{name:<{width}}  {format_value(value)}" for name, value in section.items()]

        return "\n".join(lines) + "\n"

    def write(self, file_path: str) -> str:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(), encoding="utf-8")

        return str(path)
