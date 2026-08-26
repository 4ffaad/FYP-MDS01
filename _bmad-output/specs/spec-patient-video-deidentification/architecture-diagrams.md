# Architecture diagrams

## Standalone video privacy flow

```mermaid
flowchart TD
    Upload[POST /api/video-privacy/drafts] --> Encrypt[Encrypted private draft]
    Encrypt --> Finalize[Finalize with selected profiles]
    Finalize --> Queue[202 + FastAPI BackgroundTasks]
    Queue --> Validate[Validate container, limits, streams]
    Validate --> Scrub[Remove audio, subtitles, data, and metadata]
    Scrub --> Fanout{Privacy pipeline registry}
    Fanout --> Pose[pose-only<br/>derived keypoint output]
    Fanout --> Face[face-redacted<br/>review video output]
    Pose --> InspectPose[Inspect pose coverage/schema]
    Face --> InspectFace[Inspect face coverage/output]
    InspectPose --> Store[Encrypt approved outputs]
    InspectFace --> Store
    Store --> Cleanup[Delete source and transient material]
    Cleanup --> Results[Safe job/output API]
    Results --> UI[Dedicated Video Privacy UI]
```

## System boundary

```mermaid
flowchart LR
    Job[VideoPrivacyJob] --> Orchestrator[Video privacy service]
    Orchestrator --> Registry[Pipeline registry]
    Registry --> Pose[Pose privacy pipeline]
    Registry --> Face[Face redaction pipeline]
    Orchestrator --> Repo[Video privacy repository]
    Orchestrator --> Storage[Encrypted private storage]
    Repo --> DB[(PostgreSQL metadata)]
    Orchestrator -. no call .-> EEG[EEG processing]
    Orchestrator -. no call .-> H5[H5/model runtime]
    Orchestrator -. no call .-> Action[Action analysis]
```

The public boundary is the safe job/output summary. The private boundary holds
encrypted drafts and approved derivatives only; it never turns the filesystem
into a public media endpoint.
