# Local setup

## Two environments

There are two separate environments:

1. Docker runs the application stack, including PostgreSQL and FastAPI.
2. `.venv` runs local Python tests and development scripts.

You do not need to activate `.venv` when using Docker.

## Start the full stack

From the repository root:

```bash
docker compose up --build
```

The backend container runs the Alembic migration before starting FastAPI.
Open:

```text
http://127.0.0.1:8000/docs
```

## Stop the stack

Press `Ctrl+C` in the running terminal, or use:

```bash
docker compose down
```

This removes containers but keeps named volumes. Avoid `docker compose down -v`
unless you intentionally want to delete the local database and stored files.

## Run tests locally

```bash
PYTHONPATH=. .venv/bin/python -m unittest discover -s backend/tests -v
```

Equivalent activated-venv workflow:

```bash
source .venv/bin/activate
PYTHONPATH=. python -m unittest discover -s backend/tests -v
```

## Inspect services

```bash
docker compose ps
docker compose logs -f backend
```

## Inspect PostgreSQL

```bash
docker compose exec postgres psql -U seizureai -d seizureai
```

Useful SQL:

```sql
\dt
SELECT session_id, status FROM sessions;
SELECT record_id, status FROM recordings;
\q
```

## Run migrations manually

Inside the backend image or an environment with dependencies installed:

```bash
alembic -c backend/alembic.ini upgrade head
```

Never use application startup table creation as a substitute for migrations.
