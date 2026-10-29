# Incident Response Runbook — First Fifteen Minutes (Infographic)

**Best for**: the top of an on-call runbook, read under pressure
**Avoid when**: the flow branches on severity (use the escalation path diagram alongside)
**Answers**: what to do, in order, from the moment an alert fires

```infographic
infographic sequence-steps-simple
theme
  colorPrimary #2b66c4
  palette
    - #2b66c4
    - #2f9e44
    - #f3a33c
    - #d1242f
    - #7048e8
    - #0f9b9b
    - #c16f8a
    - #7c5a3d
data
  title Incident Response — First 15 Minutes
  desc One action per step, no branching
  sequences
    - label Acknowledge
      desc Claim the page within 5 minutes
    - label Assess
      desc Check dashboards and error budget burn
    - label Declare
      desc Open the incident channel, set severity
    - label Mitigate
      desc Roll back or fail over, then verify
    - label Communicate
      desc Status page update within 30 minutes
```

## Data Shape

`sequences` with one imperative per step. Ordered by construction, so write the steps in the order they must
be performed — no `order` key needed.

## Key Options

| Option | Effect |
|---|---|
| `infographic sequence-steps-simple` | Plain numbered steps |
| `sequence-steps-badge-card` | Badge steps; heavier, easier to follow on a wall display |
| `sequence-timeline-*` | Use when the steps have clock times rather than a fixed order |

## Pitfalls

- ❌ Steps that bundle two actions ("Assess and declare") → ✅ one verb per step
- ❌ More than six steps → ✅ the first fifteen minutes has five or six actions, not a procedure
- ❌ Detail that belongs in the wiki → ✅ link out; this is the emergency extract

## Alternatives

| Variant | Use instead |
|---|---|
| Who takes over when it continues | `incident-escalation-path.md` |
| Change window steps with timings | `migration-cutover-window.md` |
| Handover between shifts | `support-shift-handover.md` |

<!-- source: AntV Infographic syntax docs + template list (`sequence-steps-simple`) -->
