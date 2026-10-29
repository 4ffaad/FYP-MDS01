# Backend architecture and security

MDS01 is a local research prototype with a Next.js browser, a FastAPI backend,
relational metadata storage, and private encrypted file storage. The combined
EEG/VEEG review path and standalone VSViG experiment are separate workflows.

The login diagram shows local-account mode. Read each sequence from top to
bottom. Solid arrows show requests or
work; dashed arrows show replies. The [backend handover](backend-handover.md)
explains startup, and the [file map](backend-file-map.md) locates each module.

## 1. Login and session security

```mermaid
%%{init: {"theme":"base","themeVariables":{"actorBkg":"#d5e8d4","actorBorder":"#82b366","activationBkgColor":"#278744","activationBorderColor":"#278744"}}}%%
sequenceDiagram
    actor User
    participant UI as Next.js interface
    participant Auth as FastAPI authentication
    participant DB as PostgreSQL

    User->>UI: Enter email and password
    UI->>+Auth: POST /api/auth/login
    Auth->>Auth: Check origin and login rate limit
    Auth->>+DB: Look up active account
    DB-->>-Auth: Account and salted password hash
    Auth->>Auth: Verify password with scrypt
    alt Valid credentials
        Auth->>DB: Save session token hash and expiry
        Auth-->>UI: Success and HttpOnly session cookie
        UI-->>User: Open workspace
    else Invalid credentials
        Auth-->>UI: 401 with generic credential error
        UI-->>User: Display sign-in error
    end
    deactivate Auth
```

Passwords use **salted scrypt hashes**. Only a **SHA-256 hash** of the random
session token is persisted; the raw token goes in the browser cookie. The
cookie uses `HttpOnly` and `SameSite=Lax`; `Secure` is set for HTTPS requests.
Expired or revoked sessions cannot authorize private reads. Session expiry
does not delete retained recordings.

## 2. EEG upload, encryption, and H5 processing

```mermaid
%%{init: {"theme":"base","themeVariables":{"actorBkg":"#d5e8d4","actorBorder":"#82b366","activationBkgColor":"#278744","activationBorderColor":"#278744"}}}%%
sequenceDiagram
    participant UI as Next.js interface
    participant API as FastAPI routes
    participant Worker as EEG processing service
    participant H5 as H5 model
    participant Store as Storage service and private files
    participant DB as PostgreSQL

    UI->>API: Upload ZIP, then finalize draft
    API->>DB: Validate session and owner context
    DB-->>API: Authenticated account and case
    API->>Store: Encrypt ZIP before file persistence
    Note over Store: AES-256-GCM with runtime storage key
    API->>Worker: Schedule background processing
    API-->>UI: Session ID and processing status
    activate Worker
    Worker->>Store: Temporarily decrypt archive, retain encrypted sources
    Store-->>Worker: Private working files
    Worker->>Worker: Validate, de-identify model metadata, preprocess
    Worker->>+H5: Validated float32 tensor
    Note over H5: 256 Hz, 18 bipolar channels, 4-second windows
    H5-->>-Worker: Timestamped research scores
    Worker->>DB: Save scores and processing state
    Worker->>Store: Remove temporary plaintext, keep encrypted sources
    deactivate Worker
```

H5 receives normal numeric model input. Encryption protects retained files;
the complete source waveform is kept separately for clinical review. EEG
scores are structured database rows, rather than encrypted model tensors.

## 3. Standalone video and encrypted VSViG results

```mermaid
%%{init: {"theme":"base","themeVariables":{"actorBkg":"#d5e8d4","actorBorder":"#82b366","activationBkgColor":"#278744","activationBorderColor":"#278744"}}}%%
sequenceDiagram
    participant UI as Next.js interface
    participant API as FastAPI routes
    participant Video as Video service
    participant Model as OpenPose and VSViG
    participant Store as Storage service and private files
    participant DB as PostgreSQL

    UI->>API: Upload standalone video with session cookie
    API->>DB: Validate session and case owner
    API->>Video: Create owner-scoped job
    Video->>Store: Encrypt original before file persistence
    Video->>Store: Temporarily decrypt for admission checks
    Store-->>Video: Private admission input
    Video->>Video: Check format and pose readiness privately
    Video->>Store: Remove admission plaintext
    alt Input fails admission
        Video->>DB: Save failure reason, no model score
        Video-->>API: Admission outcome
        API-->>UI: Display preprocessing issue
    else Input passes admission
        Video-->>API: Admitted job
        API->>Video: Schedule standalone processing
        API-->>UI: Queued job ID
        Video->>Store: Temporarily decrypt model input
        Store-->>Video: Private working source
        Video->>+Model: Pose tracks and required RGB patches
        Model-->>-Video: Research scores and Grad-CAM evidence
        Video->>DB: Save AES-GCM encrypted result payload
        Video->>Store: Encrypt review media, remove temporary files
    end
```

