# Troubleshooting

## Docker daemon is not running

Open Docker Desktop, wait until it reports that it is running, then retry:

```bash
docker compose up --build
```

## API is unavailable

Check service state and logs:

```bash
docker compose ps
docker compose logs backend
```

Then test:

```bash
curl http://127.0.0.1:8000/health
```

## PostgreSQL migration errors

Confirm PostgreSQL is healthy:

```bash
docker compose logs postgres
docker compose exec postgres pg_isready -U seizureai -d seizureai
```

Run the migration manually inside the backend container:

```bash
docker compose run --rm backend alembic -c backend/alembic.ini upgrade head
```

## Upload returns 400

Check that:

- the file extension is `.zip`;
- the ZIP contains at least one `.edf` file;
- the archive does not contain unsafe paths;
- `patient_reference` is not blank.

## Session completes with errors

Inspect the session status and backend logs. Common causes are:

- EDF cannot be read;
- mixed channel sampling rates;
- sampling rate is not 256 Hz;
- one or more required model channels are missing;
- recording is shorter than four seconds.

One failed EDF does not necessarily mean every recording failed.

## Background task did not complete

The prototype runs processing inside the FastAPI process after returning the
upload response. Check the backend logs:

```bash
docker compose logs -f backend
```

Then query the session status:

```bash
curl http://127.0.0.1:8000/api/sessions/SES-ABC123/status
```

If the backend container restarted, its in-process background task may have
been interrupted. Upload the session again after confirming the backend is
healthy. Redis/RQ can be introduced later if durable retries are required.

## No real model predictions

The repository currently uses `MODEL_RUNTIME=stub`. Stub predictions and
explanations are deterministic development outputs and are not clinical.
