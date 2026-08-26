# Repository handoff

## What this repository contains

- FastAPI/PostgreSQL EEG research backend under `backend/`;
- Next.js research frontend under `frontend/`;
- project guidance in `AGENTS.md` and `docs/`;
- checked-in BMad workflows under `_bmad/` and `.agents/skills/`;
- BMad planning/specification artifacts under `_bmad-output/`.

The patient-video privacy feature is specified but not yet implemented. Its
contract is the video-only flow:

```text
video → selected privacy pipeline(s) → encrypted output → cleanup
```

It must remain separate from EEG/H5 inference.

## Keep in Git

Source code, migrations, tests, documentation, model-contract metadata, BMad
configuration/workflows, sanitized environment templates, and reproducible
package lock files belong in the repository.

## Keep local-only

Never commit `.env`, frontend `.env.local`, patient videos, RAR archives, EEG
datasets, storage files, generated reports, SHAP backgrounds, `.DS_Store`,
build output, or private keys. Keep real patient data outside the repository,
for example under `/Users/daffa/PrivatePatientData/`.

The ignore rules are a safety net, not permission to place sensitive data in
the repository. Check `git status --short` before every commit.

## Handoff verification

From the repository root:

```bash
git diff --check
PYTHONPATH=. .venv/bin/python -m unittest discover -s backend/tests -v
PYTHONPATH=. .venv/bin/python -m compileall -q backend
cd frontend && npm run lint && npm run build && npm run test:e2e
```

Before public deployment, configure Cloudflare Access, rotate any historical
secrets, review legacy local storage, and address the remaining items in
[`security-audit.md`](security-audit.md).
