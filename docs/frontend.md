# Frontend guide

The frontend is a Next.js App Router application. It owns browser screens and
display state; FastAPI owns authentication, data, processing, and results.
Before visual changes, read [the design rules](../DESIGN.md) and
[frontend instructions](../frontend/AGENTS.md).

## Main screens

- /login — local account sign-in and registration.
- /dashboard — owner-scoped cases and three intake choices: EEG + video, EEG only, or video only.
- /upload — select a patient folder with a report, EEG recordings, and related videos.
- /upload/eeg — one EEG workspace. The tabs switch between a new analysis and
  past reviews without leaving the workspace. A report is optional and video
  files are ignored. /sessions redirects to its review tab; /sessions/{id} and
  /results/{id} open a specific EEG result.
- /analysis — a workspace linking independent EEG and video jobs.
- EEG result review shows the owner's recording, window scores, source events,
  and a shared EEG/video clock when a unique metadata mapping exists. When
  same-case clips are present, **Show synchronized video popup** is unchecked
  by default. Seeking EEG never opens it automatically. When enabled, the
  non-blocking popup follows EEG navigation and stays open until dismissed;
  when clinical review is enabled, matched clips synchronize through their
  unique metadata mapping, while unmatched clips retain their alignment
  status. Scores remain separate.
- /video-detection — one video workspace. Its tabs switch between upload and
  past reviews; /video-reviews redirects to the review tab. One detection job
  runs pose checks and VSViG independently of clinical reference playback.
  The result page reports score/pose status and provides playback only when
  the clinical-video gate allows it. New reference copies are unblurred and
  audio-free when enabled; VSViG patches are unblurred. Historical privacy
  labels are preserved.
- /video-privacy — legacy route that redirects to the unified video workflow.

## Code map

- frontend/src/app/ — routes and layout.
- frontend/src/components/ — screens and reusable UI.
- frontend/src/lib/api.ts — the browser's API adapter.
- frontend/src/lib/types.ts — frontend view-model types.
- frontend/tests/e2e/ — browser behavior tests.

Keep API calls in the existing adapter. The app uses the backend's HttpOnly
session cookie; do not put credentials or auth state in local storage. Browser
stub mode is for synthetic UI tests and does not exercise backend inference.

## Privacy and score display

The folder intake reads a DOC/DOCX report through the local Next.js app. Any
extracted fields are saved automatically to the encrypted, owner-only case
profile when processing starts and displayed in Patient Review without an
approval step. Extraction can make mistakes. If no patient name is extracted,
the case reference labels the review. If extraction fails or finds no fields,
EEG/video processing can still continue. The intake does not retain the
DOC/DOCX source.

In combined intake, EEG upload establishes the shared case reference. Once the
service accepts it, EEG processing and video jobs run independently. Video
jobs run one at a time; the progress panel shows the current clip and upload
progress, while the full clip list stays collapsed for large batches. EEG
processing-stage rows come from safe, owner-scoped stage and timing metadata;
error details and source paths are not included.

Do not display original filenames, patient references, or server paths. The EEG
viewer requests bounded time ranges from the encrypted, owner-scoped full review
waveform; do not fetch or cache the entire recording in the browser.
If a page has no acquired EEG samples, the viewer labels the interval as a
source gap while keeping recording time intact; synchronized video can remain
available when a verified clip mapping covers that time. Shared timestamps
are reused for same-timebase channels instead of copied into every channel.

The EEG canvas uses one fixed HUKM-style display profile: 12-second pages,
100 µV/cm, 30 mm/s, and a 0.5–70 Hz display band with a 50 Hz notch where the
source sampling rate supports it. Previous/next/first-page navigation and the
shared playhead remain; montage, sensitivity, timebase, and page-length
selectors are intentionally absent. The viewer derives the HUKM longitudinal
bipolar chains only from uniquely named, time-aligned source electrodes,
preserves auxiliary traces, and shows incomplete source coverage explicitly.
The graticule scales responsively to fit a 12-second page; its screen pixels do
not claim physical monitor calibration. It fetches only the visible time range.
See the [waveform and timebase details](inference-walkthrough.md#eeg-waveform-display).

Label the development stub as synthetic development data. Label H5 and VSViG
outputs as uncalibrated research scores unless their reviewed contracts say
otherwise. A flagged interval is for human review, not a confirmed seizure.

Imported source markers, model-flagged windows, and human observations are
separate timeline items. The current owner can save an interval observation
with movement/behavior labels and free text. Content is encrypted at rest and
the annotation routes are owner-scoped. The UI states that these are
observations, not diagnoses or seizure-onset localization. Left/right body
observations are not translated into a brain side; see the
[ILAE 2025 classification](https://www.ilae.org/files/dmfile/updated-classification-of-epileptic-seizures-2025.pdf)
and the ILAE Commission on Diagnostic Methods/EEG Task Force
[seizure-semiology glossary](https://onlinelibrary.wiley.com/doi/full/10.1684/epd.2022.1430),
which describes sign-specific lateralizing value and temporal sequence.

The EEG result screen may display bounded research attribution when it is
available from a compatible H5 model and reviewed background dataset. It is
labelled **Model contribution**, not seizure-origin localization. If the
attribution cannot be produced, the screen reports it as unavailable. This
optional analysis is supplementary; time-stamped scores, source traces, and
events remain the review evidence. Video's existing graph Grad-CAM is also
research-only and maps contribution to sampled time/keypoint patches, not
pixel-level localization or clinical cause.

The shared source-clock playhead drives EEG navigation and verified video
seeking. Video playback reports its position back to the same clock. The player
switches between verified mapped segments, pauses in genuine coverage gaps,
and leaves the EEG timeline available. Outside a verified mapping, an
individual clip can be viewed only if the clinical-video gate allows access;
it is not described as synchronized. Standalone VSViG results retain encrypted
source/review media until case deletion; earlier expired jobs remain expired.
The pinned model exposes body-pose and patch-relevance overlays, not facial
Action Unit estimates.

Generated local setup sets `MDS01_CLINICAL_VIDEO_REVIEW_ENABLED=true`; the
backend fallback is `false` when no value is configured. Reference-only intake
and owner playback work independently of VSViG. The UI labels
human observations, source annotations, and model results separately. The
pinned video pipeline provides body-pose and patch-relevance overlays; it does
not produce facial Action Units.
