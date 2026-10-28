# Backend file map

This is a reference list of every tracked file under `backend/` (194 files).
Read [Backend handover: start here](backend-handover.md) first for the run
command, the three processing paths, and the security overview. Files are
grouped by purpose; historical migrations and tests are kept even though they
are not imported by the live request path.

## Runtime, packaging, and dependencies

| File | Purpose |
| --- | --- |
| `backend/Dockerfile` | Builds the FastAPI image, installs pinned dependencies, and checks the video runtime. |
| `backend/README.md` | Short backend entry point linking to setup and technical guides. |
| `backend/__init__.py` | Makes `backend` an importable Python package. |
| `backend/alembic.ini` | Alembic's migration configuration. |
| `backend/requirements.txt` | Core API, EEG parsing, database, authentication, encryption, and video-file dependencies. |
| `backend/requirements-dev.txt` | Adds HTTP client support for backend tests and development. |
| `backend/requirements-research.txt` | Adds TensorFlow/H5, SHAP, and scientific tools for the local EEG research profile. |
| `backend/requirements-video-detection.txt` | Pinned CPU PyTorch dependencies for VSViG/OpenPose. |

## FastAPI application

### Entry point and HTTP routes

| File | Purpose |
| --- | --- |
| `backend/app/__init__.py` | Marks the application package. |
| `backend/app/main.py` | Builds the FastAPI app, attaches security middleware and routers, validates runtimes, and starts cleanup/recovery loops. |
| `backend/app/api/__init__.py` | Groups the HTTP router modules. |
| `backend/app/api/auth.py` | Registration, login, logout, and current-session endpoints. |
| `backend/app/api/cases.py` | Owner-scoped case summaries, patient profiles, and source reports. |
| `backend/app/api/clinical_annotations.py` | Reads, saves, and deletes owner-authored clinical observations. |
| `backend/app/api/health.py` | Public health check used by the launcher. |
| `backend/app/api/recordings.py` | Recording details, window scores, source annotations, protected waveform ranges, and original downloads. |
| `backend/app/api/sessions.py` | EEG session upload, status, recording list, and protected archive endpoints. |
| `backend/app/api/upload_contracts.py` | OpenAPI schemas for streamed binary upload endpoints. |
| `backend/app/api/uploads.py` | Creates, finalizes, checks, and deletes encrypted EEG upload drafts. |
| `backend/app/api/video_detection.py` | Creates standalone VSViG and combined-reference jobs; protects result, playback, and original-download routes. |
| `backend/app/api/video_privacy.py` | Endpoints for the separate video privacy transform workflow. |

### Shared runtime configuration and security

| File | Purpose |
| --- | --- |
| `backend/app/core/__init__.py` | Marks the shared application-configuration package. |
| `backend/app/core/config.py` | Reads and validates environment settings, paths, limits, model selections, and authentication mode. |
| `backend/app/core/middleware.py` | Rejects oversized request bodies before multipart parsing. |
| `backend/app/core/security.py` | Verifies local sessions or Cloudflare assertions, checks request origins, and exposes owner dependencies. |
| `backend/app/core/stream_upload.py` | Streams raw request bodies to bounded upload handlers. |

### Workflow services

| File | Purpose |
| --- | --- |
| `backend/app/services/__init__.py` | Marks the workflow-service package. |
| `backend/app/services/auth_rate_limiter.py` | Bounds local authentication attempts in the prototype process. |
| `backend/app/services/auth_service.py` | Hashes local passwords, manages server-side sessions, and creates configured demo accounts. |
| `backend/app/services/case_deletion_service.py` | Deletes one owner's case rows and encrypted files together. |
| `backend/app/services/case_profile_service.py` | Encrypts and validates owner-scoped patient profile fields. |
| `backend/app/services/case_service.py` | Creates opaque case IDs and produces privacy-safe case summaries. |
| `backend/app/services/case_source_report_service.py` | Validates, encrypts, reads, and deletes PDF source reports. |
| `backend/app/services/clinical_access_audit.py` | Writes a minimal log row for selected owner-authorized review actions. |
| `backend/app/services/clinical_annotation_service.py` | Encrypts and validates time-linked clinician observations. |
| `backend/app/services/explanation_service.py` | Builds human-readable, research-only summaries from EEG window scores. |
| `backend/app/services/processing_capacity.py` | Limits concurrent in-process EEG analysis work. |
| `backend/app/services/processing_service.py` | Orchestrates EEG validation, de-identification, preprocessing, H5 inference, results, and cleanup. |
| `backend/app/services/session_service.py` | Creates sessions and upload drafts, finalizes uploads, and serializes safe session status. |
| `backend/app/services/signal_service.py` | Reads bounded waveform intervals from retained encrypted EEG sources. |
| `backend/app/services/source_download_service.py` | Materializes an owner-authorized original only for a protected download response. |
| `backend/app/services/storage_service.py` | Encrypts, authenticates, reads, and cleans private session files and EEG artifacts. |
| `backend/app/services/validation_service.py` | Validates uploaded archives and EEG recording metadata before processing. |
| `backend/app/services/video_detection_service.py` | Manages encrypted video jobs, reference metadata/playback, pose admission, inference, and recovery. |
| `backend/app/services/video_privacy_service.py` | Runs bounded jobs for the separate video-privacy transform. |
| `backend/app/services/video_storage_service.py` | Stores video originals and derived media as encrypted private artifacts and serves protected ranges. |
| `backend/app/services/video_sync_service.py` | Protects and resolves EEG/video clock anchors and conservative upload-group matches. |

