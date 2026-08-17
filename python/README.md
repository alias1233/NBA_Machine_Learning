# Machine Learning Pipeline

Handles the data collection and machine learning pipelines.

## Layout

Inside `python/`, the code is one installable package, `src/nba_ml/`, laid out by pipeline stage:

```
nba_ml/sources/                  where data comes from. One module per service, all behind one interface.
nba_ml/stores/                   where it is held. One module per table, owning its writes and queries.
nba_ml/data_collection/          fills the stores from a source. No prompts, so a scheduled job can run it.
nba_ml/feature_engineering/      turns raw box scores into model inputs
nba_ml/machine_learning/         the training loop, evaluation, and model architectures. No NBA in it.
nba_ml/models/                   one folder per model family, what they share, and families.py
nba_ml/api/                      the FastAPI service. One router per family, over shared endpoints.
nba_ml/cli/                      the commands
nba_ml/paths.py                  where data and models live
nba_ml/season.py                 season phases, season years, and how a game date is written
nba_ml/upcoming.py               which scheduled games can be predicted right now
nba_ml/database.py               the database layer
```

## Running

`python/` holds its own `pyproject.toml` and lock file. `uv sync` installs the package, which puts
six commands on the path. They work from any directory.

```
uv sync
uv run nba-collect all                                # fetches everything newer than what is stored
uv run nba-build-features                             # builds the whole league's features and publishes them
uv run nba-schedule list                              # the upcoming games, and whether each is answerable
uv run nba-train --model points                       # trains one model and writes a report next to it
uv run nba-backup                                     # archives the databases and the trained models
uv run nba-predict --model points --player "Luka Doncic" \
    --home LAL --away SAS --date 2026-06-30
```

Every command takes arguments and never prompts, so the same command works by hand and on a
schedule. `--help` lists them all. The ones worth knowing:

```
nba-collect all                                       # every new game and player, then the schedule
nba-collect player-games --since 2026-01-01           # only games played on or after a date
nba-collect team-games --seasons 2024 2025            # whole seasons, named by the year they start
nba-collect players --all --start-index 2000          # every player, picking a stopped run back up
nba-collect schedule                                  # this season's games and next season's, played or not
nba-collect --source nba_api --wait 1.5 all           # choose the service and how hard to push it

nba-build-features --window-years 5                   # how far back to build, defaulting to what a prediction reads
nba-build-features --everything-stored                # build every game held, which needs a developer machine

nba-schedule list --days 14                           # what is coming, and what each game is still waiting on
nba-schedule add-mock --home LAL --away LAC \
    --date 2026-08-08                                 # a made up game, for testing out of season
nba-schedule clear-mock                               # remove every mock game, leaving the real ones

nba-backup --keep 7                                   # how many archives to leave on disk

nba-train --model rebounds --rebuild-cache            # engineer the features again instead of reusing them
nba-predict --model points --player "Luka Doncic" \
    --home LAL --away SAS --date 2026-06-30 \
    --without "Anthony Davis"                         # predict without a core teammate
```

Everything generated is stored in `python/data/`, which is not in the repository:

```
data/databases/                              the collected SQLite files
data/feature_builds/<family>/<version>/      the published whole-league features the service reads
data/models/<family>/<model>/                model.pth, training_report.txt, evaluation.json, graphs/
data/training_cache/<family>/<model>/        the preprocessed training build, disposable
data/backups/                                dated archives of the databases and the model files
```

Set `NBA_ML_DATA_DIR` to put that tree somewhere else, and `NBA_ML_BACKUP_DIR` for the archives.