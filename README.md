# Data Structure Improver

This project aims to improve access to strctured data.
It supports different data sources as modules.

## Deployment

The easiest way to deploy is using docker compose with the images built by the CI.

To run it, copy the `docker-compose.yml` file and create a `django_env` file from the `django_env.sample` provided and replace the secrets with freshly generated ones.

Create a `.env` file that contains the `DOMAIN` variable and set it to the public domain name. 

If you have a nextgen account, edit the compose file environment to your email and password.
Otherwise, delete the nextgen section.

    docker compose up -d

will bring up the whole project and directly start scraping case data.

## Management

Sometimes, one-off tasks are required. These are best run in the ui container with

    docker compose exec ui uv run manage.py <command>

### fcmcclerk_reparse

This discards all parsed snapshots and regenerates them from the raw saved pages.


### export_cases
    
Exports the latest case snapshot for each case where the case number contains the second argument.

    export_cases FCMC "2026 CVG" > cases_2026.json

## Backup & Restore

To back up the database, run

    docker compose exec -T db pg_dump eviction -U postgres > backup/database.sql


## Deployment on `as-cura-server.asc.ohio-state.edu`

This is a quite old red hat virtual machine run by OSU OTDI

```console
$ lsb_release

Distributor ID: RedHatEnterprise
Description:    Red Hat Enterprise Linux release 8.10 (Ootpa)
Release:        8.10
Codename:       Ootpa

$ uname -a
Linux as-cura-server.asc.ohio-state.edu 4.18.0-553.129.1.el8_10.x86_64 #1 SMP Tue Jun 2 12:11:39 EDT 2026 x86_64 x86_64 x86_64 GNU/Linux
```

### Firewall

First we need to ensure that the firewall is allowing web traffic.

```console
$ sudo firewall-cmd --zone=public --permanent --add-port=80/tcp
$ sudo firewall-cmd --zone=public --permanent --add-port=443/tcp
$ sudo firewall-cmd --reload
```

The ports should then be listed:

```console
$ sudo firewall-cmd --list-all
public (active)
  target: default
  icmp-block-inversion: no
  interfaces: ens33
  sources: 
  services: ssh
  ports: 80/tcp 443/tcp  # these ports are important
  protocols: 
  forward: no
  masquerade: no
  forward-ports: 
  source-ports: 
  icmp-blocks: 
  rich rules: 
        rule family="ipv4" service name="ssh" accept
```

### Reverse Proxy

Create a folder for the reverse proxy:

```console
# mkdir -p /opt/cura/traefik
# cd /opt/cura/traefik
```

Create a docker network in which all containers that expose web endpoints have an interface:

```console
# docker network create web
```

Create a compose stack file at `/opt/cura/traefik/docker-compose.yml`

```yaml
services:
  proxy:
    image: traefik:v3
    networks:
      web:
    ports:
      - "80:80"
      - "443:443"
    restart: always
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "./traefik.toml:/etc/traefik/traefik.toml"
      - "acme:/acme/"

volumes:
  acme:

networks:
  web:
    external: true
```

Create a basic config at `/opt/cura/traefik/traefik.toml`

```toml
[global]
  checkNewVersion = false
  sendAnonymousUsage = false

[entryPoints]
  [entryPoints.web]
    address = ":80"
    [entryPoints.web.http.redirections.entryPoint]
      to = "websecure"
      scheme = "https"

  [entryPoints.websecure]
    address = ":443"
    asDefault = true

[api]
  insecure = false

[certificatesResolvers.le.acme]
  email = "cura@osu.edu" # this email is used for certificate purposes
  storage = "/acme/acme.json"
  
  [certificatesResolvers.le.acme.httpChallenge]
    entryPoint = "web"

[providers.docker]
  network = "web"
  exposedByDefault = false
```

Run it and check if it works. Inside the folder `/opt/cura/traefik` run

```console
docker compose up -d
```

Then when visiting the URL https://as-cura-server.asc.ohio-state.edu/ the browser should complain about a *not-secure* issue
This warning is to be expected and everything is working.
If the browser instead complains about *Unable to connect* the above did not work.

Troubleshoot the error with
```
docker compose logs
```
which may provide more insight into what failed.

### Case Scraper

Create a new folder

```console
mkdir -p /opt/cura/case_scraper
cd /opt/cura/case_scraper
```

Then download the docker compose file from this repository

```console
curl -O https://raw.githubusercontent.com/OSU-JusticeTech/case_collector/refs/heads/main/docker-compose.yml
```

To correctly run in this environment, it requires a few additional variables provided through environment files.

Create tie file `/opt/cura/case_scraper/.env` with content

```text
DOMAIN=as-cura-server.asc.ohio-state.edu
```
to specify the publicly available URL

Then create the `django_env` file with

```text
DJANGO_SECRET: "django-insecure-ydtr_#%%p3g188$cptutqw9s7f5b-rjmvgi^l@o^s(*&ob53fh-replaceme"
DB_NAME: "eviction"
DB_PASS: "<DB-PW>"
DB_HOST: "db"
NEXTGEN_PASSWORD: "nextgen-password"
NEXTGEN_EMAIL: "nextgen-email@example.com"
```

replace the `django-insecure-ydtr_...` and `<DB-PW>` with two freshly generated randomnesses, got from: 

