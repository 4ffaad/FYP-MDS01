# Project documentation

Use [Project design](project-design.md) as the integrated description of how
MDS01 is built. It links to the detailed implementation guides below.

| Need to…                                                                            | Read                                                                               |
| ----------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Explain platforms, architecture, algorithms, models, APIs, and runtime requirements | [Project design](project-design.md)                                                |
| Understand goals and scope                                                          | [Project goal](project-goal.md)                                                    |
| Run and test the local app                                                          | [Setup](setup.md)                                                                  |
| Inspect the component and VEEG flow                                                 | [Architecture](architecture.md)                                                    |
| Edit the system architecture or VEEG workflow diagrams                             | [Draw.io sources and workflow](diagrams/README.md)                                 |
| Trace EEG parsing, processing, and storage                                          | [Backend guide](backend.md)                                                        |
| Start from zero and follow backend security and request flows                       | [Backend handover](backend-handover.md) · [backend file map](backend-file-map.md)  |
| Understand browser screens and behavior                                             | [Frontend guide](frontend.md), then [frontend instructions](../frontend/AGENTS.md) |
| Understand EEG findings and waveform display                                        | [Inference walkthrough](inference-walkthrough.md)                                  |
| Run or troubleshoot standalone VSViG                                                | [Video runbook](video-detection.md)                                                |
| Change visual styling                                                               | [Design rules](../DESIGN.md)                                                       |
| See remaining work                                                                  | [Current plan](../tasks/plan.md)                                                   |
| Prepare the final assessment report, draft RTM, code sample, and report diagrams   | [Final report package](final-report/README.md)                                     |

The implementation and tests are the source of truth for runtime behavior.
Model artifacts and contracts are local assets. All scores are research
outputs; they are not a diagnosis or proof of clinical accuracy.