New video files use independently authenticated encryption chunks. VSViG
result ciphertext is bound to its owner and job. Models operate on temporary
plaintext inputs; working frames and patches are removed after use.

## 4. Owner-authorized review and decryption

```mermaid
%%{init: {"theme":"base","themeVariables":{"actorBkg":"#d5e8d4","actorBorder":"#82b366","activationBkgColor":"#278744","activationBorderColor":"#278744"}}}%%
sequenceDiagram
    participant UI as Next.js interface
    participant API as FastAPI protected routes
    participant DB as PostgreSQL
    participant Store as Storage service and private files

    UI->>+API: Request waveform, video, result, or download
    API->>DB: Validate session and look up resource by owner
    DB-->>API: Authorization result
    alt Invalid or expired session
        API-->>UI: 401, do not decrypt
    else Resource is absent or belongs to another account
        API-->>UI: 404, do not decrypt
    else Owner is authorized
        alt Waveform, media, or original download
            API->>Store: Authenticate and decrypt protected content
            Note over Store: Video ranges use encrypted chunks, EEG source reads use temporary files
            Store-->>API: Requested bytes or waveform interval
            Note over Store: Remove temporary plaintext after use
        else Encrypted VSViG result
            DB-->>API: Encrypted result payload
            API->>API: Authenticate ciphertext and decrypt result
        end
        API->>DB: Record minimal access event where implemented
        API-->>UI: Private, no-store response
    end
    deactivate API
```

Every video-range request repeats the owner check. Private filesystem paths
are not returned to the browser. Legacy monolithic media may use a private
temporary plaintext cache; new chunked media decrypts only the required chunks.

## Where the security code lives

| Protection | Main implementation |
| --- | --- |
| Password hashing, session creation, expiry | [auth_service.py](../backend/app/services/auth_service.py) |
| Login endpoint and cookie settings | [auth.py](../backend/app/api/auth.py) |
| Authentication and write-origin checks | [security.py](../backend/app/core/security.py) |
| Owner-filtered database lookups | [repository.py](../backend/app/database/repository.py), [video_detection_repository.py](../backend/app/database/video_detection_repository.py) |
| File encryption, integrity, private temporary files | [storage_service.py](../backend/app/services/storage_service.py), [video_storage_service.py](../backend/app/services/video_storage_service.py) |
| EEG processing and cleanup | [processing_service.py](../backend/app/services/processing_service.py) |
| Video admission, encrypted results, reference preparation | [video_detection_service.py](../backend/app/services/video_detection_service.py) |
| Runtime encryption-key validation | [crypto.py](../backend/app/privacy/crypto.py) |

`MDS01_STORAGE_KEY` supplies **32 decoded bytes** through the backend runtime
environment. It is kept in ignored local configuration, outside Git and
PostgreSQL, and is never sent to the browser. AES-GCM uses fresh nonces and
authenticates encrypted content before release.

Selected patient fields, observations, synchronization anchors, and new VSViG
result payloads have application encryption. Ordinary job metadata and EEG
scores remain structured rows; this is not whole-database encryption.
New originals, review media, and results remain until owner case deletion.
Deletion removes linked rows and artifacts and is blocked while processing
is active. Audit entries avoid patient labels and request bodies.

## VEEG workflow

Combined clinical reference playback is separate from standalone video
analysis. It never requires pose readiness or VSViG inference.
Generated local setup enables MDS01_CLINICAL_VIDEO_REVIEW_ENABLED for owner-only
review; a backend with no explicit value defaults to disabled. The review popup
opens only when the user asks for it. Combined uploads encrypt and retain the
original, then acknowledge without blocking on media probing or video AI. A
restart-recoverable background worker checks the source clock and format and
refreshes matching. Compatible H.264 MP4 streams from authenticated encrypted
byte ranges. An unsupported clip is converted only after the owner opens its
popup; the encrypted original remains retained. This format preparation does
not run OpenPose or VSViG. A verified clip follows the EEG source clock, which
holds during video buffering and never gets reset by routine video time updates.
Genuine acquisition gaps stay visible, and unmatched clips are not presented as
synchronized.

## Boundaries and constraints

- Routes validate requests and return safe responses. Services own workflows;
  repositories own database queries.
- PostgreSQL stores structured state, safe metadata, and results. Recording
  binaries remain in private encrypted file storage.
- Background work runs inside the API process. It is suitable for this local
  prototype, but it is not a durable distributed job queue.
- Access is uploader-only. Local Compose binds to loopback; external hosting,
  HTTPS termination, institution-managed identity, key rotation, and verified
  backup recovery are separate deployment work.

For local startup, see [setup](setup.md). For code locations and implementation
details, see the [backend guide](backend.md), [frontend guide](frontend.md), and
[video runbook](video-detection.md).
