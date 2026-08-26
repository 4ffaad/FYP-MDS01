# Research brief

**Topic:** Privacy-preserving patient video de-identification for MDS01

**Decision:** Choose an initial patient-video representation and integration
approach that preserves required action-analysis utility while minimizing
identity leakage.

**Shape:** Explore, with an explicit comparison between:

- redacted RGB video, such as face/person masking or blurring;
- pose/keypoint or skeleton-only representations;
- learned spatio-temporal anonymization and privacy-preserving action
  recognition.

**Dimensions:**

1. Landscape and maturity: what approaches exist, what privacy properties they
   actually target, and which risks remain.
2. Integration and architecture: how video decoding, metadata/audio removal,
   face/pose inference, derived artifact storage, and action analysis compose.
3. Implementation reality: practical Python/tooling choices, model/runtime
   burden, temporal consistency, and evaluation requirements.

**Decision constraints from the repository:** video must remain outside
PostgreSQL; transient originals must be deleted; public API responses must
contain only safe result data; long-running work belongs in the existing
processing service and BackgroundTasks flow. These constraints shape the
integration questions and are not research evidence.

**Source rule:** Prefer original papers, regulator guidance, and official
tooling documentation. Treat face blurring, pose data, and learned
anonymization as privacy-risk reduction candidates, not automatic anonymity
guarantees.
