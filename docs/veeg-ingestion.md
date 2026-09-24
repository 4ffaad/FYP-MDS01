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
  channels, and applies bounded 500-to-256 Hz polyphase resampling. It then
  converts the result to a scrubbed EDF before the shared 256 Hz / 18-channel
  / 1024-sample model contract. This is a technical conversion, not clinical
  validation of the model on the source montage. Per-segment TSINFO/channel-map
  changes are not supported: the reader fails closed rather than applying one
  segment's map to another. Signal processing is also refused when a segment
  gap or overlap exceeds the half-sample continuity tolerance; sanitized event
  timing keeps actual elapsed offsets instead of compressing those gaps.
  Embedded event sections have a 64 MiB aggregate limit and a configurable
  packet-count limit (`MDS01_MAX_LEGACY_NICOLET_EVENTS`, default 100,000).
  Event-to-segment mapping is capped at 1,000,000 comparisons per read, so an
  extreme event/segment combination fails closed. Padding and short trailing
  bytes are scanned in bounded 64 KiB chunks.
- MNE Nicolet `.data` EEG only when its same-stem `.head` sidecar is present.
  The reader checks the channel-count × sample-count budget
  (`MDS01_MAX_NICOLET_SIGNAL_VALUES`, default 20,000,000) from header metadata
  before MNE preloads the signal array; the effective maximum duration therefore
  depends on the input channel count and sampling rate.
- AVI, MP4, MOV, and WebM video. The pinned VSViG path requires 1920x1080 input
  by default. Smaller readable geometry, including the delivered 640x480 AVI,
  is converted with a bounded aspect-preserving letterbox only when the operator
  explicitly enables and reviews `VSVIG_ALLOW_LETTERBOX_ADAPTATION`. A constant stream timestamp
  origin may be removed; timestamp jitter, decode truncation, unsafe duration,
  and poor pose quality still fail closed. AVI is decoded through the existing
  audio-free privacy/video path; source audio is not a visual model input.
  During queued/processing retention, the encrypted original may still contain
  source audio; retained model and visualization artifacts contain no audio.

`.doc` reports are not EEG inputs and are not imported automatically. They may
contain medication, treatment, patient, or clinician information and require a
separate approved access boundary. They must never become an automatic seizure
label.

## Safe processing order

1. Mount the delivery read-only and perform an inventory of extensions, sizes,
   technical headers, and file counts. Do not execute the supplied Windows
   viewer installer on the development host.
2. Inspect one representative `.e` file and one representative AVI before
   processing the rest. Confirm the `.e` file reaches `source_format=nicolet-e`,
   has finite signal data, and exposes sanitized event timing.
3. Create one owner-scoped case for exactly one EEG recording and its matching
   video. Do not infer a pairing from an ambiguous filename, directory, or
   patient reference.
4. Submit the EEG ZIP and video with the same case ID. The EEG event endpoint
   exposes only onset, duration, event kind, and whether text was present;
   `human_review_required` remains true.
5. Align an EEG event to video only when the recording/video clock relationship
   is explicit and unambiguous. If the video start time, offset, or patient
   association is uncertain, stop and mark the pair for manual review.
6. Expect low-quality or laggy CCTV to fail closed at timing, decode, or
   pose-quality admission. Do not lower the pose gate to manufacture a video
   pose-quality admission. OpenPose and VSViG receive the same full-frame-blurred,
   letterboxed model-input frames. The source and all transient derivatives are
   private, owner/job-scoped, and removed during cleanup.
7. Keep medication/treatment information outside prediction labels and public
   API responses. Retain only what the approved research/privacy policy allows.
8. Keep source checksums and conversion metadata in the owner-internal audit
   boundary. For Nicolet `.data` inputs, checksum both the data file and its
   matching `.head` sidecar because the sidecar defines how the data is read.
   Do not copy checksums or source paths into public artifacts or logs.

## Current limitation

The application now supports the legacy `.e` and AVI formats, but automatic
EEG-event-to-video clock alignment still requires verified pairing metadata
from the mounted delivery. In the inspected delivery, each valid EEG had
multiple AVI candidates and no shared filename stem, so the application must
not choose a video automatically. A video filename, directory, or `.doc`
report is not sufficient proof by itself. No clinical diagnosis, seizure
subtype classification, calibration, or publication readiness is implied by
the prototype output.
