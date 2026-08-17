# Database

PostgreSQL stores metadata, processing state, and result references. EEG
binary data is stored in the session storage volume instead.

## Tables

### `sessions`

One row per uploaded ZIP archive.

Important fields:

- `session_id`: public opaque identifier;
- `patient_reference`: restricted internal reference;
- `original_path`: private archive path;
- `status`: current session state;
- `current_stage`: current background-processing stage;
- `created_at`, `completed_at`: lifecycle timestamps.

### `recordings`

One row per EDF extracted from a session.

Stores the generated `record_id`, sequence index, technical metadata, private
artifact paths, status, and safe error message.

### `processing_attempts`

Audit trail for each background-processing stage. It records the session,
optional recording, stage, status, start time, finish time, and bounded error
message.

### `predictions`

One row per model window. It stores model name/version, probability, threshold
decision, and start/end time in the recording.

### `explanations`

One row per explanation artifact. PostgreSQL stores the private artifact
reference and JSON metadata; the large artifact itself remains in storage.

## Migrations

Migration files live under `backend/migrations/versions/`.

The original `001_initial` migration contains the old queue identifiers because
that migration may already have been applied. `002_remove_rq_job_ids` removes
those legacy columns and indexes without rewriting migration history.

Upgrade:

```bash
alembic -c backend/alembic.ini upgrade head
```

The Docker backend runs this command before starting FastAPI.
