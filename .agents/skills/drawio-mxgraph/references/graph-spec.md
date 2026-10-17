# Graph specification and edit operations

## Build specification

Use this shape:

```json
{
  "title": "Agent Platform Architecture",
  "direction": "LR",
  "auto_icons": true,
  "icon_layout": "tile",
  "icon_tile_size": 96,
  "nodes": [
    {"id": "user", "label": "User", "type": "actor", "icon": "user"},
    {"id": "gateway", "label": "API Gateway", "type": "service", "icon": "api-gateway"},
    {"id": "db", "label": "State DB", "type": "database"}
  ],
  "edges": [
    {"id": "edge-user-gateway", "source": "user", "target": "gateway", "label": "HTTPS"},
    {"id": "edge-gateway-db", "source": "gateway", "target": "db"}
  ],
  "groups": [
    {"id": "platform", "label": "Platform", "members": ["gateway", "db"]}
  ]
}
```

Allowed directions are `LR`, `RL`, `TB`, and `BT`.

`auto_icons` defaults to `true`. Automatic selection only fills nodes that do not already define `style`, `drawio_shape`, or `icon`.

Node fields:

- `id` and `label` are required.
- `type` may be `service`, `process`, `database`, `queue`, `actor`, `decision`, `document`, or `external`.
- `x`, `y`, `width`, and `height` are optional.
- `style` optionally overrides the default Draw.io style.
- `drawio_shape` optionally selects a native Draw.io stencil alias or exact `mxgraph.*` shape.
- `icon` optionally selects a bundled alias, an Iconify `prefix:name`, or a local image path.
- `icon_color` optionally fixes the color of a monochrome Iconify SVG at fetch time.
- `icon_layout` may be `tile` to render an icon and its label inside a bordered square card.
- `icon_tile_size` controls the square card size in pixels. It can be set globally or per node.
- `icon_font_size`, `icon_font_color`, and `icon_label_bold` optionally style labels beneath standalone icons. The size is clamped to 8–28 pixels; defaults preserve the compact style.
- `group` optionally names the parent group.

Style precedence is `style`, then `drawio_shape`, then `icon`, then `type`.

Edge fields:

- `id`, `source`, and `target` are required.
- `label` and `style` are optional.
- `points` optionally supplies absolute orthogonal waypoints as `[{"x": 300, "y": 200}]`.

Group fields:

- `id`, `label`, and `members` are required.
- `x`, `y`, `width`, `height`, and `style` are optional.
- A member may belong to at most one group.

## Incremental operations

Store operations as either a JSON array or `{"operations": [...]}`.

```json
{
  "operations": [
    {
      "op": "add_node",
      "node": {"id": "cache", "label": "Redis Cache", "type": "database", "icon": "mdi:database-clock-outline", "x": 700, "y": 80}
    },
    {
      "op": "add_edge",
      "edge": {"id": "edge-api-cache", "source": "api", "target": "cache", "label": "read/write"}
    },
    {"op": "move_node", "id": "cache", "x": 720, "y": 120},
    {"op": "update_node", "id": "api", "label": "Public API"},
    {"op": "group", "id": "data-zone", "label": "Data Layer", "members": ["cache", "db"]},
    {"op": "set_layout", "direction": "TB"},
    {"op": "remove_edge", "id": "edge-api-cache"},
    {"op": "remove_node", "id": "cache"},
    {"op": "ungroup", "id": "data-zone"}
  ]
}
```

Operation behavior:

- `add_node`: Add a vertex. Coordinates default to an open position.
- `update_node`: Change `label`, `type`, `style`, `drawio_shape`, `icon`, `icon_color`, `width`, or `height`.
- `remove_node`: Remove the node and all incident edges.
- `move_node`: Set absolute canvas coordinates, including for grouped nodes.
- `add_edge`: Add an edge between existing nodes.
- `remove_edge`: Remove an edge by ID.
- `group`: Create a swimlane container and move members into it while preserving their absolute positions.
- `ungroup`: Return members to the main layer while preserving absolute positions, then remove the container.
- `set_layout`: Recalculate node positions using graph depth and the requested direction.

Keep operation IDs identical to the existing mxCell IDs.