### Database models and query layer

| File | Purpose |
| --- | --- |
| `backend/app/database/__init__.py` | Marks the persistence package. |
| `backend/app/database/db.py` | Creates the configured SQLModel engine and per-request database session. |
| `backend/app/database/models/__init__.py` | Imports model classes so SQLModel and Alembic can discover tables. |
| `backend/app/database/models/auth.py` | Account and server-side authentication-session tables. |
| `backend/app/database/models/case_profile.py` | Encrypted patient-profile fields and review status. |
| `backend/app/database/models/case_source_report.py` | Owner/case metadata for encrypted report files. |
| `backend/app/database/models/clinical_access_event.py` | Minimal clinical-access event table. |
| `backend/app/database/models/clinical_annotation.py` | Encrypted observation metadata and ciphertext. |
| `backend/app/database/models/eeg.py` | EEG session, recording, upload draft, score, explanation, and processing-state tables. |
| `backend/app/database/models/types.py` | Reusable SQLAlchemy types for stable enum/string serialization. |
| `backend/app/database/models/video.py` | Metadata and state for the separate video-privacy job workflow. |
| `backend/app/database/models/video_detection.py` | Standalone video and combined reference job state, file pointers, encrypted sync data, and encrypted results. |
| `backend/app/database/repository.py` | Shared queries for sessions, recordings, cases, drafts, and video-privacy jobs. |
| `backend/app/database/video_detection_repository.py` | Owner-filtered queries for video-detection and VEEG-reference jobs. |

### EEG readers, privacy, and model adapters

| File | Purpose |
| --- | --- |
| `backend/app/eeg/__init__.py` | Marks the EEG input and model-preparation package. |
| `backend/app/eeg/contracts.py` | Defines the reviewed EEG input dimensions, channel order, and admission checks. |
| `backend/app/eeg/edf_io.py` | Shared EDF readers and metadata helpers. |
| `backend/app/eeg/io.py` | Detects and dispatches EDF and supported Nicolet EEG inputs. |
| `backend/app/eeg/legacy_nicolet.py` | Parses the supported legacy Nicolet `.e` format, source gaps, montage, events, and sync anchors. |
| `backend/app/eeg/model_input.py` | Builds and validates the fixed sampling, channel, and time-window tensors for inference. |
| `backend/app/eeg/preprocessing.py` | Defines EEG preprocessing utilities. |
| `backend/app/ml/__init__.py` | Marks model-loading and inference adapters. |
| `backend/app/ml/h5_compat.py` | Provides compatibility objects used to load supported legacy H5 serialization. |
| `backend/app/ml/h5_inference.py` | Checks the reviewed H5 artifact and runs the configured EEG inference contract. |
| `backend/app/ml/interface.py` | Shared model-inference input/output interface. |
| `backend/app/ml/model_loader.py` | Selects and caches the H5 or explicit development-stub runtime. |
| `backend/app/ml/shap_explanation.py` | Optional bounded SHAP generation for a compatible reviewed H5/background pair. |
| `backend/app/ml/stub_inference.py` | Deterministic synthetic scores for UI/workflow testing only. |
| `backend/app/privacy/__init__.py` | Marks the privacy/de-identification package. |
| `backend/app/privacy/crypto.py` | Loads and validates 32-byte Base64 runtime keys for AES-GCM. |
| `backend/app/privacy/deidentify.py` | Removes selected identifying EDF metadata and generates opaque recording IDs. |
| `backend/app/privacy/methods.py` | Parses and canonicalizes the supported privacy-profile settings. |
| `backend/app/privacy/retention.py` | Builds bounded retained waveform and model-window artifacts. |
| `backend/app/privacy/signal_projection.py` | Implements the optional keyed research signal-obfuscation transform. |

