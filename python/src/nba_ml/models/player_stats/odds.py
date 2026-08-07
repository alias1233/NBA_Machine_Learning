"""
Reading a predicted distribution: the value it expects, and the odds it gives a line.

A prediction is a probability per whole number outcome, so every question about a line is a sum over
that array. Nothing here loads a model, which is why the browser can do the same arithmetic itself.
"""

from dataclasses import dataclass
from typing import Sequence

@dataclass(frozen=True)
class LineOdds():
    """The three ways a line can settle. They add up to one."""

    over: float
    under: float
    push: float
    """The chance of landing exactly on the line, which only a whole number line can do."""

def _values(probabilities: Sequence[float], minimum_value: int):
    """Each probability paired with the outcome it stands for."""

    return ((minimum_value + offset, probability) for offset, probability in enumerate(probabilities))

def expected_value(probabilities: Sequence[float], minimum_value: int = 0) -> float:
    """The average outcome the distribution implies."""

    return sum(value * probability for value, probability in _values(probabilities, minimum_value))

def calculate_odds(
    probabilities: Sequence[float],
    line: float,
    minimum_value: int = 0
    ) -> LineOdds:
    """
    Args:
        minimum_value is the outcome the first probability stands for, which a model specification
        holds as minimum_of_stat.
    """

    over = 0.0
    under = 0.0
    push = 0.0

    for value, probability in _values(probabilities, minimum_value):
        if value > line:
            over += probability
        elif value < line:
            under += probability
        else:
            push += probability

    return LineOdds(over, under, push)

def most_likely_outcomes(
    probabilities: Sequence[float],
    count: int,
    minimum_value: int = 0
    ) -> list[tuple[int, float]]:
    """The count outcomes the model gives the most weight to, likeliest first."""

    ranked = sorted(_values(probabilities, minimum_value), key=lambda pair: -pair[1])

    return ranked[:count]
