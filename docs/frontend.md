# Frontend internals

The frontend is a small Next.js App Router application. It owns screens and
browser state; the FastAPI backend owns sessions, processing, and results.

MDS01 — EEG Research Review is a research workspace for clinicians and clinical
researchers. Its job is to make upload state, privacy handling, and model
output easy to inspect. It does not replace clinical judgment or claim an
autonomous diagnosis.

```mermaid
flowchart TD
    Pages[frontend/src/app/] --> Screens[frontend/src/components/]
    Screens --> API[frontend/src/lib/api.ts]
    API --> FastAPI[FastAPI REST API]
    API --> Stub[Local browser stub mode]
    Screens --> Types[frontend/src/lib/types.ts]
    Tests[frontend/tests/e2e/] --> Pages
```

## User journey

```mermaid
flowchart LR
    Upload[/upload] --> Stage[Encrypt and stage ZIP]
    Stage --> Config[Choose privacy treatment]
    Config --> Submit[Submit with metadata scrub plus optional obfuscation]
    Submit --> Session[/sessions/{sessionId}]
    Session --> Dashboard[/dashboard]
    Dashboard --> Poll[Poll active sessions]
    Session --> Results[/results/{recordId}]
    Config --> Preview[Synthetic before/after preview]
    Results --> Viewer[Optional bounded retained EEG viewer]
    Results --> Timeline[Full score timeline and alert threshold]
    Results --> Prediction[Development score or reviewed model output]
```

## Frontend-to-backend calls

```mermaid
sequenceDiagram
    participant User
    participant Page as Next.js page
    participant Adapter as lib/api.ts
    participant API as FastAPI

    User->>Page: Select ZIP
    Page->>Adapter: stageUpload(file)
    Adapter->>API: POST /api/uploads/drafts
    API-->>Adapter: draft_id and expiry
    User->>Page: Select optional signal obfuscation
    Page->>Adapter: finalizeUploadDraft(draft, method)
    Adapter->>API: POST /api/uploads/drafts/{id}/finalize
    API-->>Adapter: session_id and queued status
    Adapter-->>Page: session ID
    Page->>Adapter: getSessions()
    Adapter->>API: GET /api/sessions
    API-->>Adapter: sessions with safe recording summaries
    Page->>Adapter: getResult(record ID)
    Adapter->>API: GET recording, prediction, explanation
    Adapter-->>Page: safe result view model
```

The adapter uses FastAPI by default. Set the explicit stub flag only for local
E2E tests or UI work without a backend:

```dotenv
NEXT_PUBLIC_USE_API_STUB=false
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_ENABLE_SIGNAL_PREVIEW=false
NEXT_PUBLIC_ENABLE_FULL_SIGNAL_PREVIEW=false
```

## Pages and components

- `src/app/upload/page.tsx` renders the upload route.
- `src/app/dashboard/page.tsx` renders session groups and every recording.
- `src/app/sessions/[sessionId]/page.tsx` renders one session’s timestamp and recording list.
- `src/app/results/[recordId]/page.tsx` renders one recording result.
- `src/components/UploadScreen.tsx` owns file selection and submission.
- `src/components/DashboardScreen.tsx` owns session grouping and active-session polling.
- `src/components/SessionDetailScreen.tsx` owns one session’s summary and recording list.
- `src/components/SessionRecordings.tsx` renders safe recording rows and result links.
- `src/components/ResultScreen.tsx` owns session-scoped prediction and explanation review.
- `src/components/RecordingNavigator.tsx` lets a clinician move through every safe recording in the current session.
- `src/components/PredictionTimeline.tsx` renders window scores, the alert threshold, and flagged intervals.
- `src/components/SignalViewer.tsx` requests a bounded retained positive clip only on a model-alert result page.
- `src/components/AppShell.tsx` provides shared navigation and page frame.
- `src/lib/api.ts` is the only frontend-to-backend adapter.
- `src/lib/types.ts` defines the frontend view-model types.

## Privacy behavior in the UI

```mermaid
flowchart TD
    APIResponse[Safe API response] --> SessionView[Session groups and generated recording labels]
    APIResponse --> ResultView[Prediction and explanation]
    APIResponse --> Timeline[Show score timeline]
    APIResponse --> Viewer[Request bounded signal only on alert result]
```

The frontend never displays patient references, original filenames, original
paths, unrestricted original files, or waveform samples during upload
configuration. CHB-MIT summary/sidecar intervals are not displayed to normal
users; recording rows and alert states use only model alert windows.
Development results use amber `Development flag` and `Development score`
wording. A verified calibrated runtime may use red model-alert wording. The
development score is not confidence, accuracy, or a seizure diagnosis. The
result page leads with flagged-window counts and exact alert times; the raw
peak score stays in collapsed technical details.
Completed sessions can be deleted from the dashboard or session detail page;
active sessions stay protected until processing finishes. Signal preview is
disabled unless explicitly enabled for local development and never shows a
non-alert recording.

On an alert result, the full score timeline covers the complete recording and
shows the threshold plus exact model-positive intervals. The EEG viewer draws
all 18 model channels as stacked traces and highlights the exact positive
windows. Normal local preview uses a retained clip with up to 10 minutes of
context before the first alert. A complete transformed recording is available
only when both signal-preview and full-preview flags are enabled. A recording
with no model-positive window shows the score timeline but no EEG viewer, and
no EEG artifact is retained for it. The synthetic before/after privacy preview
exists only on the upload configuration screen.

## Frontend reading order

1. `src/app/layout.tsx` and `src/components/AppShell.tsx` — shared shell.
2. `src/app/upload/page.tsx` and `UploadScreen.tsx` — first user action.
3. `src/app/dashboard/page.tsx` and `DashboardScreen.tsx` — session grouping and polling.
4. `src/app/sessions/[sessionId]/page.tsx` and `SessionDetailScreen.tsx` — session detail.
5. `src/app/results/[recordId]/page.tsx` and `ResultScreen.tsx` — recording result review.
6. `src/lib/types.ts` — view-model contracts.
7. `src/lib/api.ts` — stub/backend switch and API calls.
8. `tests/e2e/mds01.spec.ts` — expected user-visible behavior.

The visual rules live in the root [`DESIGN.md`](../DESIGN.md). Keep new visual
work aligned with that file instead of adding another design system.

Patient-video privacy is intentionally a separate future surface. When it is
implemented, it must use the video-privacy API contract and render privacy
outputs without constructing URLs from backend storage paths. See
[`_bmad-output/specs/spec-patient-video-deidentification/SPEC.md`](../_bmad-output/specs/spec-patient-video-deidentification/SPEC.md).
