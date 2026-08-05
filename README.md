# NBA Machine Learning Framework

Predicts NBA statistics using machine learning.

## Current

Implemented Capabilities:
- Automated data collection and saving of NBA data to a database 
- Feature engineering helpers and data processing
- Training and inferencing on models
- FastAPI endpoints complete for the server to server communication

Currently working models:
- Player statistics: Predicts the probability distribution of a specified statistic for a player
in a future game. Currently supports points, rebounds, assists, and points + rebounds + assists.

## Future

Have models accessible through a website where users can predict future statistics.

## Layout

```
python/ : the machine learning pipeline: collection, feature engineering, training, inference
```

Inside `python/`, the code is one installable package, `src/nba_ml/`, laid out by pipeline stage:

```
nba_ml/sources/                  where data comes from. One module per service, all behind one interface.
nba_ml/stores/                   where it is held. One module per table, owning its writes and queries.
nba_ml/data_collection/          fills the stores from a source. No prompts, so a scheduled job can run it.
nba_ml/feature_engineering/      turns raw box scores into model inputs
nba_ml/machine_learning/         the training loop, evaluation, and model architectures. No NBA in it.
nba_ml/models/                   one folder per model family. player_props/ holds the four stat models.
nba_ml/cli/                      the commands
nba_ml/paths.py                  where data and models live
nba_ml/season.py                 season phases, season years, and how a game date is written
nba_ml/database.py               the database layer
```

## Running

`python/` holds its own `pyproject.toml` and lock file. `uv sync` installs the package, which puts
three commands on the path. They work from any directory.

```
uv sync
uv run nba-collect all                                # fetches everything newer than what is stored
uv run nba-train -stat points                         # trains one model and writes a report next to it
uv run nba-predict -stat points -player "Luka Doncic" \
    -team lakers -opponent spurs -date 2026-06-30 -line 25.5
```

`nba-collect` takes arguments and never prompts, so the same command works by hand and on a
schedule. `nba-collect --help` lists them. The ones worth knowing:

```
nba-collect all                                       # every new game, then every new player
nba-collect player-games --since 2026-01-01           # only games played on or after a date
nba-collect team-games --seasons 2024 2025            # whole seasons, named by the year they start
nba-collect players --all --start-index 2000          # every player, picking a stopped run back up
nba-collect --source nba_api --wait 1.5 all           # choose the service and how hard to push it
```

Everything generated is stored in `python/data/`, which is not in the repository:

```
data/databases/                              the collected SQLite files
data/models/player_prop/<stat>/              model.pth, training_report.txt, graphs/
data/training_cache/player_prop/<stat>/      the preprocessed training build, disposable
```

Set `NBA_ML_DATA_DIR` to put that tree somewhere else.

# TODO:

- Make frontend + backend connected to the python machine learning pipeline
- Migrate to PostgreSQL
- Switch NBA data providers
- Set up daily automated jobs for updating NBA data
- Docker