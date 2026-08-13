# EEG Privacy and Preprocessing Backend

Run the API from the project root:

```bash
.venv/bin/uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` to upload EDF files through Swagger UI.

## Public API

The application deliberately exposes only these two pipeline actions (plus
`GET /health`):

1. `POST /api/v1/deidentify`

   Upload one `.zip` archive with `archive` and `patient_reference`. The ZIP
   can contain a complete folder such as `chb01/chb01_01.edf`,
   `chb01/chb01_02.edf`, and all later EDF segments. It creates one `SES-*`
   session, one `REC-*` identifier per EDF, and writes one de-identified EDF
   per segment.

2. `POST /api/v1/preprocess/{session_id}`

   It processes every de-identified EDF in the uploaded session. Each EDF
   receives its own `storage/processed/REC-xxxx.npz` model-input artifact.

Temporary uploads are written to `storage/incoming/` and removed after each
request. Generated storage is intentionally ignored by Git.

## Model handoff

The preprocessing response is deliberately a receipt, not the EEG array:
returning a 23-channel, one-hour array in JSON would be unnecessarily large.
The model service receives the `record_id` and loads the corresponding NPZ from
shared storage:

```python
import numpy as np

payload = np.load("storage/processed/REC-xxxx.npz")
X = payload["model_windows"]              # (windows, 1024, 18), float32
window_starts = payload["window_start_seconds"]
sampling_rate = int(payload["sampling_rate"])
channel_labels = payload["channel_labels"]

# Entire EDF segment as one inference batch:
probabilities = model.predict(X)

# Or one four-second EEG window:
one_probability = model.predict(X[0:1])   # shape (1, 1024, 18)
```

The preprocessing service now enforces the confirmed model contract: 256 Hz,
the exact 18 CHB-MIT bipolar channels in training order, per-channel project
preprocessing, and non-overlapping four-second windows. It writes a float32
tensor shaped `(N, 1024, 18)`, so it is already compatible with the model's
batch input. The backend does not yet load `best_seizure_model.h5` because the
model file/runtime has not been supplied to this project; adding that adapter
is the next separate integration step.

## Local database

The prototype uses SQLite at `database/eeg.db`. SQLModel keeps database access
inside `app/database/db.py`, so a later PostgreSQL migration only requires a
`DATABASE_URL` change and migrations once the schema stabilises.

## EDF-folder uploads

Zip the patient/session folder before uploading—it is not possible for a normal
HTTP request to transmit a macOS/Windows folder as a folder. For example:

```bash
cd /path/to/chb-mit-scalp-eeg-database-1.0.0
zip -r chb01.zip chb01
```

Swagger uploads `chb01.zip` once. The backend naturally orders names such as
`chb01_2.edf` before `chb01_10.edf`, assigns each one a sequence index, and
keeps each variable-duration EDF separate. A ten-minute file and a one-hour
file therefore produce separate model artifacts and are never merged.

## Code map

- `app/main.py`: creates FastAPI and database tables at startup.
- `app/api/records.py`: the two public endpoint handlers and record status
  updates.
- `app/services/deidentification.py`: EDF header sanitisation while preserving
  signal samples and technical data.
- `app/services/eeg_preprocessor.py`: the provided four-stage signal pipeline.
- `app/services/preprocessing.py`: reads a de-identified EDF and writes the
  model-ready NPZ artifact.
- `app/database/db.py`: SQLite engine and request-scoped SQLModel sessions.
- `app/models/eeg.py`: session/record/result database schema.

## Verification

```bash
.venv/bin/python -m unittest discover -s tests -v
```
