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
- Patient case reviews offer a paired timeline link for a ready video when one
  ready EEG session is available. The manual time offset is an unverified
  display assumption; scores stay separate.
- /video-detection — one video workspace. Its tabs switch between upload and
  past reviews; /video-reviews redirects to the review tab. One detection job
  runs pose checks, VSViG, and protected review-video creation; its result page
  shows the score timeline and face-redacted player together.
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

Label the development stub as synthetic development data. Label H5 and VSViG
outputs as uncalibrated research scores unless their reviewed contracts say
otherwise. A flagged interval is for human review, not a confirmed seizure.
The EEG result page can show configured SHAP input sensitivity. Video shows a
VSViG graph Grad-CAM for the strongest-scoring window, mapped to its 15 sampled
keypoint patches. It represents relative model contribution, not pixel-level
localization or clinical cause. The combined page aligns separate EEG and
video threshold lanes using a manual, unverified time offset; it does not
combine their scores.
