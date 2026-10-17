# Current project plan

**Last reviewed: 2026-10-17**

The implementation and technical design are documented in
[Project design](../docs/project-design.md). Completed feature checklists have
been consolidated; this file tracks only current follow-up work.

## Current state

- The local prototype supports EEG-only, combined EEG/video, and separate
  video-analysis workflows.
- EEG source review uses a 12-second clinical-style page and preserves source
  timing gaps. H5 inference uses the fixed reviewed tensor contract.
- Combined reference playback is independent of OpenPose/VSViG and uses
  conservative metadata synchronization. Generated local setup enables
  owner-only reference review.
- Retained clinical files are encrypted outside PostgreSQL; API reads are
  authenticated, owner-scoped, and private/no-store.
- Verification for this cleanup: backend unit suite 476 passed / 7 skipped;
  frontend lint, format, Next type generation, TypeScript, and production build
  passed; Playwright API-stub suite 130 passed / 64 skipped; setup tests 7
  passed. These checks do not establish live PostgreSQL behavior or clinical
  model performance.

## Remaining work

1. **Repeat the selected-case live acceptance run after this cleanup.** When
   Docker is available, verify the owner's combined upload, protected
   original/review media, EEG page navigation, and shared playback clock in
   the browser. Do not process the entire patient collection for this check.
2. **Complete deployment hardening before any network exposure.** Configure
   HTTPS, decide whether clinician roles are required, document key rotation,
   and exercise backup/restore with encrypted files and database state.
3. **Keep research claims bounded.** Validate the H5 and VSViG contracts with
   their separately approved datasets and assets. HUKM pose failures remain
   preprocessing outcomes, not seizure findings; the demo does not support a
   clinical-accuracy claim.

## Next project phase

Use `docs/project-design.md` as the source of truth for the Project
Design write-up: platforms, architecture, algorithms, models, API groups,
privacy boundaries, runtime requirements, tests, and limitations. Do not copy
old checkpoint notes into the report as current behavior.
