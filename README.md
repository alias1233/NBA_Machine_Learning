# NBA Machine Learning Framework

Predicts NBA statistics using machine learning.

## Current

Implemented capabilities:

- Automated data collection and saving of NBA data to a database
- Schedule collection to find upcoming games that are ready to be predicted
- Feature engineering helpers and data processing
- Training and inferencing on models
- FastAPI endpoints for server to server communication
- A website that predicts on an upcoming game

All 24 models are trained and evaluated on held-out data:

- Player Stat Models: predicts a player's points, rebounds, assists, three-pointers, steals, blocks
  or turnovers, combinations such as points + rebounds + assists, and whether they record a
  double-double or triple-double.
- Team Stat Models: predicts a team's points, rebounds, assists or three-pointers.
- Game Stat Models: predicts the home team's margin or win chance, and game totals for points,
  rebounds, assists or three-pointers.

## Layout

```
python/ : the machine learning pipeline: collection, feature engineering, training, inference
web/    : the website, SvelteKit.
deploy/ : the Docker Compose stack, the Caddyfile, and the cron entries.
```
