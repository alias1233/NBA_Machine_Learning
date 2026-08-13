"""
What every family checks about a prediction request before it builds anything.

A request can be well formed and still be one the stores cannot answer honestly. Those checks do not
depend on what is being predicted, so they sit here rather than once per family, and a family calls
them at the top of its inference path so a refusal costs nothing.
"""

from nba_ml import season
from nba_ml.entities import Game
from nba_ml.models.errors import PredictionRefused, Refusal
from nba_ml.stores import team_games

def refuse_a_played_game(target_game: Game):
    """
    Refuses a game one of its two teams has already played.

    Every build stands the predicted game in as one more row and reads the rows in front of it. A
    game already stored is in front of its own placeholder, so the row would count a game the
    sequence beside it stops short of, and the answer would be built from two different histories.

    No team plays twice in a day, so this is only ever reached by asking about a game that has been
    played and collected.

    Raises:
        PredictionRefused naming the teams that have already played that day.
    """

    played = team_games.teams_with_game_on(target_game.date, target_game.team_ids)

    if played:
        raise PredictionRefused(
            Refusal.GAME_ALREADY_PLAYED,
            f"{'Teams' if len(played) > 1 else 'Team'} "
            f"{' and '.join(str(team_id) for team_id in sorted(played))} already played on "
            f"{season.to_date_string(target_game.date)}, so that game is stored rather than upcoming."
        )