### Video pipelines

| File | Purpose |
| --- | --- |
| `backend/app/video_detection/__init__.py` | Marks the standalone VSViG pipeline package. |
| `backend/app/video_detection/contract.py` | Checks pinned VSViG/OpenPose source, checkpoint, and preprocessing contracts. |
| `backend/app/video_detection/runtime.py` | Extracts separate person tracks and runs the pinned pose/VSViG inference path. |
| `backend/app/video_detection/visualization.py` | Builds and validates a review visualization from one pose pass. |
| `backend/app/video_privacy/__init__.py` | Marks the separate video-privacy transform package. |
| `backend/app/video_privacy/processor.py` | Runs the bounded OpenCV privacy transform and media probes. |

### Offline research modules

These modules support evaluation and research scripts; the API does not call
them as part of its ordinary upload flow.

| File | Purpose |
| --- | --- |
| `backend/app/research/__init__.py` | Marks the offline evaluation package. |
| `backend/app/research/calibration.py` | Fits/applies simple temperature scaling to research scores. |
| `backend/app/research/chb_mit.py` | Finds CHB-MIT recordings and labelled seizure intervals. |
| `backend/app/research/evaluation.py` | Evaluates EEG utility with patient-disjoint CHB-MIT splits. |
| `backend/app/research/metrics.py` | Computes offline seizure and score-calibration metrics. |
| `backend/app/research/video_privacy_evaluation.py` | Aggregates video-model results for raw versus transformed inputs. |

## Database schema history

`backend/migrations/env.py` connects Alembic to the configured database and
model metadata. Each numbered file is one immutable schema step; do not delete
old revisions to make the folder look shorter because existing databases use
that history to upgrade safely.

| File | Schema change |
| --- | --- |
| `backend/migrations/versions/001_initial.py` | Creates the initial session, recording, score, and explanation schema. |
| `backend/migrations/versions/002_remove_rq_job_ids.py` | Removes fields for the retired RQ worker. |
| `backend/migrations/versions/003_add_requested_privacy_method.py` | Persists the requested privacy setting. |
| `backend/migrations/versions/004_remove_patient_reference.py` | Removes a direct patient reference that was not used. |
| `backend/migrations/versions/005_use_cancellable_signal_projection.py` | Replaces the old detached PSD template with the shared signal transform. |
| `backend/migrations/versions/006_add_reference_annotations.py` | Adds safe reference annotations to recordings. |
| `backend/migrations/versions/007_privacy_methods_and_retention.py` | Renames public privacy modes and adds retained-artifact metadata. |
| `backend/migrations/versions/008_calibration_scores.py` | Separates raw and calibrated scores. |
| `backend/migrations/versions/009_prediction_threshold.py` | Stores the threshold used for each score. |
| `backend/migrations/versions/010_upload_drafts.py` | Adds short-lived encrypted upload-draft records. |
| `backend/migrations/versions/011_canonical_privacy_profiles.py` | Normalizes historical privacy values. |
| `backend/migrations/versions/012_video_privacy_jobs.py` | Adds standalone video-privacy job records. |
| `backend/migrations/versions/013_calibration_provenance.py` | Stores prediction privacy and calibration provenance. |
| `backend/migrations/versions/014_local_authentication.py` | Adds accounts, sessions, and data ownership. |
| `backend/migrations/versions/015_video_detection.py` | Adds independent owner-scoped video detection jobs. |
| `backend/migrations/versions/016_case_grouping.py` | Adds opaque case grouping. |
| `backend/migrations/versions/017_demo_admin_role.py` | Adds a local demo-admin flag. |
| `backend/migrations/versions/018_video_detection_visualization.py` | Adds the retained video visualization pointer. |
| `backend/migrations/versions/019_recording_source_format.py` | Stores EEG source format provenance. |
| `backend/migrations/versions/020_recording_annotation_events.py` | Stores sanitized EEG event timing separately from seizure intervals. |
| `backend/migrations/versions/021_recording_provenance.py` | Stores source checksums and conversion metadata. |
| `backend/migrations/versions/022_case_patient_profiles.py` | Adds encrypted owner-scoped patient profiles. |
| `backend/migrations/versions/023_video_privacy_pose_preview.py` | Links video-privacy previews and pose coverage to jobs. |
| `backend/migrations/versions/024_upload_draft_finalization_idempotency.py` | Makes upload-draft finalization safe to retry. |
| `backend/migrations/versions/025_case_source_report.py` | Adds metadata pointers for encrypted case reports. |
| `backend/migrations/versions/026_video_privacy_idempotency.py` | Adds owner-scoped retry identifiers to privacy jobs. |
| `backend/migrations/versions/027_owner_case_artifact_keys.py` | Binds profile/report identities to their owner and case. |
| `backend/migrations/versions/028_video_privacy_content_fingerprint.py` | Binds privacy-job retries to uploaded-content fingerprints. |
| `backend/migrations/versions/029_profile_verification_status.py` | Marks automatically extracted profile data as unverified. |
| `backend/migrations/versions/030_video_detection_blur_strength.py` | Persists the model-input blur setting for video jobs. |
| `backend/migrations/versions/031_verified_veeg_sync.py` | Adds verified VEEG sync status, anchors, and clip links. |
| `backend/migrations/versions/032_patient_region_review_blur.py` | Records the review-video transform for historical records. |
| `backend/migrations/versions/033_owner_source_retention.py` | Adds owner-source retention while preserving historical policy. |
| `backend/migrations/versions/034_clinical_annotations.py` | Adds owner-scoped clinical observations. |
| `backend/migrations/versions/035_video_until_deletion.py` | Supports standalone video retention until deletion. |
| `backend/migrations/versions/036_on_demand_veeg_playback.py` | Tracks reference-playback preparation independently from model status. |
| `backend/migrations/versions/037_encrypted_video_results.py` | Adds nonce/ciphertext fields for encrypted VSViG results. |

