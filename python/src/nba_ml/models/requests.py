"""Request checks shared by every model family."""

from nba_ml import season
from nba_ml.entities import Game
from nba_ml.models.errors import PredictionRefused, Refusal
from nba_ml.stores import team_games

def refuse_a_played_game(target_game: Game):
    """Raises PredictionRefused if either team already has a stored game on the game's date."""

    played = team_games.teams_with_game_on(target_game.date, target_game.team_ids)

    if played:
        raise PredictionRefused(
            Refusal.GAME_ALREADY_PLAYED,
            f"{'Teams' if len(played) > 1 else 'Team'} "
            f"{' and '.join(str(team_id) for team_id in sorted(played))} already played on "
            f"{season.to_date_string(target_game.date)}, so that game is stored rather than upcoming."
        )
