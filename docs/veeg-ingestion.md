# vEEG delivery runbook

This project treats the delivered vEEG data as sensitive clinical information.
Do not commit, email, log, or paste source filenames, patient identifiers,
annotation text, medication details, raw EEG, or raw video.

## Supported source files

- EDF/EDF+ EEG.
- Legacy single-file Nicolet `.e` EEG. The reviewed delivery layout uses a
  33-channel referential montage at 500 Hz. The adapter accepts that layout
  only when all required electrodes are present unambiguously, maps the old
  T3/T4/T5/T6 names to T7/T8/P7/P8, derives the exact reviewed 18 bipolar
  channels, and applies bounded 500-to-256 Hz polyphase resampling. A Nicolet
  `.e` is not an EDF, so the application does not try to edit an EDF header in
  the source or rewrite the original proprietary container. Its format-specific
  reader never decodes patient-information packets or event free text; it keeps
  only reviewed waveform channels, bounded segment timing, and sanitized event
  timing/class flags. The waveform is then written to a separate scrubbed EDF
  intermediate with blank patient/operator/equipment fields, a neutral fixed
  date, and the exact reviewed channel labels; the derivative is reopened and
  checked before preprocessing. That is the `.e` equivalent of metadata
  scrubbing, not a native `.e` rewrite. The encrypted source is removed by the
  existing cleanup path. The intermediate is used for the shared 256 Hz /
  18-channel / 1024-sample model contract. This is a technical conversion, not clinical
  validation of the model on the source montage. Per-segment TSINFO/channel-map
  changes are not supported: the reader fails closed rather than applying one
  segment's map to another. Time-contiguous source segments are coalesced before
  resampling and filtering; non-overlapping acquisition gaps remain explicit.
  Filters run per contiguous interval, z-score normalization uses only recorded
  samples, and windows never bridge a gap. Boundaries within half a sample are
  treated as timestamp jitter and coalesced; larger positive gaps remain
  separate, with repeated sub-tolerance deltas checked cumulatively. Model-window starts retain elapsed
  offsets relative to the first segment in `float64`; ingestion and previews
  fail closed when float spacing cannot resolve the 256 Hz sample grid. Gaps are
  not filled with synthetic
  samples. Overlaps beyond the half-sample timing tolerance fail closed.
  Positive recordings with gaps retain
  encrypted model windows and timestamps rather than a misleading continuous
  EDF clip. A segment shorter than one four-second model window cannot produce inference
  input, so it is excluded before filtering and normalization and counted as
  discarded; processing fails when no full window remains. A gapped NPZ preview
  reports the session's actual privacy representation instead of assuming
  signal obfuscation. Embedded event sections have a 64 MiB aggregate limit
  and a configurable packet-count limit (`MDS01_MAX_LEGACY_NICOLET_EVENTS`, default
  100,000).
  Event-to-segment mapping is capped at 1,000,000 comparisons per read, so an
  extreme event/segment combination fails closed. Padding and short trailing
  bytes are scanned in bounded 64 KiB chunks.
- MNE Nicolet `.data` EEG only when its same-stem `.head` sidecar is present.
  The reader checks the channel-count × sample-count budget
  (`MDS01_MAX_NICOLET_SIGNAL_VALUES`, default 20,000,000) from header metadata
  before MNE preloads the signal array; the effective maximum duration therefore
  depends on the input channel count and sampling rate.
- AVI, MP4, MOV, and WebM video. VSViG uses 1920x1080 input. The local H5
  profile experimentally resizes smaller readable videos to that geometry;
  this does not make their scores equivalent to native input. Other profiles
  require `VSVIG_ALLOW_LETTERBOX_ADAPTATION=true` to admit smaller clips. A
  constant stream timestamp
  origin may be removed; timestamp jitter, decode truncation, unsafe duration,
  and poor pose quality still fail closed. AVI is decoded through the existing
  audio-free privacy/video path; source audio is not a visual model input.
  During queued/processing retention, the encrypted original may still contain
  source audio; it is deleted after processing. Detection uses one shared pose
  pass to create scores and an audio-free, full-frame-blurred validation
  visualization with a skeleton overlay. That visualization is transient and
  deleted before the job is ready; detection retains only encrypted predictions
  and safe job/provenance metadata, with no video or visualization preview
  endpoint. The separate owner-scoped video-privacy utility may retain its own
  encrypted protected preview, optionally with a body-joint overlay. That is a
  distinct transform: it does not run VSViG or facial Action Units. The strict
  VSViG geometry contract is unchanged.