## Backend support scripts

The first four scripts below are runtime/setup checks or asset installation;
the remaining scripts are optional research, evaluation, and inspection tools.

| File | Purpose |
| --- | --- |
| `backend/scripts/create_shap_background.py` | Builds profile-specific SHAP backgrounds from CHB-MIT data. |
| `backend/scripts/create_video_evaluation_manifest.py` | Builds a patient-disjoint video evaluation manifest. |
| `backend/scripts/evaluate_chb_mit.py` | Runs CHB-MIT EEG utility evaluation. |
| `backend/scripts/evaluate_video_privacy.py` | Measures video-model utility before and after face redaction. |
| `backend/scripts/fit_calibration.py` | Fits a CHB-MIT score calibrator. |
| `backend/scripts/inspect_video_vision.py` | Inspects face detection on an approved local clip. |
| `backend/scripts/install_vsvig_assets.py` | Downloads only pinned model/pose files, verifies hashes, and writes them outside Git. |
| `backend/scripts/verify_h5_model.py` | Checks a local H5 model before creating/reviewing a contract. |
| `backend/scripts/verify_video_runtime.py` | Smoke-checks the video privacy runtime using synthetic frames. |
| `backend/scripts/verify_vsvig_runtime.py` | Loads pinned pose/model weights and checks one tensor-only forward pass. |
| `backend/scripts/video_contract.py` | Emits the VSViG asset contract/manifest. |
| `backend/scripts/video_inventory.py` | Prints aggregate video metadata without identifiers or source paths. |

## Backend tests and fixtures

Tests are not imported by FastAPI at runtime. They document and check the
privacy and compatibility boundaries that must survive future changes. A
small number of PostgreSQL race/integrity tests require a disposable database;
see their test names and the setup guide before enabling those tests.

