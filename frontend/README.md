# Frontend

Next.js interface for the EEG/video workspace. Start the application using the
[root setup](../docs/setup.md). For standalone browser development:

```sh
npm ci
npm run dev
```

Read [the frontend guide](../docs/frontend.md), [design rules](../DESIGN.md),
and [frontend instructions](AGENTS.md) before changing the UI.

The browser uses the backend's HttpOnly session cookie. Set
NEXT_PUBLIC_USE_API_STUB=true only for synthetic UI tests; it does not run
real EEG or video inference. Never put secrets in NEXT_PUBLIC_* variables.
