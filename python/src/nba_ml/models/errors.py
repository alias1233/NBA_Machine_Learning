"""Errors for predictions that can't be made."""

from enum import Enum

class Refusal(Enum):
    """Reasons a valid request can't be answered with the stored data."""

    TOO_FEW_GAMES = "too_few_games"
    """The player has not played enough games."""

    MISSING_PLAYER_INFORMATION = "missing_player_information"
    """The player has no stored player info."""

    UNKNOWN_PLAYER_TEAM = "unknown_player_team"
    """The player's team in this game can't be determined from their past games."""

    NO_TEAM_HISTORY = "no_team_history"
    """The team has no stored games before the one being predicted."""

    GAME_ALREADY_PLAYED = "game_already_played"
    """The game has already been played and collected."""

class PredictionRefused(ValueError):
    """Raised when a valid request can't be answered with the stored data."""

    def __init__(self, reason: Refusal, message: str):
        super().__init__(message)

        self.reason = reason
