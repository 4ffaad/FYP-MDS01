# MDS01 frontend

MDS01 is a desktop-first clinical decision-support interface for privacy-preserving EEG seizure detection. The visual system uses the local Apple design reference as a guide for white surfaces, SF Pro-style typography, hairlines, pill actions, and restrained Action Blue.

## Run locally

From this directory:

```bash
npm install
cp .env.example .env.local
npm run dev
```

Open <http://127.0.0.1:3000>. The default `NEXT_PUBLIC_USE_API_STUB=true` makes the UI usable without a running backend. It stores generated synthetic run labels in browser `localStorage`; no original filename is rendered. Model output and overlays are labelled non-clinical.

To use the FastAPI adapter:

```dotenv
NEXT_PUBLIC_USE_API_STUB=false
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

The adapter calls the current backend session and recording routes from `src/lib/api.ts`. It submits only the ZIP and selected research privacy mode—never a patient reference or the original filename as a public value. `control` performs metadata scrubbing; `cancellable-signal-projection` additionally runs a keyed, lossy transformation that feeds both detector and privacy evaluation. Neither mode is an anonymity guarantee.

### Local waveform preview

Waveforms are off by default. To enable the bounded, de-identified preview on your own machine only, set both flags before starting services:

```dotenv
# root .env, used by Docker/FastAPI
ENABLE_SIGNAL_PREVIEW=true

# frontend/.env.local
NEXT_PUBLIC_ENABLE_SIGNAL_PREVIEW=true
```

Rebuild the backend, restart `npm run dev`, and upload a new ZIP. Existing runs made while preview was disabled no longer retain the de-identified EDF. The viewer requests one 10-second window at a time and renders the 18 model channels; it never downloads the full recording. Do not enable this mode in a deployed app without authentication, authorization, and a reviewed retention policy.

## Routes

- `/upload` - choose an EEG ZIP, select a config-driven privacy method, and submit one analysis;
- `/dashboard` - monitor collapsed session cards and expand one only when its recordings are needed;
- `/sessions/[sessionId]` - inspect one uploaded ZIP and every safe EDF recording summary within it;
- `/results/[recordId]` - browse one recording’s bounded 18-channel EEG windows, dataset annotations, and separately labelled non-clinical development scores.

Session IDs start with `SES-`; recording-result IDs start with `REC-`. Opening a legacy `/results/SES-...` URL now redirects to the matching session page.

## Verification

```bash
npm run lint
npm run build
npm run test:e2e
```

The end-to-end suite checks desktop and mobile upload, empty, completed, error, navigation, and privacy-safe rendering states. Screenshots are written to `test-results/` during the visual checks.

## Reading order

1. `src/app/layout.tsx` - metadata and shell boundary;
2. `src/app/globals.css` - named visual tokens, focus, selection, motion, and shared controls;
3. `src/components/AppShell.tsx` and `src/components/NavLink.tsx` - workspace chrome and active navigation;
4. `src/components/UploadScreen.tsx` - the single-action submission flow;
5. `src/components/DashboardScreen.tsx` and `src/components/StatusBadge.tsx` - polling, filters, safe run rows, and states;
6. `src/components/ResultScreen.tsx`, `RecordingNavigator.tsx`, and `SignalScoreChart.tsx` - session-scoped result review and optional local score-window preview;
7. `src/lib/api.ts` and `src/lib/types.ts` - the replaceable data boundary and presentation types.

See the durable visual contract in [`DESIGN.md`](../DESIGN.md) and the source reference in [`apple/DESIGN.md`](../apple/DESIGN.md).
