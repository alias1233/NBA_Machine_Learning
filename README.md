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

- Player game statistics: predicts what a player does in a future game. Points, rebounds, assists,
  three pointers, steals, blocks and turnovers, the pairs and the trio of them added together, and
  whether they record a double double or a triple double.

## Future

Have models accessible through a website where users can predict future statistics.

## Layout

```
python/ : the machine learning pipeline: collection, feature engineering, training, inference
web/    : the website, SvelteKit.
deploy/ : the Docker Compose stack, the Caddyfile, and the cron entries.
```

# Deployment

One rented Linux server.

```sh
git clone <repository> /srv/nba-ml && cd /srv/nba-ml/deploy
cp .env.example .env && nano .env            # DOMAIN and ACME_EMAIL
mkdir -p data/models backups && sudo chown -R 10001:10001 data backups
docker compose up -d --build                 # caddy, web, api
docker compose run --rm jobs                 # collect, then build the features
crontab crontab                              # hourly collect and build, nightly backup
```

Models are trained on the developer machine and published by copying them in:

```sh
scp -r python/data/models/* <server>:/srv/nba-ml/deploy/data/models/
```

Updating is `git pull && docker compose up -d --build`. Both are picked up without a restart: a new
feature build and a republished model file.