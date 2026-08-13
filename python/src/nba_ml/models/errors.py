"""
Why a prediction could not be made.

A refusal carries a reason as well as a sentence. The sentence names ids and is for a developer
reading a log. The reason is what a caller matches on to word the failure for its own reader, so a
website never has to guess at the meaning of a status code.
"""

from enum import Enum

class Refusal(Enum):
    """Every reason the stored data cannot answer a well formed request."""

    TOO_FEW_GAMES = "too_few_games"
    """The player has not played enough games for a model to read."""

    MISSING_PLAYER_INFORMATION = "missing_player_information"
    """Nothing is stored about the player themselves, which is part of every model input."""

    UNKNOWN_PLAYER_TEAM = "unknown_player_team"
    """Which of the game's two teams the player is on cannot be worked out from their games."""

    NO_TEAM_HISTORY = "no_team_history"
    """The team has no recorded game before the one being predicted."""

    GAME_ALREADY_PLAYED = "game_already_played"
    """The game asked about has been played and collected, so it is not a prediction to make."""

class PredictionRefused(ValueError):
    """The request is well formed, and what is stored cannot answer it."""

    def __init__(self, reason: Refusal, message: str):
        super().__init__(message)

        self.reason = reason
