# Privacy-pipeline evaluation plan

The output is a research risk-reduction profile. It must not be described as
anonymous until the intended release context, attacker model, and results have
been reviewed.

## Test fixture

Use synthetic or consented clips with known duration, frame rate, subject
count, planted metadata/stream edge cases, and representative face/pose
coverage. Do not commit patient-identifying fixtures to the repository.

## Profile-specific checks

| Profile | Required evidence |
| --- | --- |
| `pose-only` | Landmark coverage, timestamp continuity, tracking gaps, person re-identification, sensitive-attribute inference, cross-clip linkage, and body/motion leakage review |
| `face-redacted` | Face detection/coverage over time, missed-face rate, multi-person handling, output readability, background/text/clothing linkage review, and human visual review |
| Common preflight | Audio, subtitle/data stream, container metadata, background text, and transient-file removal checks |

No action-recognition utility score belongs in this subsystem. If action
utility is studied later, it consumes a privacy output as a separate research
experiment and does not become part of the privacy job.

## Acceptance gates

1. Unit and integration tests prove source media and transient artifacts are
   removed on successful and failed paths.
2. API tests prove public responses contain no patient references, original
   names, paths, hashes, source media, or complete pose artifacts.
3. Pipeline-registry tests prove profile selection is explicit, branches are
   independent, and no EEG/H5/model service is called.
4. Output tests prove each profile emits the declared type and schema, and
   common stream/metadata scrubbing is applied.
5. Failure tests prove unsupported, corrupt, unsafe-stream, missing-coverage,
   and multi-person cases fail closed.
6. A research report marks every privacy check as measured, unmeasured, or
   blocked by an open question. It must not claim anonymity from encryption,
   face redaction, pose extraction, or a development runtime.

## Later changes

Learned anonymizers, silhouette transforms, and stronger multi-person handling
require their own pipeline contract and evaluation evidence. They must be
added as new registry entries, not hidden branches inside an existing profile.
