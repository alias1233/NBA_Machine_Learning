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

One rented Linux server. Before starting, it needs:

- **Docker Engine and the Compose v2 plugin.** Everything below is `docker compose`.
- **DNS.** An `A` record for the domain and one for `www.` in front of it, both pointing at this
  server. Caddy asks for a certificate for each, and it will retry a name that does not resolve for
  as long as it runs.
- **Ports 80 and 443 open**, at the provider's firewall as well as the host's. Port 443 on UDP too,
  which is HTTP/3.
- **Room for the jobs container.** The long-running services are capped at 2 GB, 512 MB and 256 MB,
  and the hourly collection adds a container capped at 4 GB on top of them. A box that fits only the
  services deploys cleanly and is killed the first time cron runs. 8 GB leaves room.

On the server, clone the repository:

```sh
git clone <repository> /srv/bazaarball
```

On the developer machine, after collection and training, create the first-start snapshot and copy it
to the server. Replace `<server>` with its SSH host:

```sh
cd <local-repository>/python
uv run nba-serving-data pack ../nba-serving-data.tar.gz
scp ../nba-serving-data.tar.gz <server>:/srv/bazaarball/
```

`nba-serving-data.tar.gz` contains the trained models and the five-year game-data window the server
needs. The load command mounts it read-only as `/release.tar.gz` and verifies it into the empty `data/`
directory.

Back on the server:

```sh
cd /srv/bazaarball/deploy
cp .env.example .env && nano .env            # DOMAIN, ACME_EMAIL, and BALL_DONT_LIE_KEY
mkdir -p data backups logs && sudo chown -R 10001:10001 data backups
docker compose build jobs
docker compose run --rm -v /srv/bazaarball/nba-serving-data.tar.gz:/release.tar.gz:ro jobs nba-serving-data load /release.tar.gz
docker compose run --rm jobs nba-collect --source balldontlie schedule
docker compose run --rm jobs nba-build-features --quiet
docker compose run --rm jobs                    # refresh rosters and rebuild features
docker compose run --rm jobs nba-showcase       # publish the home-page samples
docker compose up -d --build                    # caddy, web, api
sudo install -m 0644 logrotate /etc/logrotate.d/bazaarball
sudo install -m 0644 crontab /etc/cron.d/bazaarball
```

# During Deployment

Run these commands from `/srv/bazaarball/deploy`.

## Check the server

```sh
docker compose ps
docker compose logs --tail=100 caddy web api
docker compose logs -f api                  # Ctrl-C leaves the service running
tail -n 100 logs/nba-ml.log                  # scheduled collection, build, and backup jobs
tail -n 100 logs/access.log                  # requests, as Caddy saw them
curl -fsS https://<domain>/health
df -h
```

`api` should be healthy. The Docker logs cover the three long-running services. The cron log records
the short-lived scheduled jobs, including a line for any run that stood down because another job
still held the lock.

## Update the site

```sh
git pull --ff-only
sudo install -m 0644 crontab /etc/cron.d/bazaarball
sudo install -m 0644 logrotate /etc/logrotate.d/bazaarball
docker compose up -d --build
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
docker compose ps
curl -fsS https://<domain>/health
```

Every update installs the current host jobs and log rotation rule, and Caddy reloads its mounted
configuration. Do not run `docker compose down -v` as part of a normal update, because it removes the
saved Caddy certificates.

## Delete the deployment

Copy any archive you need off the server first. This removes the containers, certificates, data,
backups and source tree:

```sh
cd /srv/bazaarball/deploy
docker compose down --volumes --remove-orphans
docker image rm nba-ml-web:latest nba-ml-python:latest
sudo rm -f /etc/cron.d/bazaarball /etc/logrotate.d/bazaarball
cd /srv
sudo rm -rf -- /srv/bazaarball
```

If an older deployment used `crontab crontab`, remove only its `NBA_ML` line and four NBA job lines
with `crontab -e`. If `.env` points data or backups outside `/srv/bazaarball`, remove those verified
directories separately.

## Back up the server

Cron creates a nightly archive in `backups/` and keeps the newest seven. Run one manually or check it
with:

```sh
docker compose run --rm jobs nba-backup
ls -lh backups/
tar -tzf backups/nba-ml-<timestamp>.tar.gz >/dev/null
```

Copy each archive to storage outside this server. A backup on the same machine does not protect against
losing the machine:

```sh
rsync -av backups/ <backup-host>:<backup-path>/
```

The archives hold the databases and trained models. Keep the deployment `.env` in a separate secure
secret store.

## Updating and adding models

Train models on the development machine only. The server has the processor-only runtime and must
only receive the finished weights and their held-out evaluation. Do not use `--skip-evaluations`.

To replace a model without changing its code or inputs, train and check it locally:

```sh
cd <local-repository>/python
uv run pytest
uv run nba-train --model <model> --no-cache
```

First create a temporary staging directory on the server, then copy those two files into it. This does
not touch the running model:

```sh
ssh <server> 'mkdir -p /tmp/bazaarball-<model>'
scp data/models/<family>/<model>/model.pth \
    data/models/<family>/<model>/evaluation.json \
    <server>:/tmp/bazaarball-<model>/
```

On the server, take a backup, copy the files into the container-owned data directory, and replace the
weights last. The final moves are atomic, so the API sees either the old complete model or the new one,
never a partial upload:

```sh
cd /srv/bazaarball/deploy
docker compose run --rm jobs nba-backup
docker compose run --rm -v /tmp/bazaarball-<model>:/release:ro jobs sh -eu -c '
  target=/data/models/<family>/<model>
  mkdir -p "$target"
  cp /release/evaluation.json "$target/evaluation.json.new"
  cp /release/model.pth "$target/model.pth.new"
  mv "$target/evaluation.json.new" "$target/evaluation.json"
  mv "$target/model.pth.new" "$target/model.pth"
'
docker compose exec api python -c "from nba_ml.models import families, loading, metrics; found = families.find_model('<model>'); assert found and loading.can_load(found[1]) and metrics.read(found[1].evaluation_file()); print(f'Published {found[1].name}.')"
rm -f /tmp/bazaarball-<model>/model.pth /tmp/bazaarball-<model>/evaluation.json
rmdir /tmp/bazaarball-<model>
```

The API checks the model file each request, so this needs no restart. The verification uses the same
compatibility check as a prediction, including the output shape and feature columns.

When adding a model or changing its code, output, or feature columns, train it from the same commit,
then run **Update the site** on the server before publishing its files. If its inputs changed, rebuild
the server's shared features before the publish command:

```sh
docker compose run --rm jobs nba-build-features --quiet
```

Until the matching model and feature build are both present, the API marks that model unpublished
instead of serving it with the wrong inputs. A new model also needs its specification and website
catalogue in the deployed commit before it can appear on the site.
