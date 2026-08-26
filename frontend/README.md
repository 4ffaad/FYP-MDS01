# MDS01 frontend

Next.js research interface for uploading EEG archives, monitoring sessions,
and reviewing safe model-result summaries. It does not render patient
references, original filenames, private paths, or raw source files by default.

## Run locally

Start the backend from the repository root, then run:

```bash
npm install
cp .env.example .env.local
npm run dev
```

Open <http://127.0.0.1:3000>. The real FastAPI adapter uses:

```dotenv
NEXT_PUBLIC_USE_API_STUB=false
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

Set `NEXT_PUBLIC_USE_API_STUB=true` only for isolated UI work or the stub
Playwright suite.

## Product routes

- `/upload` — stage an EEG ZIP and select its research privacy profile;
- `/dashboard` — monitor sessions and processing states;
- `/sessions/[sessionId]` — inspect safe recording summaries;
- `/results/[recordId]` — review the score timeline and research-only result.

Patient-video privacy is not wired into the frontend yet. Its implementation
contract is in
[`_bmad-output/specs/spec-patient-video-deidentification/`](../_bmad-output/specs/spec-patient-video-deidentification/).

## Verification

```bash
npm run lint
npm run build
npm run test:e2e
```

The real end-to-end workflow is available with:

```bash
npm run test:e2e:real
```

See [`docs/frontend.md`](../docs/frontend.md) for the component/data-boundary
guide and [`DESIGN.md`](../DESIGN.md) for the visual contract.
