"""The output types a model can have."""

from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, Literal

class OutputKind(StrEnum):
    """Identifies the output type in API responses."""

    INTEGER_DISTRIBUTION = "integer_distribution"
    CATEGORY_DISTRIBUTION = "category_distribution"
    VALUES = "values"

@dataclass(frozen=True)
class IntegerDistribution():
    """A probability for each integer, or bucket of integers, starting at minimum_value."""

    minimum_value: int
    outcomes: int
    bucket_width: int = 1
    impossible_value: int | None = None
    """An integer inside the range that can't happen, such as a point differential of 0."""

    kind: Literal[OutputKind.INTEGER_DISTRIBUTION] = OutputKind.INTEGER_DISTRIBUTION

    ordered: ClassVar[bool] = True
    """The classes are ordered numeric values."""

    def __post_init__(self):
        if self.impossible_value is None:
            return

        edge = self.impossible_value - self.minimum_value

        if not 0 < edge < self.outcomes * self.bucket_width or edge % self.bucket_width != 0:
            raise ValueError(
                "An impossible value has to fall on a bucket edge inside the range, so that taking "
                "it off the number line leaves every bucket the same width."
            )

    @property
    def length(self) -> int:
        return self.outcomes

    @property
    def first_value(self) -> int:
        return self.minimum_value

    @property
    def value_step(self) -> int:
        """Returns the distance between the values of two neighbouring classes."""

        return self.bucket_width

    def value_at(self, step: int) -> int:
        """Returns the integer that is `step` places above minimum_value, skipping the impossible value."""

        value = self.minimum_value + step

        if self.impossible_value is not None and value >= self.impossible_value:
            return value + 1

        return value

    def values(self, position: int) -> list[int]:
        """Returns every integer covered by the class at the given position."""

        first = position * self.bucket_width

        return [self.value_at(step) for step in range(first, first + self.bucket_width)]

    def value_of(self, position: int) -> float:
        """Returns the midpoint of the integers covered by the class at the given position."""

        values = self.values(position)

        return sum(values) / len(values)

    def label(self, position: int) -> str:
        values = self.values(position)

        return str(values[0]) if len(values) == 1 else f"{values[0]} to {values[-1]}"

@dataclass(frozen=True)
class CategoryDistribution():
    """A probability for each named category. The most notable category comes first."""

    categories: tuple[str, ...]
    kind: Literal[OutputKind.CATEGORY_DISTRIBUTION] = OutputKind.CATEGORY_DISTRIBUTION

    ordered: ClassVar[bool] = False
    """The categories have no order."""

    @property
    def length(self) -> int:
        return len(self.categories)

    @property
    def first_value(self) -> int:
        return 0

    @property
    def value_step(self) -> int:
        return 1

    @property
    def impossible_value(self) -> None:
        return None

    def label(self, position: int) -> str:
        return self.categories[position]

@dataclass(frozen=True)
class Values():
    """A single number for each named quantity."""

    quantities: tuple[str, ...]
    kind: Literal[OutputKind.VALUES] = OutputKind.VALUES

    @property
    def length(self) -> int:
        return len(self.quantities)

    def label(self, position: int) -> str:
        return self.quantities[position]

ModelOutput = IntegerDistribution | CategoryDistribution | Values

ClassDistribution = IntegerDistribution | CategoryDistribution
"""The output types that give a probability per class."""

DISCRIMINATOR = "kind"
"""Name of the field that identifies the output type."""

@dataclass(frozen=True)
class Prediction():
    """A model's output values and the number of past games they were based on."""

    values: list[float]
    past_games: int
