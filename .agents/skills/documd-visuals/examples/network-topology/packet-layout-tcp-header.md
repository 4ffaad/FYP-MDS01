# Packet / Frame Layout (packetdiag)

**Best for**: protocol and binary format documentation — which bits live where, and how wide each field is
**Avoid when**: the reader needs packet *flow* (use a sequence diagram) or a value-level trace
**Answers**: the exact layout of a wire format, field by field, at bit granularity

```plantuml
@startpacketdiag
title TCP Segment Header — Field Layout
colwidth = 32
node_height = 72

0-15: Source Port
16-31: Destination Port
32-63: Sequence Number
64-95: Acknowledgment Number
96-99: Data Offset
100-105: Reserved
106: URG
107: ACK
108: PSH
109: RST
110: SYN
111: FIN
112-127: Window
128-143: Checksum
144-159: Urgent Pointer
160-191: Options and Padding
192-223: data
@endpacketdiag
```

## Key Options

| Syntax | Effect |
|---|---|
| `@startpacketdiag` … `@endpacketdiag` | Dedicated mode for bit-range diagrams (not `@startuml`) |
| `0-15: Source Port` | Field occupying bit range 0–15; the label is what appears in the box |
| `106: URG` | Single-bit field (one number, no range) |
| `colwidth = 32` | Width allocated per bit column — raise it when labels are long |
| `node_height = 72` | Row height in points; increase for wrapped/2-line labels |
| `scale_interval = 2` | Scale lookup (see fixture 005) — useful for very wide layouts |

## Data Shape

A **contiguous bit map**: ranges must tile the header without gaps or overlaps, because the diagram *is* the
specification. Order ranges from bit 0 (left/top) to the end of the header; put payload at the end and label it
as such.

## Pitfalls

- ❌ Gaps or overlaps in bit ranges → ✅ ranges must tile exactly; a gap is a specification bug, not a rendering one
- ❌ One-letter labels for flags → ✅ write the flag name (`SYN`, `ACK`); the reader is looking up field meanings
- ❌ Colours as decoration → ✅ if you colour, colour by meaning (header vs payload, or fixed vs variable)
- ❌ Trying to show packet *sequence* here → ✅ packetdiag is a layout view; use a sequence diagram for exchanges

## Alternatives

| Variant | Use instead |
|---|---|
| Message exchange between components | `api-interaction-sequence.md` |
| Stateful protocol behaviour | `order-state-machine.md` |
| Field semantics in prose/table form | A GFM table (better for searchable documentation) |

<!-- source: draw-uml-dev fixtures/plantuml/packetdiag-diagram/001/002/005.puml (L1, 16 fixtures) -->
