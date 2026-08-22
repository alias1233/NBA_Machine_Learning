# NBA Machine Learning Framework

Predicts NBA statistics using machine learning.

## Current

Implemented capabilities:

- Automated data collection and saving of NBA data to a database
- Schedule collection, and working out which upcoming games have every model input already collected
- Feature engineering helpers and data processing
- Training and inferencing on models
- FastAPI endpoints for server to server communication
- A website that predicts on an upcoming game

All twenty four models are trained and have a held-out evaluation:

- Player Stat Models: predicts what a player does in a future game. Points, rebounds, assists,
  three pointers, steals, blocks and turnovers, the pairs and the trio of them added together, and
  whether they record a double double or a triple double.
- Team Stat Models: predicts a team's points, rebounds, assists or three-pointers.
- Game Stat Models: predicts the home team's margin or win chance, and game totals for points,
  rebounds, assists or three-pointers.

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
mkdir -p data backups logs && sudo chown -R 10001:10001 data backups
sudo cp logrotate /etc/logrotate.d/nba-ml
docker compose build jobs
docker compose run --rm -v /srv/nba-ml/nba-serving-data.tar.gz:/release.tar.gz:ro jobs nba-serving-data load /release.tar.gz
docker compose run --rm jobs nba-build-features --quiet
docker compose run --rm jobs                    # refresh rosters and rebuild features
docker compose run --rm jobs nba-showcase       # publish the home-page samples
docker compose up -d --build                 # caddy, web, api
crontab crontab                              # hourly collect and build, nightly backup
```

Create `nba-serving-data.tar.gz` on the developer machine after training and collection:

```sh
cd python && uv run nba-serving-data pack ../nba-serving-data.tar.gz
scp nba-serving-data.tar.gz <server>:/srv/nba-ml/
```

Updating is `git pull && docker compose up -d --build`. Both are picked up without a restart: a new
feature build and a republished model file.
