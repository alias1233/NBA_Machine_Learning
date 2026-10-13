# Deployment

The whole site runs on one Linux server. Requirements:

- Docker Engine 25.0+ and Docker Compose v2.24+. Older versions don't support the `start_interval`
  and `required: false` options used in `docker-compose.yml`.
- DNS `A` records for the domain and for `www.<domain>`, both pointing to the server. Caddy needs
  both to get its certificates.
- Ports 80 and 443 open in the host firewall and in the hosting provider's firewall. Open 443 on UDP
  as well for HTTP/3.
- 8 GB of RAM is recommended. The three services are limited to about 3 GB in total, and the hourly
  job can use up to 4 GB more while it runs.

Clone the repository on the server:

```sh
git clone <repository> /srv/<name>
```

On your local machine, after collecting the data and training the models, pack the data the server
needs and copy it over. `<server>` is the server's SSH host:

```sh
cd <local-repository>/python
uv run nba-serving-data pack ../nba-serving-data.tar.gz
scp ../nba-serving-data.tar.gz <server>:/srv/<name>/
```

`nba-serving-data.tar.gz` contains the trained models and the last five years of game data. It gets
loaded into the empty `data/` directory in the next step.

Then on the server:

```sh
cd /srv/<name>/deploy
cp .env.example .env && nano .env            # set DOMAIN, ACME_EMAIL, and BALL_DONT_LIE_KEY
mkdir -p data backups logs && sudo chown -R 10001:10001 data backups
docker compose build jobs
docker compose run --rm -v /srv/<name>/nba-serving-data.tar.gz:/release.tar.gz:ro jobs nba-serving-data load /release.tar.gz
docker compose run --rm jobs nba-collect --source balldontlie schedule
docker compose run --rm jobs nba-build-features --quiet
docker compose run --rm jobs                    # refresh rosters and rebuild features
docker compose run --rm jobs nba-showcase       # build the home page samples
docker compose up -d --build                    # start caddy, web, and api
sudo install -m 0644 logrotate /etc/logrotate.d/<name>
sudo install -m 0644 crontab /etc/cron.d/<name>
```

# During Deployment

Run these commands from `/srv/<name>/deploy`.

## Check the server

```sh
docker compose ps
docker compose logs --tail=100 caddy web api
docker compose logs -f api                  # Ctrl-C stops following, the service keeps running
tail -n 100 logs/nba-ml.log                  # cron job output
tail -n 100 logs/access.log                  # Caddy access log
curl -fsS https://<domain>/health
df -h
```

`api` and `web` should both show as healthy. `docker compose logs` covers the three running
services, and `logs/nba-ml.log` has the output of the cron jobs. If a job gets skipped because
another one is still running, that is logged there too.

## Update the site

```sh
git pull --ff-only
sudo install -m 0644 crontab /etc/cron.d/<name>
sudo install -m 0644 logrotate /etc/logrotate.d/<name>
docker compose up -d --build
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
docker compose ps
curl -fsS https://<domain>/health
```

This also reinstalls the cron and logrotate files in case they changed, and reloads the Caddy
config. Don't use `docker compose down -v` for a normal update, because it deletes the saved Caddy
certificates.

## Delete the deployment

This deletes the containers, certificates, data, backups, and the repository itself. Copy any
backups you want to keep off the server first.

```sh
cd /srv/<name>/deploy
docker compose down --volumes --remove-orphans
docker image rm nba-ml-web:latest nba-ml-python:latest
sudo rm -f /etc/cron.d/<name> /etc/logrotate.d/<name>
cd /srv
sudo rm -rf -- /srv/<name>
```

If an older deployment installed the jobs with `crontab crontab`, remove the `NBA_ML` line and the
four job lines with `crontab -e`. If `.env` points the data or backup directory somewhere outside
`/srv/<name>`, delete those directories separately.

## Back up the server

A cron job creates a backup in `backups/` every night and keeps the seven most recent. To run one
manually and check that the archive is readable:

```sh
docker compose run --rm jobs nba-backup
ls -lh backups/
tar -tzf backups/nba-ml-<timestamp>.tar.gz >/dev/null
```

Copy the backups to another machine too, so they survive if the server is lost:

```sh
rsync -av backups/ <backup-host>:<backup-path>/
```

The backups contain the databases and the trained models. `.env` is not included, so keep a copy of
it somewhere safe.

## Updating and adding models

Models are trained on your local machine, never on the server. The server only has the CPU build of
PyTorch, so it just gets the trained weights and the evaluation file. Don't train with
`--skip-evaluations`, since the server needs the evaluation file.

To retrain a model without changing its code or its features, train and test it locally:

```sh
cd <local-repository>/python
uv run pytest
uv run nba-train --model <model> --no-cache
```

Copy the two files to a temporary directory on the server. This doesn't affect the live model yet:

```sh
ssh <server> 'mkdir -p /tmp/<name>-<model>'
scp data/models/<family>/<model>/model.pth \
    data/models/<family>/<model>/evaluation.json \
    <server>:/tmp/<name>-<model>/
```

On the server, make a backup, then copy the files into the data directory. Each file is copied under
a temporary name and then renamed, with the weights renamed last, so the API never reads a partly
copied model:

```sh
cd /srv/<name>/deploy
docker compose run --rm jobs nba-backup
docker compose run --rm -v /tmp/<name>-<model>:/release:ro jobs sh -eu -c '
  target=/data/models/<family>/<model>
  mkdir -p "$target"
  cp /release/evaluation.json "$target/evaluation.json.new"
  cp /release/model.pth "$target/model.pth.new"
  mv "$target/evaluation.json.new" "$target/evaluation.json"
  mv "$target/model.pth.new" "$target/model.pth"
'
docker compose exec api python -c "from nba_ml.models import families, loading, metrics; found = families.find_model('<model>'); assert found and loading.can_load(found[1]) and metrics.read(found[1].evaluation_file()); print(f'Published {found[1].name}.')"
rm -f /tmp/<name>-<model>/model.pth /tmp/<name>-<model>/evaluation.json
rmdir /tmp/<name>-<model>
```

No restart is needed, because the API checks the model file on every request. The `python -c`
command runs the same checks the API runs before a prediction, including the output shape and the
feature columns.

If you are adding a new model, or changing a model's code, output, or feature columns, train it on
the same commit that will be deployed. Then follow **Update the site** on the server before copying
the model files over. If the feature columns changed, rebuild the features on the server first:

```sh
docker compose run --rm jobs nba-build-features --quiet
```

The API marks a model as unpublished until both the model files and a matching feature build are on
the server. A new model also has to be added to the model specifications and to the website code in
the deployed commit before it shows up on the site.
