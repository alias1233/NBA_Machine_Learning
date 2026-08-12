"""
What a model answers with.

Every answer is an ordered list of numbers. The output says what each position means, so the service
can describe a model and return its answer without knowing what it predicts, and a stored answer
still reads correctly on its own.

A model does not have to be a distribution. Any statistic worth predicting belongs here, whether the
answer is a chance per outcome or a plain amount. Adding a shape is one class here, one branch
wherever an answer is drawn, and nothing else.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, Literal

class OutputKind(StrEnum):
    """Names the shape on the wire, so a caller reads the numbers the right way."""

    INTEGER_DISTRIBUTION = "integer_distribution"
    CATEGORY_DISTRIBUTION = "category_distribution"
    VALUES = "values"

@dataclass(frozen=True)
class IntegerDistribution():
    """
    A probability for each whole number, counting up from minimum_value.

    A position may stand for a run of whole numbers rather than one. bucket_width says how many, and
    at one the answer is a probability per whole number. Wider buckets are for a model with too few
    samples to fill a class per outcome: the same data spread over fewer classes is a steadier answer.

    Odds for a line are the sums either side of it, so a caller holding the answer can read any line
    without asking again. A line falling inside a bucket splits it, and the bucket is read as spread
    evenly over the whole numbers it holds, because that is all the model claims to know.
    """

    minimum_value: int
    outcomes: int
    bucket_width: int = 1
    impossible_value: int | None = None
    """
    A whole number inside the range that cannot happen, such as a point differential of zero.

    It is taken off the number line rather than out of one bucket, so every bucket still covers
    bucket_width outcomes and the buckets either side of it read as -4 to -1 and 1 to 4. Nothing
    reads the value: it is left out of every label, out of the value a position is read as, and out
    of the odds on a line. It has to sit on a bucket edge, so no bucket is split by it.
    """

    kind: Literal[OutputKind.INTEGER_DISTRIBUTION] = OutputKind.INTEGER_DISTRIBUTION

    ordered: ClassVar[bool] = True
    """The positions sit on a number line, so landing one out is a smaller miss than landing ten out."""

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
        """How far apart the values two neighbouring positions stand for are."""

        return self.bucket_width

    def value_at(self, step: int) -> int:
        """
        The whole number a count of steps up from the lowest one stands for.

        The impossible value is not on the line, so every step from it upward lands one higher.
        """

        value = self.minimum_value + step

        if self.impossible_value is not None and value >= self.impossible_value:
            return value + 1

        return value

    def values(self, position: int) -> list[int]:
        """Every whole number a position stands for, which is what its probability is spread over."""

        first = position * self.bucket_width

        return [self.value_at(step) for step in range(first, first + self.bucket_width)]

    def value_of(self, position: int) -> float:
        """The middle of what a position stands for, which is the value it is read as."""

        values = self.values(position)

        return sum(values) / len(values)

    def label(self, position: int) -> str:
        values = self.values(position)

        return str(values[0]) if len(values) == 1 else f"{values[0]} to {values[-1]}"

@dataclass(frozen=True)
class CategoryDistribution():
    """
    A probability per named category, for an answer with no number line to sit on.

    Categories are listed most notable first, because a caller drawing one leads with the first.
    """

    categories: tuple[str, ...]
    kind: Literal[OutputKind.CATEGORY_DISTRIBUTION] = OutputKind.CATEGORY_DISTRIBUTION

    ordered: ClassVar[bool] = False
    """The categories have no order, so one wrong answer is no nearer than another."""

    @property
    def length(self) -> int:
        return len(self.categories)

    @property
    def first_value(self) -> int:
        """Categories are numbered from zero, so the first position stands for the value zero."""

        return 0

    @property
    def value_step(self) -> int:
        """One category per position, which is what the shared fit reads them as."""

        return 1

    @property
    def impossible_value(self) -> None:
        """Every category is one the model can answer with, so none of them is ruled out."""

        return None

    def label(self, position: int) -> str:
        return self.categories[position]

@dataclass(frozen=True)
class Values():
    """One number per named quantity, which is what a model predicting an amount answers with."""

    quantities: tuple[str, ...]
    kind: Literal[OutputKind.VALUES] = OutputKind.VALUES

    @property
    def length(self) -> int:
        return len(self.quantities)

    def label(self, position: int) -> str:
        return self.quantities[position]

ModelOutput = IntegerDistribution | CategoryDistribution | Values

ClassDistribution = IntegerDistribution | CategoryDistribution
"""
The shapes that give a probability per class, which is what a classifier answers with.

Both number their positions from zero and say what value the first one stands for, how far apart two
of them are and which value the line skips, so one training run fits either and nothing in it has to
know which it is fitting.
"""

DISCRIMINATOR = "kind"
"""The field telling the shapes apart, which is what lets one response type carry any of them."""

@dataclass(frozen=True)
class Prediction():
    """
    One finished answer: the numbers, and how many earlier games stood behind them.

    Every model here reads a sequence of past games, so how many were found is worth carrying beside
    the answer. It is what lets a caller say that an answer rests on very little.
    """

    values: list[float]
    past_games: int
