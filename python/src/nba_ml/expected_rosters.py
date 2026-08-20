"""
Who each side is expected to play, rather than who it played last.

Every build assumes a team plays whoever played its last game, because a box score is the only thing
that ever said who took the floor. That assumption is wrong for exactly two reasons: somebody in
that lineup will not play this one, and somebody who was not in it will. The collected roster
snapshot answers both, so this turns it into the same RosterScenario a caller would have named by
hand. See stores/rosters.py.

Nothing here changes a prediction on its own. It produces a scenario, and the caller decides whether
to use it, which is what lets the site fill its roster controls in with these and still hand them
back to the reader to change. See nba_ml/api/app.py.

With no snapshot held, every scenario is empty, which is exactly how predictions behaved before any
of this was collected.
"""

from datetime import date

from nba_ml.entities import Game, RosterScenario
from nba_ml.feature_engineering import roster_columns, team_rosters
from nba_ml.stores import player_games, rosters, team_games

def _last_lineup(team_id: int, before: date) -> set[int]:
    """
    Who played the team's most recent game, which is the lineup every build assumes it will play.

    Read out of the same games the roster columns are measured against, so what this compares
    against is what a prediction will actually be built on.
    """

    games = team_rosters.recent_team_games(team_id, before)
    if games.empty:
        return set()

    return player_games.player_ids_in_games(
        team_id,
        [games[team_games.GAME_ID.category_name].iloc[-1]]
    )

def expected_scenario(team_id: int, before: date) -> RosterScenario:
    """
    How one team's expected lineup differs from the one it last played, before a given day.

    A player from that lineup is counted out only when the snapshot positively says so, either
    because the injury report rules them out or because they are now on another team. A player the
    snapshot has never heard of is left in the lineup, because a service that simply does not list
    somebody must not be read as that somebody being dropped.

    A player joining the lineup has to be worth counting to be named. The roster columns only ever
    read core players, so anyone below that cutoff would be a name in the answer's way rather than a
    change to it. That keeps the list to the returning star and the traded star, which is what the
    lineup a build assumes actually gets wrong.
    """

    lineup = _last_lineup(team_id, before)
    on_team = rosters.on_team(team_id)

    if not on_team:
        return RosterScenario()

    known = rosters.entries_for(lineup)
    without = {
        player_id
        for player_id, entry in known.items()
        if entry.team_id != team_id or not entry.playing
    }

    joining = {entry.player_id for entry in on_team if entry.playing} - lineup
    minutes = player_games.recent_mean_minutes(joining, before, team_rosters.ROLLING_WINDOW)
    returning = {
        player_id
        for player_id, played in minutes.items()
        if played >= roster_columns.CORE_PLAYER_MINUTES_CUTOFF
    }

    return RosterScenario.of(without, returning)

def expected_scenarios(game: Game) -> dict[int, RosterScenario]:
    """Both sides of a game, keyed by team id, which is how a build asks for them."""

    return {team_id: expected_scenario(team_id, game.date) for team_id in game.team_ids}

def with_player_playing(scenario: RosterScenario, player_id: int) -> RosterScenario:
    """
    The same scenario with one player never counted as absent.

    A player game statistic is about somebody taking the floor, so asking for one out of a lineup
    that sits them out is a question with no answer. Only a scenario nobody asked for is corrected
    here. A reader who names somebody out by hand is answered as they asked.
    """

    if player_id not in scenario.without:
        return scenario

    return RosterScenario(scenario.without - {player_id}, scenario.returning)
