# Backend architecture

This repository contains the backend only. There is no frontend yet; Swagger
at `/docs` is the current way to call the API.

## Components

```text
Client / Swagger
       |
       v
FastAPI backend (:8000)
       |
       +--> PostgreSQL
       |    sessions, recordings, statuses, predictions
       |
       +--> private session storage
       |    ZIP, EDF, NPZ, explanation JSON
       |
       +--> FastAPI BackgroundTasks
            |
            +--> validation
            +--> de-identification
            +--> preprocessing
            +--> inference adapter
            +--> explanation artifacts
```

## What each service does

| Component | Responsibility |
| --- | --- |
| FastAPI | Receives uploads, returns API responses, reads database state |
| PostgreSQL | Stores metadata and results, never large EEG binaries |
| Session storage | Stores ZIP, EDF, NPZ, and explanation files |
| Alembic | Creates and upgrades PostgreSQL tables |
| BackgroundTasks | Starts the processing pipeline after the upload response |

## Why BackgroundTasks exists

EDF processing can take longer than a normal HTTP request. The upload route
therefore creates a database session, returns HTTP 202, and registers
`process_session(session_id)` with FastAPI BackgroundTasks. The pipeline updates
status rows while the client polls the status endpoint.

This is appropriate for the prototype, but the task runs in the FastAPI process.
A server restart can interrupt it. Redis/RQ or another durable job system can
be added later for retries, multiple workers, and production-scale workloads.

## Docker services

`docker-compose.yml` starts two services:

```text
postgres  database server
backend   FastAPI + migrations + background pipeline
```

The backend uses the `backend_storage` Docker volume for private session
artifacts.
