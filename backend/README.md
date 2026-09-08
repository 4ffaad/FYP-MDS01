# MDS01 backend

FastAPI, PostgreSQL and encrypted filesystem storage. Run Docker Compose from the repository root.

- [First run and tests](../docs/setup.md)
- [Architecture](../docs/architecture.md)
- [Processing, API and research commands](../docs/backend.md)
- [Interactive API reference](http://127.0.0.1:8000/docs) when running locally

Use Alembic for schema changes. Keep processing in services, database queries in repositories, and patient binaries out of PostgreSQL. The default runtime is a research-only development stub; H5 is an explicit opt-in.

Local teammate runs use `AUTH_MODE=local-accounts`: `POST /api/auth/register`
or `/api/auth/login` sets an HttpOnly session cookie, and protected EEG/video
queries are filtered by the signed-in user. `AUTH_MODE=local` is reserved for
isolated tests. Production requires Cloudflare Access.
