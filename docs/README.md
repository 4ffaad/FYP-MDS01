# Read this first

If you only need to understand the project, read [EEG and video inference](inference-walkthrough.md). It explains the two model paths in plain language.

| Need to… | Read |
| --- | --- |
| Run or test the local Docker app | [Setup](setup.md) |
| See how the parts fit together | [Architecture](architecture.md) |
| Change or trace backend behavior | [Backend guide](backend.md) |
| Change the browser app | [Frontend guide](frontend.md), then [frontend instructions](../frontend/AGENTS.md) |
| Run or troubleshoot VSViG video inference | [Video runbook](video-detection.md) |
| Change visual styling | [Design rules](../DESIGN.md) |

## What to trust

Runtime behavior comes from the code and tests. The EEG model contract and
artifact must be reviewed and mounted locally. The video source, checkpoints,
and preprocessing contract are pinned in the [video runbook](video-detection.md).
All outputs are for research review; they are not a diagnosis or proof of
clinical accuracy or anonymity.
