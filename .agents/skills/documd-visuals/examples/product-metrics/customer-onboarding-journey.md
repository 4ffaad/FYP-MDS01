# Onboarding Snake — Multi-Step Journey (Infographic)

**Best for**: a longer but still single-threaded process where a straight timeline would feel too flat or too tall
**Avoid when**: the steps branch, loop heavily, or need formal workflow semantics
**Answers**: what the onboarding sequence is, and how the reader should progress through it stage by stage

```infographic
infographic sequence-snake-steps-simple
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
  title Customer Onboarding Flow
  desc Six sequential steps from signup to productive usage
  sequences
    - label Sign Up
      desc Account created
    - label Verify Identity
      desc Email and tenant confirmed
    - label Configure Workspace
      desc Core settings applied
    - label Connect Systems
      desc APIs and data sources linked
    - label Invite Team
      desc Roles and access assigned
    - label Go Live
      desc First real workflow enabled
```

## Data Shape

Use an ordered `sequences` list with short labels and one-line descriptions for each step.

## Key Options

| Option | Effect |
|---|---|
| `sequence-snake-steps-simple` | Bends a longer sequence into a compact path |
| Ordered `sequences` | Preserves the step-by-step journey |
| Short `desc` values | Adds context without overloading the shape |

## Pitfalls

- ❌ Treating a branching flow as one snake path → ✅ this layout is still linear, even if visually playful
- ❌ Very long text on each step → ✅ the path shape only works when step copy stays short
- ❌ Using it for only two or three steps → ✅ simpler timeline or row layouts are often clearer |

## Alternatives

| Variant | Use instead |
|---|---|
| Straight milestone sequence | `platform-milestone-timeline.md` |
| Roadmap phases | `product-roadmap-sequence.md` |
| Formal workflow | PlantUML swimlane or activity examples |

<!-- source: AntV Infographic template reference (`sequence-snake-steps-simple`) + syntax docs for sequences -->