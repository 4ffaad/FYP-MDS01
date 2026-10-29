# Hiring Loop Checklist — Steps A Candidate Walks Through (Infographic)

**Best for**: an internal checklist that keeps every candidate on the same loop
**Avoid when**: the steps are time-ordered with dates (use a timeline)
**Answers**: what happens in the hiring loop, in order, and what each step needs from the team

```infographic
infographic list-zigzag-up-simple
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
  title Interview Loop — Backend Engineer
  desc Four steps, each with a named owner
  lists
    - label Intake call
      desc Recruiter — 30 minutes
    - label Work sample
      desc Paid, two hours, reviewed blind
    - label Panel
      desc Two engineers plus a partner team
    - label Debrief
      desc Decision within 24 hours
```

## Data Shape

Four to six `lists` items in execution order. Zigzag layouts stagger items vertically, so keep labels short
and move constraints (duration, owner) into `desc`.

## Key Options

| Option | Effect |
|---|---|
| `infographic list-zigzag-up-simple` | Steps climb in a zigzag; reads as a path |
| `list-zigzag-down-compact-card` | Descending variant with denser cards |
| `sequence-steps-*` | Use when the order is contractual rather than procedural |

## Pitfalls

- ❌ Owners left out → ✅ every step without an owner becomes a scheduling accident
- ❌ Seven steps → ✅ loops longer than six steps reliably lose candidates
- ❌ Using zigzag for unordered lists → ✅ the shape implies progression; keep it honest

## Alternatives

| Variant | Use instead |
|---|---|
| Candidate experience over time | `customer-onboarding-journey.md` |
| Compliance evidence collection | `compliance-evidence-zigzag.md` |
| Hiring plan by quarter | `hiring-plan-roadmap.md` |

<!-- source: AntV Infographic syntax docs + template list (`list-zigzag-up-simple`) -->