| File | What it protects or checks |
| --- | --- |
| `backend/tests/fixtures/synthetic-review.mp4` | Synthetic short clip for backend playback tests. |
| `backend/tests/generate_e2e_archive.py` | Creates a patient-free synthetic EDF archive for browser tests. |
| `backend/tests/seed_video_detection.py` | Seeds disposable synthetic video-review data. |
| `backend/tests/test_auth_rate_limiter.py` | Local login attempt limits. |
| `backend/tests/test_auth_security.py` | Public versus authenticated API boundaries. |
| `backend/tests/test_backend.py` | Basic EEG upload-to-result behavior using synthetic EDF input. |
| `backend/tests/test_case_patient_profile.py` | Owner-scoped encrypted patient profiles. |
| `backend/tests/test_case_profile_orphan_cleanup.py` | Recovery from interrupted profile/report deletion. |
| `backend/tests/test_case_report_pdf_validation.py` | Rejection of malformed or truncated source PDFs. |
| `backend/tests/test_case_report_row_locking.py` | Safe serialization of report replacement and deletion. |
| `backend/tests/test_case_report_upload_limit.py` | Memory-safe bounds on report uploads. |
| `backend/tests/test_case_source_report.py` | Owner-only source-report API behavior. |
| `backend/tests/test_case_summary_projection.py` | Privacy-safe owner-scoped case summaries. |
| `backend/tests/test_clinical_annotations.py` | Encrypted owner observation API and ownership checks. |
| `backend/tests/test_configuration.py` | Rejection of invalid or unsafe configuration. |
| `backend/tests/test_e2e_patient_folder_generator.py` | Synthetic patient-folder fixture generation. |
| `backend/tests/test_eeg_archive_dispatch.py` | Correct dispatch among supported EEG archive layouts. |
| `backend/tests/test_eeg_enum_compatibility.py` | Compatibility of persisted EEG status enums. |
| `backend/tests/test_eeg_formats.py` | EDF/Nicolet format support and metadata privacy. |
| `backend/tests/test_eeg_input_contract.py` | Fail-closed sample-rate, channel, and timeline checks. |
| `backend/tests/test_evaluation_and_explanations.py` | Research evaluation and explanation behavior. |
| `backend/tests/test_explanation_postgres_batch_integrity.py` | Optional PostgreSQL integrity for batched explanation writes. |
| `backend/tests/test_legacy_nicolet_gaps.py` | Preservation of gaps in legacy Nicolet source time. |
| `backend/tests/test_local_auth.py` | Local password/session handling and record ownership. |
| `backend/tests/test_local_research_profile.py` | H5 runtime restriction to the reviewed local profile. |
| `backend/tests/test_migration_chain.py` | Alembic upgrades from the supported prior schema states. |
| `backend/tests/test_processing_capacity.py` | Bounded in-process analysis concurrency. |
| `backend/tests/test_processing_failures.py` | Failure status and cleanup for EEG processing. |
| `backend/tests/test_retained_signal_regressions.py` | Full-source retained waveform reads. |
| `backend/tests/test_review_regressions.py` | Previously found review-workflow regressions. |
| `backend/tests/test_secure_owner_review.py` | Owner downloads, encrypted range media, VEEG conversion, cleanup, and case deletion. |
| `backend/tests/test_session_summary_repository.py` | Safe bulk summaries for session listings. |
| `backend/tests/test_signal_physical_units.py` | Source voltage conversion and invalid-unit rejection. |
| `backend/tests/test_storage_security.py` | Encryption, tampering, private paths, and opaque file identifiers. |
| `backend/tests/test_stream_upload.py` | Request-body size and streaming behavior. |
| `backend/tests/test_stream_upload_route.py` | Raw upload route boundaries for EEG drafts. |
| `backend/tests/test_upload_draft_owner_locking.py` | Safe concurrent draft finalization and case cleanup. |
| `backend/tests/test_upload_draft_postgres_concurrency.py` | Optional PostgreSQL race regression for upload drafts. |
| `backend/tests/test_upload_openapi.py` | Binary upload OpenAPI request contracts. |
| `backend/tests/test_video_detection.py` | VSViG admission, owner checks, encrypted results, VEEG playback, and synchronization matching. |
| `backend/tests/test_video_evaluation_manifest.py` | Patient-disjoint evaluation manifest generation. |
| `backend/tests/test_video_inventory.py` | Aggregate video inventory behavior. |
| `backend/tests/test_video_preflight.py` | Video format and resource admission limits. |
| `backend/tests/test_video_privacy.py` | Standalone video privacy transform and API boundaries. |
| `backend/tests/test_video_privacy_admission.py` | Concurrency and queue limits for privacy transforms. |
| `backend/tests/test_video_privacy_evaluation.py` | Aggregate privacy-utility calculations. |
| `backend/tests/test_video_privacy_idempotency.py` | Safe retries for video-privacy uploads. |
| `backend/tests/test_video_privacy_lifecycle.py` | Video-privacy status, retention, and cleanup transitions. |
| `backend/tests/test_video_runtime_compatibility.py` | Compatibility with the pinned video processing runtime. |
| `backend/tests/test_video_visualization.py` | Synthetic visualization artifact output and validation. |
| `backend/tests/test_vsvig_runtime.py` | Pinned VSViG asset contract and import boundary. |
