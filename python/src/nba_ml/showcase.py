"""Defines the sample predictions used by the website's home page hero."""

import json
import os
import random
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from nba_ml import expected_rosters, paths, season, upcoming
from nba_ml.entities import Game, ScheduledGame
from nba_ml.models.families import ALL_FAMILIES, ModelFamily
from nba_ml.models.game_stats import inference as game_stat_inference
from nba_ml.models.player_stats import inference as player_stat_inference
from nba_ml.models.specifications import ModelSpecification
from nba_ml.models.team_stats import inference as team_stat_inference
from nba_ml.stores import player_games, players, teams

FORMAT_VERSION = 1

DEFAULT_COUNT = 6
"""Default number of samples per build."""

ROSTER_WINDOW = timedelta(days=365)
"""How far back to look for players who played for a team."""

MINIMUM_PAST_GAMES = 10
"""Minimum number of past games a prediction needs to be used as a sample."""

MINIMUM_OUTCOMES = 8
"""Minimum number of output classes a model needs to be used for samples."""

@dataclass(frozen=True)
class NamedTeam():
    abbreviation: str
    name: str

@dataclass(frozen=True)
class NamedPlayer():
    id: int
    name: str

@dataclass(frozen=True)
class SampleGame():
    """The game a sample is for, with team names instead of IDs."""

    date: str
    home_team: NamedTeam
    away_team: NamedTeam
    season_type: str
    tipoff: str | None

@dataclass(frozen=True)
class Sample():
    """A model prediction with everything the site needs to display it."""

    family: str
    model: str
    title: str
    predicts: list[str]
    output: dict
    values: list[float]
    past_games: int
    game: SampleGame
    player: NamedPlayer | None
    team: NamedTeam | None
    read_from: str | None

@dataclass(frozen=True)
class Showcase():
    format_version: int
    built_for: str
    """The date the samples were generated for."""

    built_at: str
    samples: list[Sample]

def _rng(day: date) -> random.Random:
    """Returns a random generator seeded by the date, so reruns on the same day pick the same samples."""

    return random.Random(day.toordinal())

def _worth_drawing(family: ModelFamily) -> list[ModelSpecification]:
    """Returns the family's published models that have enough output classes."""

    return [
        specification
        for specification in family.specifications.values()
        if family.is_published(specification) and specification.output.length >= MINIMUM_OUTCOMES
    ]

def _named_team(team_id: int, named: dict[int, NamedTeam]) -> NamedTeam:
    return named[team_id]

def _sample_game(scheduled: ScheduledGame, named: dict[int, NamedTeam]) -> SampleGame:
    return SampleGame(
        date=season.to_date_string(scheduled.game.date),
        home_team=_named_team(scheduled.game.home_team_id, named),
        away_team=_named_team(scheduled.game.away_team_id, named),
        season_type=scheduled.game.season_type.value,
        tipoff=None if scheduled.tipoff is None else scheduled.tipoff.isoformat()
    )

def _roster(team_id: int, cutoff: date) -> list[NamedPlayer]:
    player_ids = player_games.player_ids_on_team(team_id, cutoff)

    return [
        NamedPlayer(id=player.id, name=player.name)
        for player in sorted(players.get_players(player_ids), key=lambda player: player.name)
    ]

def _answer(family_name: str, specification: ModelSpecification, game: Game, subject_team_id: int, player_id: int | None):
    """Runs a prediction with the same inference code the API uses."""

    scenarios = expected_rosters.expected_scenarios(game)

    if family_name == "player_stats":
        assert player_id is not None
        return player_stat_inference.predict(
            specification,
            player_id,
            game,
            expected_rosters.with_player_playing(scenarios[subject_team_id], player_id),
            print_debug=False
        )

    if family_name == "team_stats":
        return team_stat_inference.predict(
            specification, subject_team_id, game, scenarios, print_debug=False
        )

    return game_stat_inference.predict(specification, game, scenarios, print_debug=False)

def _draw(
    chooser: random.Random,
    family: ModelFamily,
    specification: ModelSpecification,
    games: list[ScheduledGame],
    named_teams: dict[int, NamedTeam],
    roster_cutoff: date
    ) -> Sample | None:
    """Tries to build a sample for a random game. Returns None if it fails or has too few past games."""

    scheduled = chooser.choice(games)
    subject_team_id = chooser.choice(scheduled.team_ids)

    player: NamedPlayer | None = None

    if family.name == "player_stats":
        roster = _roster(subject_team_id, roster_cutoff)
        if not roster:
            return None

        player = chooser.choice(roster)

    try:
        prediction = _answer(
            family.name,
            specification,
            scheduled.game,
            subject_team_id,
            None if player is None else player.id
        )
    except Exception:
        return None

    if prediction.past_games < MINIMUM_PAST_GAMES:
        return None

    return Sample(
        family=family.name,
        model=specification.name,
        title=specification.title,
        predicts=list(specification.predicts),
        output=asdict(specification.output),
        values=[float(value) for value in prediction.values],
        past_games=int(prediction.past_games),
        game=_sample_game(scheduled, named_teams),
        player=player,
        team=None if family.name == "game_stats" else _named_team(subject_team_id, named_teams),
        read_from=None if specification.read_from is None else specification.read_from.value
    )

def build(count: int = DEFAULT_COUNT, day: date | None = None) -> Showcase:
    """Builds the day's samples, rotating through the families that have usable models."""

    day = day or season.today()
    chooser = _rng(day)

    ready = upcoming.predictable_games()
    if not ready:
        return Showcase(FORMAT_VERSION, season.to_date_string(day), datetime.now(timezone.utc).isoformat(), [])

    choosable = [
        (family, specification)
        for family in ALL_FAMILIES
        for specification in _worth_drawing(family)
    ]
    if not choosable:
        return Showcase(FORMAT_VERSION, season.to_date_string(day), datetime.now(timezone.utc).isoformat(), [])

    named_teams = {
        team.id: NamedTeam(abbreviation=team.abbreviation, name=team.name)
        for team in teams.all_teams()
    }
    roster_cutoff = day - ROSTER_WINDOW

    families = sorted({family.name for family, _ in choosable})
    chooser.shuffle(families)

    samples: list[Sample] = []
    attempts = 0

    while len(samples) < count and attempts < count * 6:
        attempts += 1
        wanted = families[len(samples) % len(families)]
        options = [pair for pair in choosable if pair[0].name == wanted]
        family, specification = chooser.choice(options)

        sample = _draw(chooser, family, specification, ready, named_teams, roster_cutoff)
        if sample is not None:
            samples.append(sample)

    return Showcase(
        format_version=FORMAT_VERSION,
        built_for=season.to_date_string(day),
        built_at=datetime.now(timezone.utc).isoformat(),
        samples=samples
    )

def write(showcase: Showcase, showcase_file: Path = paths.SHOWCASE_FILE) -> Path:
    """Saves the showcase to a temporary file, then renames it to the final path."""

    showcase_file.parent.mkdir(parents=True, exist_ok=True)
    working = showcase_file.with_name(showcase_file.name + ".incomplete")
    working.write_text(json.dumps(asdict(showcase), indent=2, sort_keys=True), encoding="utf-8")
    os.replace(working, showcase_file)

    return showcase_file

def read(showcase_file: Path = paths.SHOWCASE_FILE) -> dict | None:
    """Returns the saved showcase, or None if the file is missing or invalid."""

    try:
        published = json.loads(showcase_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(published, dict) or published.get("format_version") != FORMAT_VERSION:
        return None
    if not isinstance(published.get("samples"), list):
        return None

    return published
