# Data Structure Improver

This project aims to improve access to structured data.
It supports different data sources as modules.

## Prerequisites

* Docker Engine and the Docker Compose plugin (`docker compose version`)
* A DNS record for your chosen `DOMAIN` pointing at the host, already resolving before you bring up the reverse proxy (required for Let's Encrypt/ACME to succeed)

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

To back up the database in custom format (required for `pg_restore`), run

    docker compose exec -T db pg_dump -Fc eviction -U postgres > backup/database.dump

To restore that dump into an empty database, run

    docker compose exec -T db pg_restore -U postgres -d eviction < backup/database.dump


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

Create the file `/opt/cura/case_scraper/.env` with content

```text
DOMAIN=as-cura-server.asc.ohio-state.edu
```
to specify the publicly available URL

Then create the `django_env` file with

```text
DJANGO_SECRET=django-insecure-ydtr_#%%p3g188$cptutqw9s7f5b-rjmvgi^l@o^s(*&ob53fh-replaceme
DB_NAME=eviction
DB_PASS=<DB-PW>
DB_HOST=db
NEXTGEN_PASSWORD=nextgen-password
NEXTGEN_EMAIL=nextgen-email@example.com
```

replace the `django-insecure-ydtr_...` and `<DB-PW>` with two freshly generated randomnesses, got from: 

```console
$ openssl rand -hex 40
```

Also set the nextgen password and email to scrape the PDFs.

Create a `/opt/cura/case_scraper/mcp_env` file with the content of the public read only database user `read_user`:

```text
DB_DSN=postgresql://read_user:<PASSWORD HERE>@db:5432/eviction?sslmode=require
```

Create a `/opt/cura/case_scraper/db_env` with the following content:

```text
POSTGRES_PASSWORD=<DB-PW>
POSTGRES_DB=eviction
POSTGRES_USER=postgres
```

where DB-PW is the *same* as the `DB_PASS` variable in the `django_env` file.

With these 4 files (`.env`, `django_env`, `db_env`, `mcp_env`) in place, check that docker is happy with the setup:

```console
$ docker compose ps
```

| File         | Key variable(s)                                  | Notes                                              |
|--------------|---------------------------------------------------|-----------------------------------------------------|
| `.env`       | `DOMAIN`                                           | Public hostname, must already resolve via DNS       |
| `django_env` | `DJANGO_SECRET`, `DB_PASS`, `NEXTGEN_EMAIL/PASSWORD` | `DB_PASS` must match `POSTGRES_PASSWORD` in `db_env` |
| `db_env`     | `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_USER` | `POSTGRES_PASSWORD` must match `DB_PASS` above       |
| `mcp_env`    | `DB_DSN`                                           | Uses the `read_user` role created later, not `postgres` |

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

The files are still missing, but docker has created a pdfs volume at `/var/geo-cura-project/volumes/pdfs`.
Move all the folders of files there and make sure that they belong to root:

```console
# chown 0:0 -R /var/geo-cura-project/volumes/pdfs/*
```

### Read Only User

To safely expose the database to external uses, we create a read only user that cannot change the database and can't read sensitive tables

For that, create a file `/opt/cura/case_scraper/read_user.sql` with a strong READUSER PW

```sql

\c eviction

REASSIGN OWNED BY read_user TO postgres;
DROP OWNED BY read_user;

DROP ROLE IF EXISTS read_user;

CREATE ROLE read_user
    LOGIN
    PASSWORD '<READUSER PW>';

GRANT CONNECT ON DATABASE eviction TO read_user;
GRANT USAGE ON SCHEMA public TO read_user;


GRANT SELECT ON 
   public.attending_checkinsheet ,
     public.cases_casesnapshot     ,
 public.cases_courtcase        ,
 public.cases_disposition      ,
 public.cases_docketentry      ,
 public.cases_event            ,
 public.cases_finance          ,
 public.cases_party            ,
 public.cases_source           ,
 public.fcmcclerk_page         ,
 public.nextgen_page           ,
 public.nextgen_scandocketentry ,
 public.geocode_location,
  public.latest_overview ,
  public.latest_snapshot,
 public.nextgen_magistrate_presence,
 public.nextgen_roicount,
 public.nextgen_magdecanalysis,
 public.nextgen_scandocketentry_magdec_analyses
TO read_user;
```

To reload changes for the read_user, execute 

```console
$ docker compose exec -T -u postgres db psql < read_user.sql
```

### MCP Server

To expose the mcp server safely with authentication requires multiple services to work together and expose an OIDC flow.

We use authelia as IDP. It requires the following configuration in `/opt/cura/case_scraper/authelia/configuration.yml`

More details are available at https://www.authelia.com/configuration/prologue/introduction/

Create 4 different, fresh secrets with
```console
# openssl rand -base64 45
qq...
```
for the following positions:
* identity_validation.reset_password.jwt_secret
* session.secret
* storage.encryption_key
* identity_providers.oidc.hmac_secret

You also need to generate a RSA 2048 secret key with
```console
openssl genrsa -out tempkey.pem 2048
```
to a `tempkey.pem` file.
Copy the content of this file to identity_providers.oidc.jwks[0].key
but watch out that all lines have the same and correct indentation.

Finally generate a client secret with

```console
# docker run --rm authelia/authelia:latest authelia crypto hash generate argon2 --variant argon2id --random --random.length 72 --random.charset rfc3986
Random Password: pZ...
Digest: $argon2id$v=19$m=65536,t=3,p=4$...
```

```yaml
server:
  # Tell Authelia to listen on the subpath context
  address: 'tcp://0.0.0.0:9091/authelia'

log:
  level: info

identity_validation:
  reset_password:
    jwt_secret: 'secret 1 from openssl'

authentication_backend:
  file:
    path: /config/users_database.yml
    watch: true

access_control:
  default_policy: 'one_factor' # Change to 'one_factor' if you don't want 2FA enforced by default

session:
  name: authelia_session
  secret: 'secret 2'
  cookies:
    - domain: 'as-cura-server.asc.ohio-state.edu'
      authelia_url: 'https://as-cura-server.asc.ohio-state.edu/authelia'

storage:
  encryption_key: 'secret 3'
  local:
    path: /config/db.sqlite3

notifier:
  disable_startup_check: false
  filesystem:
    filename: /config/notification.txt

identity_providers:
  oidc:
    hmac_secret: 'secret 4'
    # required JWKS configuration for signing tokens
    jwks:
      - key_id: 'mcp-key'
        algorithm: 'RS256'
        use: 'sig'
        # Authelia can auto-generate a key pair if you pass a file path
        key: |
                -----BEGIN PRIVATE KEY-----
                MIIE...
                -----END PRIVATE KEY-----
    clients:
      - client_id: claude-mcp
        client_secret: "$argon2id$v=19$m=65536,t=3,p...."
        client_name: "Claude.ai Integration"
        public: false 
        authorization_policy: one_factor
        redirect_uris:
          - https://claude.ai/mcp/callback
          - https://claude.ai/api/mcp/auth_callback

        # issue JWT access tokens instead of opaque strings
        access_token_signed_response_alg: 'RS256'

        response_types:
          - code
        # allow Claude to authenticate using POST body parameters
        token_endpoint_auth_method: 'client_secret_post'
        # scopes Claude requests (including offline_access, groups, etc.)
        scopes: 
          - openid
          - profile
          - email
          - offline_access
          - groups
          - address
          - phone
        
        # allows Refresh Token generation for offline_access
        grant_types:
          - authorization_code
          - refresh_token
        audience: ["https://as-cura-server.asc.ohio-state.edu"]

```

After the configuration file is done, start the authelia container once:

```console
# docker compose up authelia
[+] Running 1/1
 ✔ Container case_scraper-authelia-1  Created                                                                                                                                     0.0s 
Attaching to authelia-1
authelia-1  | time="2026-07-20T14:34:44Z" level=warning msg="Configuration: access_control: no rules have been specified so the 'default_policy' of 'one_factor' is going to be applied to all requests"
authelia-1  | time="2026-07-20T14:34:44Z" level=info msg="Authelia v4.39.20 is starting"
authelia-1  | time="2026-07-20T14:34:44Z" level=info msg="Log severity set to info"
authelia-1  | time="2026-07-20T14:34:44Z" level=info msg="Storage schema is being checked for updates"
authelia-1  | time="2026-07-20T14:34:44Z" level=info msg="Storage schema migration from 0 to 24 is being attempted"
authelia-1  | time="2026-07-20T14:34:44Z" level=info msg="Storage schema migration from 0 to 24 is complete"
authelia-1  | time="2026-07-20T14:34:44Z" level=error msg="Error checking user authentication YAML database" error="user authentication database file doesn't exist at path '/config/users_database.yml' and has been generated"
authelia-1  | time="2026-07-20T14:34:44Z" level=error msg="Error occurred running a startup check" error="one or more errors occurred checking the authentication database" provider=user
authelia-1  | time="2026-07-20T14:34:49Z" level=warning msg="Could not determine the clock offset due to an error" error="error occurred reading ntp packet response to the connection: read udp 172.18.0.4:46010->...:123: i/o timeout"
authelia-1  | time="2026-07-20T14:34:49Z" level=fatal msg="One or more providers had fatal failures performing startup checks, for more details check the error level logs" providers="[user]" stack="github.com/authelia/authelia/v4/internal/commands/root.go:93 (*CmdCtx).RootRunE\ngithub.com/spf13/cobra@v1.10.2/command.go:1015               (*Command).execute\ngithub.com/spf13/cobra@v1.10.2/command.go:1148               (*Command).ExecuteC\ngithub.com/spf13/cobra@v1.10.2/command.go:1071               (*Command).Execute\ngithub.com/authelia/authelia/v4/cmd/authelia/main.go:11      main\ninternal/runtime/atomic/types.go:194                         (*Uint32).Load\nruntime/asm_amd64.s:1771                                     goexit"
```

After this first run, the user database is created at `authelia/users_database.yml`

Edit the file to create users, remove the Test User:

```yaml
# yamllint disable rule:line-length
---
###############################################################
#                         Users Database                      #
###############################################################

# This file can be used if you do not have an LDAP set up.

users:
  justicetech:
    displayname: "JusticeTech"
    password: "$argon2id$v=19$m=65536,t=3,p=4$..." 
    email: "jt@usu.edu"
    groups:
      - admins
      - mcp-users
...
# yamllint enable rule:line-length

```

You can generate the password hash with 

```console
# docker run --rm -it authelia/authelia:latest authelia crypto hash generate pbkdf2 --variant sha512 
```
and have to enter the password twice.

Start the container again with

```console
# docker compose up -d authelia
```

Then you should have a login view at https://as-cura-server.asc.ohio-state.edu/authelia
The password for justicetech should work with an *Authenticated* page

#### Metadata

The OIDC relying party needs to know a few endpoints and other information.
This is served at a `.well-known` location.

Create the folder `metadata` and the two files that must have no file extension:

`/opt/cura/case_scraper/metadata/oauth-authorization-server` 

```json
{
  "issuer": "https://as-cura-server.asc.ohio-state.edu/authelia",
  "authorization_endpoint": "https://as-cura-server.asc.ohio-state.edu/authelia/api/oidc/authorization",
  "token_endpoint": "https://as-cura-server.asc.ohio-state.edu/authelia/api/oidc/token",
  "userinfo_endpoint": "https://as-cura-server.asc.ohio-state.edu/authelia/api/oidc/userinfo",
  "jwks_uri": "https://as-cura-server.asc.ohio-state.edu/authelia/jwks.json",
  "response_types_supported": ["code"],
  "subject_types_supported": ["public"],
  "id_token_signing_alg_values_supported": ["RS256"],
  "scopes_supported": ["openid", "profile", "email"]
}
```

`/opt/cura/case_scraper/metadata/oauth-protected-resource`

```json
{
  "resource": "https://as-cura-server.asc.ohio-state.edu",
  "authorization_servers": [
    "https://as-cura-server.asc.ohio-state.edu/authelia"
  ]
}
```

Start the metadata server and the mcp server:

```console
# docker compose up -d mcp-metadata mcp
```

Verify that the files are present at https://as-cura-server.asc.ohio-state.edu/.well-known/oauth-authorization-server

#### Connecting Claude.ai

Once the metadata and MCP containers are running, add a custom connector in Claude.ai using:

* MCP server URL: https://as-cura-server.asc.ohio-state.edu/mcp
* Client ID: `claude-mcp` (or whatever `client_id` you set above)
* Client secret: the plaintext secret generated above — **not** the hashed `client_secret` value stored in the Authelia config

### Scrapers

Now you can start the scrapers:

```console
# docker compose up -d scraper_public
```

When looking at the logs, it should refresh the materialized and then fetch the reports:

```console
# docker compose logs scraper_public
scraper_public-1  | start scraping
scraper_public-1  | refresh materialized
scraper_public-1  | refreshing CSVs
scraper_public-1  | fetching csv <a href="/storage/shared/civil-fed/FCMC Civil F.E.D. (Eviction) Case List 2026-07-01 to 2026-07-31.csv?678971" target="_blank">FCMC Civil F.E.D. (Eviction) Case List 2026-07-01 to 2026-07-31.csv</a>
scraper_public-1  | fetching csv <a href="/storage/shared/civil-fed/FCMC Civil F.E.D. (Eviction) Case List 2026-06-01 to 2026-06-30.csv?287790" target="_blank">FCMC Civil F.E.D. (Eviction) Case List 2026-06-01 to 2026-06-30.csv</a>
```

Proceed similarely with the other scrapers:

```console
# docker compose up -d scraper_nextgen
```

```console
# docker compose logs scraper_nextgen
scraper_nextgen-1  | start scraping
scraper_nextgen-1  | still 10 cases to scrape
scraper_nextgen-1  | next case case_number='2026 CVG 0...' digest=None earliest=None restart=False
scraper_nextgen-1  | skip download, exists: DISMISSED BY PLAINTI...
scraper_nextgen-1  | skip download, exists: BAILIFF RETURN FILED...
scraper_nextgen-1  | skip download, exists: IMAGE OF COMPLAINT...
```

And any other scraper defined in the compose file.

### Analysis

There are also analysis jobs running in containers:

The magdec extracts the checkboxes from Magistrate Decisions:

```console
# docker compose up -d magdec_analysis

# docker compose logs magdec_analysis
magdec_analysis-1  | start extracting
magdec_analysis-1  | process 2025 CVG 0... ###- DMAGDEC - CV Docket -###.pdf
magdec_analysis-1  | page number 0
magdec_analysis-1  | all done, sleep 6h

```

The geocoder fetches coordinates for addresses in the data:

```console
# docker compose up -d geocoder 

# docker compose logs geocoder 
geocoder-1  | start geocoding
geocoder-1  | could not geolocate 106301: DEF ...  /  to {'address': '', 'score': 0, 'attributes': {'ResultID': 1, 'Status': 'U', 'Score': 0, 'Match_addr': '', 'LongLabel': '', 'ShortLabel': '', 'Addr_type': '', 'Type': '', 'PlaceName': '', 'Place_addr': '', 'Phone': '', 'URL': '', 'Rank': 0, 'AddBldg': '', 'AddNum': '', 'AddNumFrom': '', 'AddNumTo': '', 'AddRange': '', 'Side': '', 'StPreDir': '', 'StPreType': '', 'StName': '', 'StType': '', 'StDir': '', 'BldgType': '', 'BldgName': '', 'LevelType': '', 'LevelName': '', 'UnitType': '', 'UnitName': '', 'SubAddr': '', 'StAddr': '', 'Block': '', 'Sector': '', 'Nbrhd': '', 'District': '', 'City': '', 'MetroArea': '', 'Subregion': '', 'Region': '', 'RegionAbbr': '', 'Territory': '', 'Zone': '', 'Postal': '', 'PostalExt': '', 'Country': '', 'LangCode': '', 'Distance': 0, 'X': 0, 'Y': 0, 'DisplayX': 0, 'DisplayY': 0, 'Xmin': 0, 'Xmax': 0, 'Ymin': 0, 'Ymax': 0, 'ExInfo': ''}} because of KeyError('location')
```

There will be a few undecodable addresses, which is fine.

### Verify

All services are configured and can be started together as well:

```console
# docker compose up -d
[+] Running 9/9
 ✔ Container case_scraper-mcp-metadata-1     Running                                                                                                                              0.0s 
 ✔ Container case_scraper-db-1               Healthy                                                                                                                              0.5s 
 ✔ Container case_scraper-authelia-1         Running                                                                                                                              0.0s 
 ✔ Container case_scraper-mcp-1              Running                                                                                                                              0.0s 
 ✔ Container case_scraper-ui-1               Healthy                                                                                                                              1.0s 
 ✔ Container case_scraper-scraper_nextgen-1  Started                                                                                                                              1.3s 
 ✔ Container case_scraper-magdec_analysis-1  Started                                                                                                                              1.2s 
 ✔ Container case_scraper-geocoder-1         Started                                                                                                                              0.7s 
 ✔ Container case_scraper-scraper_public-1   Started                                                                                                                              1.1s 

# docker compose ps
NAME                             IMAGE                                             COMMAND                  SERVICE           CREATED          STATUS                    PORTS
case_scraper-authelia-1          authelia/authelia:latest                          "/app/entrypoint.sh"     authelia          43 minutes ago   Up 23 minutes (healthy)   9091/tcp
case_scraper-db-1                postgis/postgis:18-3.6                            "docker-entrypoint.s…"   db                5 days ago       Up 5 days (healthy)       5432/tcp
case_scraper-geocoder-1          ghcr.io/osu-justicetech/case_collector:main       "sh -c 'uv run manag…"   geocoder          3 minutes ago    Up 8 seconds              
case_scraper-magdec_analysis-1   ghcr.io/osu-justicetech/case_collector:main       "sh -c 'uv run manag…"   magdec_analysis   5 minutes ago    Up 8 seconds              
case_scraper-mcp-1               ghcr.io/osu-justicetech/case_collector-mcp:main   "uv run server.py"       mcp               11 minutes ago   Up 11 minutes             8000/tcp
case_scraper-mcp-metadata-1      halverneus/static-file-server:latest              "/serve"                 mcp-metadata      14 minutes ago   Up 14 minutes             8080/tcp
case_scraper-scraper_nextgen-1   ghcr.io/osu-justicetech/case_collector:main       "sh -c 'uv run manag…"   scraper_nextgen   7 minutes ago    Up 8 seconds              
case_scraper-scraper_public-1    ghcr.io/osu-justicetech/case_collector:main       "sh -c 'uv run manag…"   scraper_public    5 days ago       Up 8 seconds              
case_scraper-ui-1                ghcr.io/osu-justicetech/case_collector:main       "sh -c 'uv run manag…"   ui                5 days ago       Up 5 days (healthy)       
```

## Updating

To pull the latest images built by CI and recreate the containers, run

    docker compose pull
    docker compose up -d
