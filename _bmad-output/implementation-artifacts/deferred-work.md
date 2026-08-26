# Deferred work

- source_spec: `_bmad-output/implementation-artifacts/spec-video-privacy-vertical-slice.md`
  summary: Add per-user or per-tenant ownership checks to video jobs and media endpoints before multi-user deployment.
  evidence: The approved v1 model has opaque job IDs and protected API authentication but no owner field; the current prototype is local/single-workspace and any authenticated caller could enumerate jobs.

- source_spec: `_bmad-output/implementation-artifacts/spec-video-privacy-vertical-slice.md`
  summary: Replace in-process video BackgroundTasks with durable job claiming, retry recovery, and bounded video concurrency.
  evidence: The approved architecture explicitly uses FastAPI BackgroundTasks for the prototype; duplicate workers, restarts, and CPU-heavy parallel video transforms are not addressed by this slice.

- source_spec: `_bmad-output/implementation-artifacts/spec-video-privacy-vertical-slice.md`
  summary: Add a scheduled retention sweeper and explicit operator erasure endpoint.
  evidence: Retained encrypted artifacts are deleted when an expired job is read, but an idle expired job has no periodic cleanup trigger or user-requested deletion route.

- source_spec: `_bmad-output/implementation-artifacts/spec-video-privacy-vertical-slice.md`
  summary: Run real OpenCV/MediaPipe processor and PostgreSQL/Alembic integration tests in the research-enabled container.
  evidence: Local tests use a fake processor and SQLite metadata setup because the host Python environment lacks the optional runtimes; Docker was not available during this verification pass.

- source_spec: `_bmad-output/implementation-artifacts/spec-video-privacy-vertical-slice.md`
  summary: Add identity and policy-version audit fields to quality-caveat acknowledgement.
  evidence: v1 records only an acknowledgement timestamp; authenticated reviewer identity and the accepted privacy-policy version are not part of the approved persistence contract.

- source_spec: `_bmad-output/implementation-artifacts/spec-video-privacy-vertical-slice.md`
  summary: Verify authenticated cross-origin preview and download behavior behind the production Cloudflare Access deployment.
  evidence: The browser surface uses protected media URLs; local E2E runs in stub mode and cannot validate cookie/auth behavior for streamed media assets.
