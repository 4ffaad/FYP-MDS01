# Backend

FastAPI, PostgreSQL, and encrypted private file storage run through Docker
Compose. Start with the [local setup](../docs/setup.md), then use the
[backend guide](../docs/backend.md) or [architecture](../docs/architecture.md).
The [video runbook](../docs/video-detection.md) documents pinned VSViG assets
and its inference contract.

Keep route handlers thin, database queries in repositories, and patient
binaries out of PostgreSQL. Use Alembic for schema changes.
