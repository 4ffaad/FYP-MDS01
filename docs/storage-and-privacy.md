# Storage and privacy

## Directory layout

Each session uses this private layout:

```text
backend/storage/sessions/{session_id}/
  original/upload.zip
  extracted/{edf files}
  deidentified/{REC-*.edf}
  processed/{REC-*.npz}
  explanations/prediction-*.json
```

In Docker, this directory is backed by the `backend_storage` volume used by the
FastAPI process and its in-process background task.

## Database versus files

PostgreSQL stores IDs, status, technical metadata, timestamps, predictions,
and internal file references. It does not store complete EEG signals or ZIP
archives in ordinary columns.

## API privacy rules

Public responses must not expose:

- `patient_reference`;
- original client filenames, which may contain identifiers;
- original EDF metadata;
- absolute or relative server filesystem paths;
- unrestricted original ZIP or EDF files.

The signal endpoint returns only bounded data from a de-identified EDF.

## Original-file retention

Original files are retained per session according to
`ORIGINAL_RETENTION_DAYS`. This setting is a development configuration, not a
replacement for an approved ethics or institutional retention policy.

## Logging

Logs should use opaque session/record IDs. Never log patient names, clinical
references, original metadata, or raw upload contents.
