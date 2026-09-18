# MDS01 frontend

Next.js interface for the shared EEG/video analysis workspace and the separate
video privacy workflow.
From this directory, after completing [root setup](../docs/setup.md):

```sh
npm ci
npm run dev
```

If Next reports `Can't resolve '@hugeicons/core-free-icons'` after changing
frontend dependencies, stop the existing `npm run dev` process, run `npm ci`
from this directory, and start it again. Turbopack can cache a transient module
resolution failure if `node_modules` is changed while it is compiling.

- [Screens, API adapter and privacy behavior](../docs/frontend.md)
- [Video seizure review setup and model contract](../docs/video-detection.md)
- [Architecture](../docs/architecture.md)
- [Design rules](../DESIGN.md)
- [Testing](../docs/setup.md#tests)

`NEXT_PUBLIC_USE_API_STUB=true` enables synthetic browser-only data for UI work. The normal default is the real FastAPI adapter. Public frontend variables must never contain secrets.

With the normal adapter, set `NEXT_PUBLIC_AUTH_MODE=backend` and start the
backend in `AUTH_MODE=local-accounts`; the first visit opens `/login`. The
backend owns the HttpOnly session cookie. The Playwright stub suite sets
`NEXT_PUBLIC_AUTH_MODE=stub` explicitly so it can exercise screens without an
API.
