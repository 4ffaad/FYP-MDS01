# Current project plan

**Last reviewed: 2026-10-27**

The implementation and technical design are documented in
[Project design](../docs/project-design.md). Completed feature checklists have
been consolidated; this file tracks current handover and validation work.

## Current state

- The local prototype supports EEG-only, combined EEG/video review, and a
  separate video-analysis workflow.
- EEG source review uses a 12-second clinical-style page and preserves source
  timing gaps. H5 inference follows the reviewed 18-channel tensor contract.
- Combined reference playback is independent of OpenPose/VSViG and uses
  conservative metadata synchronization. New reference-video upload returns
  after encrypted retention; a background metadata probe queues preparation for
  unsupported browser formats.
- Retained clinical files are encrypted outside PostgreSQL; API reads are
  authenticated, owner-scoped, and private/no-store.
- Verification repeated on 2026-10-27: backend suite 490 passed / 6 skipped;
  selected desktop Playwright waveform and VSViG-result display tests passed.
  The Playwright fixtures use synthetic API data. Docker/PostgreSQL and a
  TensorFlow runtime were unavailable, so this run did not exercise a live
  H5 inference or real HUKM case.

## Remaining work

1. **Finish assessment handover.** Review the [final report package](../docs/final-report/README.md), confirm authorship and AI-use disclosure, and have the team and supervisor review the draft RTM.
2. **Repeat a live selected-case acceptance run** when Docker and approved local data are available. Check owner upload, encrypted retention, waveform navigation, video popup, and source-clock correspondence; do not process the full patient collection.
3. **Correct conversion status language.** The current worker queues unsupported-format playback preparation after the background metadata probe, before popup open; opening can prioritize it. Align the UI and all documentation with this behavior or change the service if the product decision becomes on-open-only conversion.
4. **Complete deployment hardening before network exposure.** Configure HTTPS, decide whether clinician roles are required, document key rotation, and exercise backup/restore with encrypted files and database state.
5. **Keep research claims bounded.** Validate H5 and VSViG with approved assets and datasets. HUKM pose failures remain preprocessing outcomes, not seizure findings; model scores are not clinical probabilities.

## Next project phase

Hand over the code, diagrams, report, test evidence, and unresolved requirements to
the research assistants and successor team. Use `docs/project-design.md` as the
source of truth for platforms, architecture, algorithms, model contracts, APIs,
privacy boundaries, runtime needs, tests, and limitations.
