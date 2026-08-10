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

    Odds for a line are the sums either side of it, so a caller holding the answer can read any line
    without asking again.
    """

    minimum_value: int
    outcomes: int
    kind: Literal[OutputKind.INTEGER_DISTRIBUTION] = OutputKind.INTEGER_DISTRIBUTION

    ordered: ClassVar[bool] = True
    """The positions sit on a number line, so landing one out is a smaller miss than landing ten out."""

    @property
    def length(self) -> int:
        return self.outcomes

    @property
    def first_value(self) -> int:
        return self.minimum_value

    def label(self, position: int) -> str:
        return str(self.minimum_value + position)

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

Both number their positions from zero and say what value the first one stands for, so one training
run fits either and nothing in it has to know which it is fitting.
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