`.doc` and `.docx` reports are not EEG inputs and never enter inference. The
local one-patient intake uses macOS `textutil` to create a bounded editable list
of labeled fields and unlabelled report text. It does not derive age from DOB.
The operator can edit, remove, or unselect each field; only reviewed selections
are encrypted into the owner-scoped profile. The source document is not stored.
See
[one-patient research/demo](one-patient-research-demo.md) for the local boundary.

## Safe processing order

The application does not overwrite the supplied EEG. It keeps the upload
encrypted in private storage, then creates a separate model-input derivative
before inference. For EDF, the EDF header scrubber clears identifying fields.
For Nicolet `.e`, the reader's whitelist and scrubbed EDF intermediate are used;
no original patient/event text is copied into that intermediate. Every model
derivative must contain the exact reviewed 18-channel bipolar
montage in contract order. Extra channels (and their possibly identifying
labels) are dropped only after all 18 required labels have been matched;
missing or duplicate required channels fail closed. Patient/operator/equipment
fields, sex, birthdate, annotation descriptions, and the source calendar date
are removed or neutralized and checked by reopening the derivative. Relative
event timing is retained for review. The encrypted original is removed by the
normal cleanup path after processing. This does not make EEG waveform data
anonymous; use only data approved for this research workflow.

1. Mount the delivery read-only and perform an inventory of extensions, sizes,
   technical headers, and file counts. Do not execute the supplied Windows
   viewer installer on the development host.
2. Inspect one representative `.e` file and one representative AVI before
   processing the rest. Confirm the `.e` file reaches `source_format=nicolet-e`,
   has finite signal data, and exposes sanitized event timing.
3. Select one patient folder, include one or more EEG sources, and review the
   report fields. Video files in the folder are candidates only; names do not
   pair recordings. The signed-in operator must select and confirm each clip
   before its preflight upload.
4. Submit an EEG-only ZIP. Preflight each video separately; only native
   1920x1080 originals can proceed to an independent video job with the same
   opaque case ID. The EEG event endpoint
   exposes only onset, duration, event kind, and whether text was present;
   `human_review_required` remains true.
5. Align an EEG event to video only when the recording/video clock relationship
   is explicit and unambiguous. If the video start time, offset, or patient
   association is uncertain, stop and mark the pair for manual review.
6. Expect non-native geometry, low-quality or laggy CCTV to fail closed at
   resolution, timing, decode, or pose-quality admission. Do not lower the pose
   gate to manufacture a video pose-quality admission. OpenPose and VSViG receive
   the same full-frame-blurred native-resolution frames. The source and all transient derivatives are
   private, owner/job-scoped, and removed during cleanup.
7. Keep medication/treatment information outside prediction labels and public
   API responses. Retain only what the approved research/privacy policy allows.
8. Keep source checksums and conversion metadata in the owner-internal audit
   boundary. For Nicolet `.data` inputs, checksum both the data file and its
   matching `.head` sidecar because the sidecar defines how the data is read.
   Do not copy checksums or source paths into public artifacts or logs.

## Current limitation

The application supports the legacy `.e` and AVI formats, but automatic
EEG-event-to-video clock alignment still requires verified timing metadata.
Video candidates require explicit operator association; neither folder
membership nor a matching filename stem proves a relationship. The supplied
640x480 clips are blocked by default; the opt-in letterbox path is experimental
and its scores are not equivalent evidence to native 1920x1080 results. No
clinical diagnosis, seizure subtype classification, calibration, or publication
readiness is implied by the prototype output.
