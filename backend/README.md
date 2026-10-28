# Backend

New to the project? Start with the [backend handover](../docs/backend-handover.md)
for the shortest supported startup path, the EEG/VEEG/video request flows, and
the security boundaries. The [backend file map](../docs/backend-file-map.md)
explains every tracked file in this directory.

For deeper detail, see [local setup](../docs/setup.md), the [backend guide](../docs/backend.md),
the [architecture](../docs/architecture.md), and the [video runbook](../docs/video-detection.md).

Keep route handlers thin, database queries in repositories, and patient
binaries out of PostgreSQL. Use Alembic for schema changes.
