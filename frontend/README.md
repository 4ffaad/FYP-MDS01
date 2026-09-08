# MDS01 frontend

Next.js interface for separate EEG analysis and video privacy workflows.
From this directory, after completing [root setup](../docs/setup.md):

```sh
npm ci
npm run dev
```

- [Screens, API adapter and privacy behavior](../docs/frontend.md)
- [Architecture](../docs/architecture.md)
- [Design rules](../DESIGN.md)
- [Testing](../docs/setup.md#tests)

`NEXT_PUBLIC_USE_API_STUB=true` enables synthetic browser-only data for UI work. The normal default is the real FastAPI adapter. Public frontend variables must never contain secrets.
