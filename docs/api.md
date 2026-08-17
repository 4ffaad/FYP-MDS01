# API reference

The API is available at `http://127.0.0.1:8000` when Docker is running.
Interactive OpenAPI documentation is available at `/docs`.

## Health

```http
GET /health
```

This is a liveness check for the FastAPI process. It does not prove that the
database or a background task is healthy.

## Upload a session

```http
POST /api/sessions/upload
Content-Type: multipart/form-data
```

Required form fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `archive` | ZIP file | Contains one or more EDF files |
| `patient_reference` | string | Restricted internal reference |

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/sessions/upload \
  -F "archive=@/absolute/path/to/session.zip" \
  -F "patient_reference=demo-001"
```

Successful uploads return HTTP 202:

```json
{
  "session_id": "SES-ABC123",
  "status": "queued"
}
```

## Session endpoints

```text
GET /api/sessions
GET /api/sessions/{session_id}
GET /api/sessions/{session_id}/status
GET /api/sessions/{session_id}/recordings
```

The status response contains:

```json
{
  "session_id": "SES-ABC123",
  "status": "preprocessing",
  "current_stage": "preprocessing",
  "error_message": null
}
```

Possible session statuses are `queued`, `validating`, `deidentifying`,
`preprocessing`, `inference`, `explaining`, `completed`,
`completed_with_errors`, and `failed`.

## Recording endpoints

```text
GET /api/recordings/{record_id}
GET /api/recordings/{record_id}/prediction
GET /api/recordings/{record_id}/explanation
GET /api/recordings/{record_id}/signal
```

The signal endpoint accepts bounded query parameters:

```text
start_seconds=0
duration_seconds=10     # maximum 60
max_points=2000         # maximum 10000
```

Responses never include patient references, original filesystem paths, or
unrestricted original files.
