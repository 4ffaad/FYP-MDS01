# Certification Study Roadmap — Quarters Of Preparation (Infographic)

**Best for**: a personal or team study plan milled to quarter markers
**Avoid when**: the exam date is fixed and study weeks matter (use a timeline)
**Answers**: what is studied each quarter, and when practice exams start

```infographic
infographic sequence-roadmap-vertical-quarter-simple-card
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
  title Security Certification Path
  desc Four quarters from fundamentals to exam
  sequences
    - label Q1 — Fundamentals
      desc Networking and identity basics
    - label Q2 — Core domain
      desc Threat modelling and controls
    - label Q3 — Practice
      desc Two mock exams, review gaps
    - label Q4 — Exam
      desc Booked for the second week
```

## Data Shape

`sequences` with quarter markers in the label. This variant draws quarter shapes, so exactly four items read
as a year; fewer items look like a fragment.

## Key Options

| Option | Effect |
|---|---|
| `infographic sequence-roadmap-vertical-quarter-simple-card` | Quarter-styled vertical cards |
| `sequence-roadmap-vertical-plain-text` | Text-only variant for study logs |
| `sequence-ascending-steps` | Use when the story is skill levels, not a calendar |

## Pitfalls

- ❌ Practice left to the end → ✅ schedule mocks in Q3 so there is time to fix gaps
- ❌ No exam date → ✅ a roadmap without a booking is a wish
- ❌ Three quarters → ✅ the layout expects four; trim to two topics instead

## Alternatives

| Variant | Use instead |
|---|---|
| Engineer level progression | `engineer-skill-progression.md` |
| Certification for a whole team | `hiring-plan-roadmap.md` |
| Study plan as ordered steps | `incident-response-runbook.md` |

<!-- source: AntV Infographic syntax docs + template list (`sequence-roadmap-vertical-quarter-simple-card`) -->
