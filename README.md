# madoc_search_proto

Build:

`docker-compose -f local.yml build`

Run:

`docker-compose -f local.yml up`

## Using a .env file

The local.yml file expects to load env variables from a .env file.

e.g.

`.env`

```..env
# General
# ------------------------------------------------------------------------------
USE_DOCKER=yes
IPYTHONDIR=/app/.ipython
MIGRATE=True
LOAD=True
DJANGO_DEBUG=False
WAITRESS=False
DJANGO_ADMIN=SOME NAME
DJANGO_ADMIN_PASSWORD=SOME PASSWORD
DJANGO_ADMIN_EMAIL=SOME PASSWORD
INIT_SUPERUSER=True  # If True, create a superuser using above credentials

# PostgreSQL
# ------------------------------------------------------------------------------
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=SOME PASSWORD # change me
DATABASE_URL=postgres://postgres:SOME PASSWORD@postgres:5432/postgres  # change me
```