```console
$ openssl rand -hex 40
```

Also set the nextgen password and email to scrape the PDFs.

Create a `/opt/cura/case_scraper/mcp_env` file with the content of the public read only database user `read_user`:

```text
DB_DSN="postgresql://read_user:<PASSWORD HERE>@db:5432/eviction?sslmode=require"
```

Create a `/opt/cura/case_scraper/db_env` with the following content:

```text
POSTGRES_PASSWORD: <DB-PW>
POSTGRES_DB: eviction
POSTGRES_USER: postgres
```

where DB-PW is the *same* as the `DB_PASS` variable in the `django_env` file.

With these 4 files (`.env`, `django_env`, `db_env`, `mcp_env`) in place, check that docker is happy with the setup:

```console
$ docker compose ps
```

### Storage

The VM itself only has around 60GB of storage, we have to move the data heavy files to the NFS mounted 1TB storage

```console
$ df -h
Filesystem                                                                     Size  Used Avail Use% Mounted on
/dev/mapper/rhel_as--cura--server_1-root                                        30G  6.6G   23G  23% /
/dev/mapper/rhel_as--cura--server_1-var                                         43G  4.3G   38G  11% /var
asc-nfs-data.asc.ohio-state.edu:/ifs/asc-nfs-data/b/projects/geo-cura-project  1.0T     0  1.0T   0% /var/geo-cura-project
```

First, create new folders for the volumes:

```console
# mkdir -p /var/geo-cura-project/volumes/db
# mkdir -p /var/geo-cura-project/volumes/pdfs
```

Then create a `docker-compose.override.yml` file to change where the data is stored:

```yaml
volumes:
  db:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /var/geo-cura-project/volumes/db

  pdfs:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /var/geo-cura-project/volumes/pdfs
```

### Migration

It is time to start up the database alone:

```console
$ docker compose up -d db
```

Verify the database started correctly.

```console
$ docker compose logs
```
should output `UTC [1] LOG:  database system is ready to accept connections` twice, once before and once after ` FATAL:  database "eviction" does not exist
db-1  | CREATE DATABASE`

Copy a `-Fc` formatted database dump to the vm. This works with rsync through the jumphost once a folder with the correct permissions is created:

```console
# mkdir /var/geo-cura-project/tmp
# chmod 757 /var/geo-cura-project/tmp
```

Then from the source server copy with
```console
rsync -avz -e "ssh -J <normal-osu>@jump.asc.ohio-state.edu" backup.dump  <admin-user>@as-cura-server.asc.ohio-state.edu:/var/geo-cura-project/tmp/
```

Then import the database backup to an empty database (the ui container must not have started before): 

```console
docker compose exec -T db pg_restore -U postgres -d eviction < /var/geo-cura-project/tmp/backup.dump
```

This copy process takes many minutes. You can check the progress by looking at the size of the db volume

```console
$ du -hcs /var/geo-cura-project/volumes/db/
3.5G    /var/geo-cura-project/volumes/db/
3.5G    total
```
It should approach twice the size of your backup file.

The restore may throw errors about `read_user` not existing like:

```text
pg_restore: error: could not execute query: ERROR:  role "read_user" does not exist
Command was: GRANT USAGE ON SCHEMA public TO read_user;
```

Which will be fixed later.

If the import fails more severely, you can start from scratch with (`-v` deletes all volumes, but the bind mounted ones are not cleaned up):
Beware not to run this command later as it would delete all scraped PDFs.
```console
$ docker compose down -v
$ rm -rf /var/geo-cura-project/volumes/db
```

Before continuing, assure that the data is present by inspecting the database:

```console
$ docker compose exec -u postgres db psql
```

Then inside the psql command, list all databases, connect to eviction and see how many cases are present:

```console
postgres=# \l
                                                        List of databases
       Name       |  Owner   | Encoding | Locale Provider |  Collate   |   Ctype    | Locale | ICU Rules |   Access privileges   
------------------+----------+----------+-----------------+------------+------------+--------+-----------+-----------------------
 eviction         | postgres | UTF8     | libc            | en_US.utf8 | en_US.utf8 |        |           | 
 postgres         | postgres | UTF8     | libc            | en_US.utf8 | en_US.utf8 |        |           | 
 template0        | postgres | UTF8     | libc            | en_US.utf8 | en_US.utf8 |        |           | =c/postgres          +
                  |          |          |                 |            |            |        |           | postgres=CTc/postgres
 template1        | postgres | UTF8     | libc            | en_US.utf8 | en_US.utf8 |        |           | =c/postgres          +
                  |          |          |                 |            |            |        |           | postgres=CTc/postgres
 template_postgis | postgres | UTF8     | libc            | en_US.utf8 | en_US.utf8 |        |           | 
(5 rows)

postgres=# \c eviction
You are now connected to database "eviction" as user "postgres".

eviction=# select count(*) from cases_courtcase;
 count 
-------
 98026
(1 row)
```

Note, the `latest_overview` is a materialized view that has not yet been materialized in the new database, so does not show up.

Now, you can start the ui with

```console
$ docker compose up -d ui
```

If everything worked, you are able to log in at https://as-cura-server.asc.ohio-state.edu/admin/

If you forgot the `root` password, you can change it with
```console
$ docker compose exec ui uv run manage.py changepassword root
```
