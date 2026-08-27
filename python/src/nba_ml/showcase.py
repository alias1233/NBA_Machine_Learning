"""
The day's sample predictions, built once by a job and read by everyone.

Nothing on this site predicts on its own. A prediction costs real compute on one small server, so a
visitor arriving at the home page must never start one, and the home page still has to show what the
site can actually answer rather than describing it. This is how both hold at once: a job builds a
handful of real predictions once a day and writes them where the service reads them back, so every
reader of that day sees the same set and the page costs no forward pass at all.

What appears is chosen at random from the models whose answers are worth drawing, seeded from the day
itself, so the set is different every morning and identical for every reader of that morning. A model
answering yes or no is left out, because the home page is showing the shape of an answer and two bars
have no shape. See MINIMUM_OUTCOMES.

That seeding is the whole trick. A rerun on the same day picks the same models, games, players and
teams, so a job that is run twice, or run again after a failure, replaces the file with the same set
rather than reshuffling the page under whoever is reading it.

Every number in the set is a real model answering a real upcoming game. None of it is a
recommendation, and a sample carries no more weight than the same prediction asked for by hand.
"""

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
"""How many samples a build writes. The home page draws every one of them, so this is a design number."""

ROSTER_WINDOW = timedelta(days=365)
"""How far back a team's players are read from, matching what the service offers as a roster."""

MINIMUM_PAST_GAMES = 10
"""
How many earlier games a sample has to rest on before it is worth showing.

An answer built from three games is a real answer and the site says so wherever one is asked for by
hand. A sample nobody asked for is different: it is the site showing what it can do, so it should not
lead with its weakest work. A pick resting on less than this is dropped and another is drawn.
"""

MINIMUM_OUTCOMES = 8
"""
How many outcomes a model has to spread its answer over before it is drawn on the home page.

The home page shows an answer nobody asked for, and what it is really showing is the shape of one. A
model answering yes or no gives two bars, which is a true answer and a dull drawing, so those are
left out of the draw and are predicted only where a reader asks for one by hand. This counts
outcomes rather than naming the shapes, so a model answering in eight named categories is drawn and a
narrow number line is not.
"""

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
    """The game a sample answers, named the way a reader reads it rather than by stored id."""

    date: str
    home_team: NamedTeam
    away_team: NamedTeam
    season_type: str
    tipoff: str | None

@dataclass(frozen=True)
class Sample():
    """
    One real answer, carrying everything needed to draw it and nothing worked out from it.

    The expected value, the odds on a line and every phrase a reader reads are arithmetic the browser
    already holds, so none of it is written here. This is the same shape a prediction endpoint
    returns, plus the subject it was asked about, because a sample nobody requested has to say what
    it is of.
    """

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
    """The day the set was drawn for, which is what the seeding makes reproducible."""

    built_at: str
    samples: list[Sample]

def _rng(day: date) -> random.Random:
    """
    The day's own generator.

    Seeded on the ordinal rather than on the string, so the seed is a number that moves by exactly
    one each day and cannot depend on how a date happens to be written down.
    """

    return random.Random(day.toordinal())

def _worth_drawing(family: ModelFamily) -> list[ModelSpecification]:
    """Every model of a family that can answer and is worth drawing. See MINIMUM_OUTCOMES."""

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
    """
    Run one model, through the same inference the service runs.

    Nothing here is a second code path for predicting. A sample is the same answer a reader would get
    asking for it by hand, which is the only reason it is worth showing, and it is asked with the
    same expected lineups the site opens its roster controls on.
    """

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
    """
    One attempt at a sample. None where the pick could not be answered, so the caller draws again.

    A refusal here is ordinary rather than exceptional: a player the feature build holds almost
    nothing about, a game whose inputs moved between the schedule being read and the model being run.
    The job is a demonstration, so it steps over one of those and takes the next pick instead of
    failing the whole build.
    """

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
    """
    Draw the day's set.

    Picks are spread across every family that has something worth drawing, so a set shows the range
    of what the site answers rather than six versions of one model. Where there are fewer families
    than samples the families repeat, which is what a site with one trained family looks like and is
    not a failure. A family whose every model answers too narrowly to draw is not in the rotation at
    all. See MINIMUM_OUTCOMES.
    """

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

    # Families in a shuffled order, cycled, so the set covers what exists before it repeats anything.
    families = sorted({family.name for family, _ in choosable})
    chooser.shuffle(families)

    samples: list[Sample] = []
    attempts = 0

    # A cap rather than a loop until full: every pick runs a model, so a day where most picks refuse
    # must end with a short set rather than with the job running until something works.
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
    """
    Publish the set, whole.

    Written under a working name and moved into place, the same way a feature build is published, so
    a reader can never catch the file half written and a failed build leaves yesterday's set where
    the service can still read it.
    """

    showcase_file.parent.mkdir(parents=True, exist_ok=True)
    working = showcase_file.with_name(showcase_file.name + ".incomplete")
    working.write_text(json.dumps(asdict(showcase), indent=2, sort_keys=True), encoding="utf-8")
    os.replace(working, showcase_file)

    return showcase_file

def read(showcase_file: Path = paths.SHOWCASE_FILE) -> dict | None:
    """
    The published set, or None where there is nothing to read.

    None is normal rather than an error. A machine that has never run the job, a day before the first
    build, and a file written by a version this one does not understand all read as nothing, and the
    home page shows what it shows without samples instead of failing.
    """

    try:
        published = json.loads(showcase_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(published, dict) or published.get("format_version") != FORMAT_VERSION:
        return None
    if not isinstance(published.get("samples"), list):
        return None

    return published
