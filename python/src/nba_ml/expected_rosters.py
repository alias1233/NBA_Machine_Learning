"""Works out each team's expected lineup from the roster and injury snapshot."""

from datetime import date

from nba_ml.entities import Game, RosterScenario
from nba_ml.feature_engineering import roster_columns, team_rosters
from nba_ml.stores import player_games, rosters, team_games

def _last_lineup(team_id: int, before: date) -> set[int]:
    """Returns the IDs of the players who played in the team's most recent game."""

    games = team_rosters.recent_team_games(team_id, before)
    if games.empty:
        return set()

    return player_games.player_ids_in_games(
        team_id,
        [games[team_games.GAME_ID.category_name].iloc[-1]]
    )

def expected_scenario(team_id: int, before: date) -> RosterScenario:
    """Returns how a team's expected lineup differs from its last game before the given date."""

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
    """Returns the expected scenario for both teams in a game, keyed by team ID."""

    return {team_id: expected_scenario(team_id, game.date) for team_id in game.team_ids}

def with_player_playing(scenario: RosterScenario, player_id: int) -> RosterScenario:
    """Returns the scenario with the given player removed from the absent list."""

    if player_id not in scenario.without:
        return scenario

    return RosterScenario(scenario.without - {player_id}, scenario.returning)
