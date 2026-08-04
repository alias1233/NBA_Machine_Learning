# NBA Machine Learning Framework

Predicts how an NBA player will do in an upcoming game. A prediction is not a single number. It is a
probability for every whole-number outcome, so for points the model gives the chance of exactly 0,
exactly 1, and so on. Over and under odds for any line are the sum of the probabilities above it.

Four stats are modelled: points, rebounds, assists, and the three added together.

Today this is local research code. The plan is to turn it into a public website. See
`docs/ARCHITECTURE.md` for that design and `docs/STATUS.md` for where things actually stand.

## Layout

```
python/   the machine learning pipeline: collection, feature engineering, training, inference
docs/     architecture, status, open work
```

`web/` and `deploy/` are planned and do not exist yet.

## Running it

Everything runs from inside `python/`, which holds its own `pyproject.toml` and lock file. Imports
are rooted at `src`.

```
uv sync
uv run collect_data.py          # interactive, fetches NBA data into local SQLite files
uv run train.py -stat points    # trains one model and writes a report next to it
```

Trained models land in `python/trained_models/player_prop/<stat>/`. Inference lives in
`model_manager.predict()` and has no command-line entry point yet.

## Documents

- `docs/STATUS.md` is where the project stands, what works, and what is broken.
- `docs/TODO.md` is the ordered list of open work.
- `docs/ARCHITECTURE.md` is the target design for the website.
- `docs/IMPLEMENTED.md` is an index of shipped features and the commits that landed them.
- `docs/NOTEPAD.md` is the working log of experiments and their numbers.
- `AGENTS.md` is the operating manual for agents working in this repository.
