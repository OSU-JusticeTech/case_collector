# Data Structure Improver

This project aims to improve access to strctured data.
It supports different data sources as modules.

## Deployment

The easiest way to deploy is using docker compose with the images built by the CI.

To run it, copy the `docker-compose.yml` file and create a `django_env` file from the `django_env.sample` provided and replace the secrets with freshly generated ones.

If you have a nextgen account, edit the compose file environment to your email and password.
Otherwise, delete the nextgen section.

    docker compose up -d

will bring up the whole project and directly start scraping case data.

## Management

Sometimes, one-off tasks are required. These are best run in the ui container with

    docker compose exec ui uv run manage.py <command>

### fcmcclerk_reparse

This discards all parsed snapshots and regenerates them from the raw saved pages.


## Backup & Restore

To back up the database, run

    docker compose exec -T db pg_dump eviction -U postgres > backup/database.sql
