# Video privacy contract

This companion defines the resource, pipeline, output, API, and retention
rules for the standalone video privacy subsystem. It does not authorize a
clinical model or a claim that any output is anonymous.

## Privacy profiles

| Profile | Initial status | Output | Purpose |
| --- | --- | --- | --- |
| `pose-only` | Implement first | Encrypted normalized keypoints, confidence, relative timestamps, and quality flags | Remove RGB while retaining a derived motion representation |
| `face-redacted` | Implement as opt-in | Encrypted video with detected faces blurred or masked | Human review when visual context is required |

The profiles are independent branches over the same validated source. A user
may select either profile or both. They must not be chained implicitly.

Both branches first remove audio, subtitles/data streams, and copied metadata.
`face-redacted` must also check temporal face coverage, all visible people, and
background/linkage risks. Face redaction is a research derivative, not an
anonymity guarantee.

## Resource model

Use independent resources rather than extending `EEGRecording`:

- `VideoPrivacyJob`: opaque job ID, optional session link, lifecycle status,
  selected profiles, safe input summary, bounded safe error, and timestamps;
- `VideoPrivacyOutput`: opaque output ID, job reference, profile, output kind,
  status, quality flags, adapter/version metadata, safe output summary, and
  private encrypted artifact reference.

Original filenames, patient references, absolute paths, hashes, source
metadata, and encryption details are internal-only. Public serializers must
not expose them.

## Pipeline interface

The implementation should have one common orchestrator and a profile registry:

```python
class VideoPrivacyPipeline(Protocol):
    name: str
    output_kind: str

    def transform(
        self, source_path: Path, work_dir: Path, context: PrivacyContext
    ) -> PrivacyOutput: ...
```

The orchestrator owns validation, preflight stream/metadata scrubbing,
branch scheduling, output inspection, encryption, persistence, cleanup, and
safe errors. A pipeline owns only its privacy transform and quality checks.
There is no `ActionAnalysisAdapter` in this subsystem.

## Lifecycle

```text
staged → queued → validating → scrubbing → transforming → inspecting
  → completed
  ↘ completed_with_errors
  ↘ failed
```

Each selected profile gets an independent output status. One branch may fail
without publishing an unsafe artifact or changing a successful sibling branch.

Processing must:

1. validate content and configured resource limits, not only the filename;
2. inspect the container and create a temporary scrubbed input with audio,
   subtitles/data, and identifying metadata removed;
3. run every selected `VideoPrivacyPipeline` independently;
4. inspect each output for expected type, readable structure, coverage, and
   privacy-specific quality flags;
5. encrypt only approved outputs into private session/application storage; and
6. delete the source, decrypted input, frames, scrubbed input, and failed or
   unapproved outputs in success and failure cleanup paths.

## Output contracts

### `pose-only`

The private artifact contains derived, relative motion data only:

```json
{
  "schema_version": "pose-0.1",
  "pipeline": {"name": "pose-only", "version": "reviewed-runtime"},
  "frames": [
    {
      "t_ms": 0,
      "landmarks": [{"x": 0.5, "y": 0.4, "z": 0.0, "confidence": 0.98}],
      "quality_flags": []
    }
  ]
}
```

The landmark count and adapter metadata come from the selected privacy runtime
contract. Do not store RGB pixels, face crops, audio, subtitles, absolute
wall-clock timestamps, or original container metadata. Pose data can still
leak identity and remains encrypted/private.

### `face-redacted`

The output is a review derivative with no audio, subtitles/data streams, or
copied metadata. Every detected face must be blurred or masked consistently
across the clip. Missed detection, tracking gaps, extra people, or output
inspection failures must prevent retention unless an approved policy says the
output is only a failed artifact for internal testing.

The public API returns output status and safe summary only. It does not expose a
source-media URL. Any future preview/download route needs an explicit local
review authorization and retention policy.

## API boundary

Add video-privacy routes while leaving the EEG routes unchanged:

```text
POST /api/video-privacy/drafts
GET  /api/video-privacy/drafts/{draft_id}
POST /api/video-privacy/drafts/{draft_id}/finalize
DELETE /api/video-privacy/drafts/{draft_id}
GET  /api/video-privacy/jobs/{job_id}
GET  /api/video-privacy/jobs/{job_id}/outputs
GET  /api/video-privacy/outputs/{output_id}
DELETE /api/video-privacy/jobs/{job_id}
```

The draft endpoint encrypts a supported video upload and returns an opaque
expiring draft ID. Finalization receives a list of selected profile names,
returns `202`, and schedules the privacy job with `BackgroundTasks`. Public
responses contain only generated IDs, profile/output kind, status, safe
technical summary, quality flags, and bounded errors.

The frontend should consume these routes through `frontend/src/lib/api.ts`
and render a dedicated Video Privacy page. It should let the user select
profiles, show one output card per branch, display a research-only warning, and
never construct media URLs from storage paths.

## Dependency and retention boundary

Keep MediaPipe/OpenCV/FFmpeg handling inside privacy services and pipeline
adapters. The EEG H5 loader and its `(N, 1024, 18)` contract remain untouched.

Use private encrypted storage for drafts and approved outputs. Apply the
configured retention policy after every terminal state. The default behavior
never retains the original video as a normal result; it retains only approved
derived outputs and safe job metadata.
