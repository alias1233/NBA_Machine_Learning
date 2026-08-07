# NBA Machine Learning Framework

Predicts NBA statistics using machine learning.

## Current

Implemented capabilities:

- Automated data collection and saving of NBA data to a database
- Schedule collection, and working out which upcoming games have every model input already collected
- Feature engineering helpers and data processing
- Training and inferencing on models
- FastAPI endpoints for server to server communication
- A website that predicts on an upcoming game, or on a game typed out by hand

Working models:

- Player game statistics: predicts the probability distribution of one statistic for a player in a
  future game. Points, rebounds, assists, and points plus rebounds plus assists.

## Future

Have models accessible through a website where users can predict future statistics.

## Layout

```
python/ : the machine learning pipeline: collection, feature engineering, training, inference
web/    : the website, SvelteKit.
```