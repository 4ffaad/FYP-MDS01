# Code map and reading order

Read the backend in this order:

## 1. Application entry point

`backend/app/main.py` creates FastAPI and includes the health, session, and
recording routers.

## 2. Configuration and database

- `backend/app/core/config.py`
  - `Settings`
  - `ensure_runtime_directories`
- `backend/app/database/db.py`
  - `get_session`
- `backend/app/database/models/eeg.py`
  - status enums;
  - `EEGSession`, `EEGRecording`, `ProcessingAttempt`, `Prediction`, and
    `Explanation`.
- `backend/app/database/repositories/`
  - public-ID lookup and ordered list functions.

## 3. HTTP API

- `api/health.py`: `health`
- `api/sessions.py`: upload, listing, detail, status, and recording routes
- `api/recordings.py`: recording, prediction, explanation, and signal routes

Routes validate HTTP input and delegate to services. They should not contain
long-running EEG logic.

## 4. File and privacy services

- `services/storage_service.py`: `SessionStorage` directory, upload, and
  extraction methods;
- `services/validation_service.py`: `validate_edf`;
- `privacy/deidentify.py`: `generate_record_id`, `inspect_metadata`, and
  `deidentify_edf`;
- `privacy/hashing.py`: `sha256_file` and `stable_probability`.

## 5. EEG processing

- `eeg/edf_io.py`: `read_uniform_edf`;
- `eeg/preprocessing.py`: `EEGPreprocessor` filtering, normalization, and
  clipping methods;
- `eeg/model_input.py`: `prepare_model_windows` and
  `preprocess_edf_to_npz`.

## 6. Model boundary

- `backend/model/best_seizure_model.h5`: unintegrated model artifact; do not
  load it until its runtime and training contract are verified;
- `ml/interface.py`: `WindowPrediction` and `InferenceService`;
- `ml/model_loader.py`: `get_inference_service`;
- `ml/stub_inference.py`: `StubInferenceService.predict`.

## 7. Background processing orchestration

- `services/processing_service.py`: `process_session`, session state updates,
  processing attempts,
  per-recording pipeline, predictions, and explanation creation;
- `services/session_service.py`: session IDs, upload creation, and safe API
  serializers;
- `services/explanation_service.py`: development explanation artifact writer.

`api/sessions.py` registers `process_session(session_id)` with FastAPI
`BackgroundTasks` after saving the upload. There is no separate worker process
or queue in the prototype.

Every active function and method has an inline docstring describing its
purpose, inputs, outputs, errors, and privacy implications where relevant.
