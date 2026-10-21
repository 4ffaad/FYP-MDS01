#!/usr/bin/env python3
"""Build, edit, and validate editable Draw.io (mxGraph) XML files."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import mimetypes
import re
import sys
import urllib.parse
import urllib.request
import zlib
from collections import defaultdict, deque
from pathlib import Path
import xml.etree.ElementTree as ET


SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ICON_CATALOG = SKILL_DIR / "assets" / "icon-catalog.json"
DEFAULT_ICON_CACHE = SKILL_DIR / "assets" / "icons"
ICONIFY_API = "https://api.iconify.design"
ICON_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*:[a-z0-9]+(?:-[a-z0-9]+)*$")

NODE_STYLES = {
    "service": "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;",
    "process": "rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;",
    "database": "shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=15;fillColor=#fff2cc;strokeColor=#d6b656;",
    "queue": "shape=process;whiteSpace=wrap;html=1;backgroundOutline=1;fillColor=#ffe6cc;strokeColor=#d79b00;",
    "actor": "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;outlineConnect=0;",
    "decision": "rhombus;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;",
    "document": "shape=document;whiteSpace=wrap;html=1;boundedLbl=1;fillColor=#e1d5e7;strokeColor=#9673a6;",
    "external": "rounded=1;whiteSpace=wrap;html=1;dashed=1;fillColor=#f5f5f5;strokeColor=#666666;",
}
EDGE_STYLE = (
    "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;"
    "strokeColor=#64748B;strokeWidth=1.5;endArrow=block;endFill=1;"
    "fontColor=#334155;fontSize=10;labelBackgroundColor=#FFFFFF;"
    "labelBorderColor=#E2E8F0;spacing=4;"
)
GROUP_STYLE = "swimlane;html=1;startSize=28;rounded=1;collapsible=0;fillColor=#f5f5f5;strokeColor=#666666;"


class DiagramError(ValueError):
    pass


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_catalog(path: Path | None = None):
    catalog_path = path or DEFAULT_ICON_CATALOG
    if not catalog_path.exists():
        return {"aliases": {}, "drawio_shapes": {}, "libraries": []}
    data = load_json(catalog_path)
    if not isinstance(data, dict):
        raise DiagramError("Icon catalog must be a JSON object")
    data.setdefault("aliases", {})
    data.setdefault("drawio_shapes", {})
    data.setdefault("libraries", [])
    return data


def normalize_icon_id(value: str, catalog) -> str:
    icon_id = str(value).strip().lower()
    icon_id = catalog.get("aliases", {}).get(icon_id, icon_id)
    if icon_id.startswith("iconify:"):
        icon_id = icon_id[len("iconify:"):]
    if not ICON_ID_RE.fullmatch(icon_id):
        raise DiagramError(
            f"Invalid icon ID '{value}'. Use an alias or Iconify prefix:name, such as mdi:robot-outline"
        )
    return icon_id


def icon_cache_path(icon_id: str, cache_dir: Path = DEFAULT_ICON_CACHE, color: str | None = None) -> Path:
    suffix = ""
    if color:
        suffix = "--" + hashlib.sha1(color.encode("utf-8")).hexdigest()[:8]
    return cache_dir / f"{icon_id.replace(':', '--')}{suffix}.svg"


def fetch_iconify_svg(icon_id: str, output: Path, color: str | None = None):
    prefix, name = icon_id.split(":", 1)
    query = {}
    if color:
        query["color"] = color
    url = f"{ICONIFY_API}/{urllib.parse.quote(prefix)}/{urllib.parse.quote(name)}.svg"
    if query:
        url += "?" + urllib.parse.urlencode(query)
    request = urllib.request.Request(url, headers={"User-Agent": "drawio-mxgraph-skill/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            content_type = response.headers.get_content_type()
            payload = response.read()
    except Exception as exc:
        raise DiagramError(f"Could not fetch Iconify icon {icon_id}: {exc}") from exc
    if content_type not in ("image/svg+xml", "text/xml", "application/xml") and not payload.lstrip().startswith(b"<svg"):
        raise DiagramError(f"Iconify returned non-SVG content for {icon_id}")
    try:
        svg = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise DiagramError(f"Iconify returned invalid SVG for {icon_id}: {exc}") from exc
    if not svg.tag.endswith("svg"):
        raise DiagramError(f"Iconify response for {icon_id} is not SVG")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    return output


def file_data_uri(path: Path) -> str:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise DiagramError(f"Cannot read icon file {path}: {exc}") from exc
    mime_type = mimetypes.guess_type(path.name)[0]
    if mime_type not in ("image/svg+xml", "image/png", "image/jpeg", "image/webp", "image/gif"):
        raise DiagramError(f"Unsupported icon format for {path}; use SVG, PNG, JPEG, WebP, or GIF")
    # mxGraph style strings use semicolons as property separators. Base64 data
    # URIs contain ";base64" and can therefore be split before the image value
    # reaches the renderer. Percent-encoded data URIs avoid that ambiguity.
    encoded = urllib.parse.quote_from_bytes(payload, safe="")
    return f"data:{mime_type},{encoded}"


def resolve_icon_path(icon_value: str, catalog, cache_dir: Path, offline=False, color=None) -> Path:
    candidate = Path(icon_value).expanduser()
    if candidate.exists():
        return candidate.resolve()
    icon_id = normalize_icon_id(icon_value, catalog)
    cached = icon_cache_path(icon_id, cache_dir, color=color)
    if cached.exists():
        return cached
    if offline:
        raise DiagramError(f"Icon {icon_id} is not cached and offline mode is enabled")
    return fetch_iconify_svg(icon_id, cached, color=color)


def node_style(node, catalog, cache_dir: Path, offline=False) -> str:
    if node.get("style"):
        return str(node["style"])
    if node.get("drawio_shape"):
        shape_value = str(node["drawio_shape"]).strip()
        shape_name = catalog.get("drawio_shapes", {}).get(shape_value, shape_value)
        if not re.fullmatch(r"(?:mxgraph\.)?[A-Za-z0-9_.-]+", shape_name):
            raise DiagramError(f"Invalid Draw.io shape name: {shape_value}")
        return (
            f"shape={shape_name};html=1;whiteSpace=wrap;aspect=fixed;"
            "verticalLabelPosition=bottom;verticalAlign=top;"
        )
    if node.get("icon"):
        icon_path = resolve_icon_path(
            str(node["icon"]), catalog, cache_dir, offline=offline, color=node.get("icon_color")
        )
        data_uri = file_data_uri(icon_path)
        if node.get("icon_layout") == "tile":
            return (
                "shape=label;rounded=1;whiteSpace=wrap;html=1;imageAspect=0;"
                "imageWidth=44;imageHeight=44;imageAlign=center;imageVerticalAlign=top;"
                "spacingTop=8;verticalAlign=bottom;align=center;spacingBottom=8;"
                "fillColor=#FFFFFF;strokeColor=#CBD5E1;strokeWidth=1.5;"
                "fontColor=#1F2937;fontSize=11;shadow=1;image=" + data_uri + ";"
            )
        icon_font_size = max(8, min(28, int(round(num(node.get("icon_font_size"), 12)))))
        icon_font_color = str(node.get("icon_font_color", "#1F2937"))
        icon_label_bold = 1 if node.get("icon_label_bold", False) else 0
        return (
            "shape=image;verticalLabelPosition=bottom;verticalAlign=top;"
            "imageAspect=0;aspect=fixed;html=1;align=center;"
            f"fontSize={icon_font_size};fontColor={icon_font_color};"
            f"fontStyle={icon_label_bold};"
            "image=" + data_uri + ";"
        )
    return NODE_STYLES.get(node.get("type", "service"), NODE_STYLES["service"])


def auto_decorate_node(node, catalog):
    result = dict(node)
    if any(result.get(key) for key in ("style", "drawio_shape", "icon")):
        return result
    if result.get("type") in {"database", "decision", "document", "queue"}:
        return result
    text = " ".join(
        str(result.get(key, "")).lower()
        for key in ("id", "label", "type")
    )
    for rule in catalog.get("auto_rules", []):
        if any(str(keyword).lower() in text for keyword in rule.get("keywords", [])):
            if rule.get("drawio_shape"):
                result["drawio_shape"] = rule["drawio_shape"]
            elif rule.get("icon"):
                result["icon"] = rule["icon"]
            break
    return result


def search_iconify(query: str, limit: int = 32, prefix: str | None = None):
    params = {"query": query, "limit": max(32, min(int(limit), 999))}
    if prefix:
        params["prefix"] = prefix
    url = f"{ICONIFY_API}/search?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": "drawio-mxgraph-skill/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.load(response)
    except Exception as exc:
        raise DiagramError(f"Could not search Iconify: {exc}") from exc
    return data.get("icons", [])[:limit]


def geometry(cell: ET.Element) -> ET.Element:
    item = cell.find("mxGeometry")
    if item is None:
        item = ET.SubElement(cell, "mxGeometry", {"as": "geometry"})
    return item


def num(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def fmt(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def topological_positions(nodes, edges, direction: str):
    ids = [node["id"] for node in nodes]
    incoming = {node_id: 0 for node_id in ids}
    outgoing = defaultdict(list)
    for edge in edges:
        source, target = edge.get("source"), edge.get("target")
        if source in incoming and target in incoming:
            outgoing[source].append(target)
            incoming[target] += 1
    queue = deque(node_id for node_id in ids if incoming[node_id] == 0)
    depth = {node_id: 0 for node_id in ids}
    visited = set()
    while queue:
        source = queue.popleft()
        visited.add(source)
        for target in outgoing[source]:
            depth[target] = max(depth[target], depth[source] + 1)
            incoming[target] -= 1
            if incoming[target] == 0:
                queue.append(target)
    for index, node_id in enumerate(ids):
        if node_id not in visited:
            depth[node_id] = max(depth.values(), default=0) + 1 + index
    ranks = defaultdict(list)
    for node_id in ids:
        ranks[depth[node_id]].append(node_id)
    positions = {}
    rank_gap, lane_gap = 230, 140
    for rank in sorted(ranks):
        for lane, node_id in enumerate(ranks[rank]):
            a, b = 70 + rank * rank_gap, 70 + lane * lane_gap
            if direction == "LR":
                x, y = a, b
            elif direction == "RL":
                x, y = 70 + (max(ranks) - rank) * rank_gap, b
            elif direction == "TB":
                x, y = b, a
            elif direction == "BT":
                x, y = b, 70 + (max(ranks) - rank) * rank_gap
            else:
                raise DiagramError(f"Unsupported direction: {direction}")
            positions[node_id] = (x, y)
    return positions


def create_base(title: str, page_width: float = 1600, page_height: float = 900) -> tuple[ET.Element, ET.Element]:
    mxfile = ET.Element("mxfile", {
        "host": "app.diagrams.net",
        "agent": "Codex drawio-mxgraph skill",
        "version": "24.7.17",
        "type": "device",
        "compressed": "false",
    })
    diagram = ET.SubElement(mxfile, "diagram", {"id": "page-1", "name": title or "Page-1"})
    model = ET.SubElement(diagram, "mxGraphModel", {
        "dx": "1200", "dy": "800", "grid": "1", "gridSize": "10", "guides": "1",
        "tooltips": "1", "connect": "1", "arrows": "1", "fold": "1", "page": "1",
        "pageScale": "1", "pageWidth": fmt(page_width), "pageHeight": fmt(page_height),
        "math": "0", "shadow": "0",
    })
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})
    return mxfile, root


def add_vertex(root, node, parent="1", xy=None, catalog=None, cache_dir=DEFAULT_ICON_CACHE, offline=False):
    node_id = str(node["id"])
    if find_cell(root, node_id) is not None:
        raise DiagramError(f"Duplicate cell ID: {node_id}")
    node_type = node.get("type", "service")
    style = node_style(node, catalog or {"aliases": {}}, cache_dir, offline=offline)
    width = num(node.get("width"), 120 if node_type != "actor" else 60)
    height = num(node.get("height"), 60 if node_type != "actor" else 90)
    x, y = xy or (num(node.get("x"), 70), num(node.get("y"), 70))
    cell = ET.SubElement(root, "mxCell", {
        "id": node_id, "value": str(node.get("label", node_id)), "style": style,
        "vertex": "1", "parent": str(parent),
    })
    ET.SubElement(cell, "mxGeometry", {
        "x": fmt(x), "y": fmt(y), "width": fmt(width), "height": fmt(height), "as": "geometry",
    })
    return cell


def add_edge(root, edge):
    edge_id = str(edge["id"])
    if find_cell(root, edge_id) is not None:
        raise DiagramError(f"Duplicate cell ID: {edge_id}")
    source, target = str(edge["source"]), str(edge["target"])
    if find_cell(root, source) is None or find_cell(root, target) is None:
        raise DiagramError(f"Edge {edge_id} has missing endpoint: {source} -> {target}")
    cell = ET.SubElement(root, "mxCell", {
        "id": edge_id, "value": str(edge.get("label", "")),
        "style": edge.get("style") or EDGE_STYLE, "edge": "1",
        "parent": "1", "source": source, "target": target,
    })
    geo = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
    points = edge.get("points", [])
    if points:
        points_array = ET.SubElement(geo, "Array", {"as": "points"})
        for index, point in enumerate(points):
            if not isinstance(point, dict) or "x" not in point or "y" not in point:
                raise DiagramError(
                    f"Edge {edge_id} point {index} must contain numeric x and y"
                )
            ET.SubElement(points_array, "mxPoint", {
                "x": fmt(num(point["x"], 0)),
                "y": fmt(num(point["y"], 0)),
            })
    return cell


def find_cell(root, cell_id: str):
    return next((cell for cell in root.findall("mxCell") if cell.get("id") == str(cell_id)), None)


def absolute_xy(root, cell):
    geo = geometry(cell)
    x, y = num(geo.get("x"), 0), num(geo.get("y"), 0)
    parent_id = cell.get("parent")
    seen = set()
    while parent_id not in (None, "0", "1"):
        if parent_id in seen:
            raise DiagramError(f"Parent cycle at {cell.get('id')}")
        seen.add(parent_id)
        parent = find_cell(root, parent_id)
        if parent is None:
            break
        pgeo = geometry(parent)
        x += num(pgeo.get("x"), 0)
        y += num(pgeo.get("y"), 0) + num(parent.get("style", "").find("swimlane") >= 0 and 28 or 0, 0)
        parent_id = parent.get("parent")
    return x, y


def create_group(root, group_id, label, members, style=None):
    if find_cell(root, group_id) is not None:
        raise DiagramError(f"Duplicate group ID: {group_id}")
    cells = []
    for member in members:
        cell = find_cell(root, member)
        if cell is None or cell.get("vertex") != "1":
            raise DiagramError(f"Unknown group member: {member}")
        if cell.get("parent") != "1":
            raise DiagramError(f"Node already grouped: {member}")
        cells.append(cell)
    if not cells:
        raise DiagramError("A group needs at least one member")
    absolute = {cell.get("id"): absolute_xy(root, cell) for cell in cells}
    min_x = min(value[0] for value in absolute.values()) - 30
    min_y = min(value[1] for value in absolute.values()) - 50
    max_x = max(absolute[cell.get("id")][0] + num(geometry(cell).get("width"), 120) for cell in cells) + 30
    max_y = max(absolute[cell.get("id")][1] + num(geometry(cell).get("height"), 60) for cell in cells) + 30
    group = ET.SubElement(root, "mxCell", {
        "id": str(group_id), "value": str(label), "style": style or GROUP_STYLE,
        "vertex": "1", "parent": "1",
    })
    ET.SubElement(group, "mxGeometry", {
        "x": fmt(min_x), "y": fmt(min_y), "width": fmt(max_x - min_x),
        "height": fmt(max_y - min_y), "as": "geometry",
    })
    for cell in cells:
        x, y = absolute[cell.get("id")]
        cell.set("parent", str(group_id))
        geo = geometry(cell)
        geo.set("x", fmt(x - min_x))
        geo.set("y", fmt(y - min_y - 28))
    return group


def raise_edges_above_containers(root):
    """Keep connectors visible over swimlane fills and group outlines."""
    edges = [cell for cell in root.findall("mxCell") if cell.get("edge") == "1"]
    for edge in edges:
        root.remove(edge)
    for edge in edges:
        root.append(edge)


def ungroup(root, group_id):
    group = find_cell(root, group_id)
    if group is None or "swimlane" not in group.get("style", ""):
        raise DiagramError(f"Unknown group: {group_id}")
    members = [cell for cell in root.findall("mxCell") if cell.get("parent") == str(group_id)]
    positions = {cell.get("id"): absolute_xy(root, cell) for cell in members}
    for cell in members:
        cell.set("parent", "1")
        geo = geometry(cell)
        geo.set("x", fmt(positions[cell.get("id")][0]))
        geo.set("y", fmt(positions[cell.get("id")][1]))
    root.remove(group)


def build(spec, catalog=None, cache_dir=DEFAULT_ICON_CACHE, offline=False, auto_icons=True):
    direction = str(spec.get("direction", "LR")).upper()
    nodes = spec.get("nodes", [])
    edges = spec.get("edges", [])
    positions = topological_positions(nodes, edges, direction)
    page_width = max(1, num(spec.get("page_width"), 1600))
    page_height = max(1, num(spec.get("page_height"), 900))
    mxfile, root = create_base(str(spec.get("title", "Page-1")), page_width, page_height)
    for node in nodes:
        rendered_node = auto_decorate_node(node, catalog or {}) if auto_icons else node
        if rendered_node.get("icon") and spec.get("icon_layout"):
            rendered_node = dict(rendered_node)
            rendered_node.setdefault("icon_layout", spec["icon_layout"])
            if rendered_node.get("icon_layout") == "tile":
                tile_size = num(
                    rendered_node.get("icon_tile_size"),
                    num(spec.get("icon_tile_size"), 96),
                )
                rendered_node["width"] = tile_size
                rendered_node["height"] = tile_size
        xy = (
            num(node.get("x"), positions[node["id"]][0]),
            num(node.get("y"), positions[node["id"]][1]),
        )
        add_vertex(
            root, rendered_node, xy=xy, catalog=catalog, cache_dir=cache_dir, offline=offline
        )
    for edge in edges:
        add_edge(root, edge)
    grouped = set()
    for group in spec.get("groups", []):
        members = [str(item) for item in group.get("members", [])]
        overlap = grouped.intersection(members)
        if overlap:
            raise DiagramError(f"Nodes belong to multiple groups: {sorted(overlap)}")
        create_group(root, str(group["id"]), str(group.get("label", group["id"])), members, group.get("style"))
        grouped.update(members)
    raise_edges_above_containers(root)
    return mxfile


def decode_diagram_text(text: str) -> ET.Element:
    try:
        raw = zlib.decompress(base64_decode(text), -15)
        return ET.fromstring(urllib.parse.unquote(raw.decode("utf-8")))
    except Exception as exc:
        raise DiagramError(f"Cannot decode compressed diagram: {exc}") from exc


def base64_decode(text: str) -> bytes:
    import base64
    return base64.b64decode(text)


def parse_file(path: Path, require_editable=False):
    try:
        tree = ET.parse(path)
    except (ET.ParseError, OSError) as exc:
        raise DiagramError(f"Invalid XML: {exc}") from exc
    mxfile = tree.getroot()
    if mxfile.tag != "mxfile":
        raise DiagramError("Root element must be <mxfile>")
    diagrams = mxfile.findall("diagram")
    if not diagrams:
        raise DiagramError("No <diagram> page found")
    for diagram in diagrams:
        if diagram.find("mxGraphModel") is None and (diagram.text or "").strip():
            if require_editable:
                raise DiagramError("Incremental editing requires uncompressed mxGraph XML")
            decode_diagram_text((diagram.text or "").strip())
    return tree


def roots_from_tree(tree):
    roots = []
    for diagram in tree.getroot().findall("diagram"):
        model = diagram.find("mxGraphModel")
        if model is not None:
            root = model.find("root")
            if root is not None:
                roots.append(root)
    return roots


def validate_tree(tree):
    errors = []
    roots = roots_from_tree(tree)
    if not roots:
        for diagram in tree.getroot().findall("diagram"):
            if (diagram.text or "").strip():
                try:
                    model = decode_diagram_text((diagram.text or "").strip())
                    root = model.find("root")
                    if root is not None:
                        roots.append(root)
                except DiagramError as exc:
                    errors.append(str(exc))
    if not roots:
        errors.append("No mxGraphModel/root found")
    for page, root in enumerate(roots, 1):
        cells = root.findall("mxCell")
        ids = [cell.get("id") for cell in cells]
        if "0" not in ids or "1" not in ids:
            errors.append(f"Page {page}: required base cells 0 and 1 are missing")
        duplicates = sorted({cell_id for cell_id in ids if cell_id and ids.count(cell_id) > 1})
        if duplicates:
            errors.append(f"Page {page}: duplicate IDs: {duplicates}")
        known = set(ids)
        for cell in cells:
            cell_id = cell.get("id", "<missing>")
            style = cell.get("style", "")
            for attr in ("parent", "source", "target"):
                ref = cell.get(attr)
                if ref and ref not in known:
                    errors.append(f"Page {page}: {cell_id} has unknown {attr}={ref}")
            if cell.get("vertex") == "1" and cell.find("mxGeometry") is None:
                errors.append(f"Page {page}: vertex {cell_id} lacks mxGeometry")
            if "image=data:" in style and ";base64," in style:
                errors.append(
                    f"Page {page}: vertex {cell_id} uses a base64 data URI inside an "
                    "mxGraph style; use a percent-encoded data URI to preserve the image"
                )
            if cell.get("edge") == "1":
                if not cell.get("source") or not cell.get("target"):
                    errors.append(f"Page {page}: edge {cell_id} lacks source or target")
                geo = cell.find("mxGeometry")
                if geo is None or geo.get("as") != "geometry":
                    errors.append(f"Page {page}: edge {cell_id} lacks valid mxGeometry")
    return errors


def set_layout(root, direction):
    direction = str(direction).upper()
    group_ids = {
        cell.get("parent")
        for cell in root.findall("mxCell")
        if cell.get("vertex") == "1"
        and "swimlane" not in cell.get("style", "")
        and cell.get("parent") not in (None, "0", "1")
    }
    for group_id in sorted(group_ids):
        ungroup(root, group_id)
    nodes = [
        cell for cell in root.findall("mxCell")
        if cell.get("vertex") == "1" and "swimlane" not in cell.get("style", "")
    ]
    node_ids = {cell.get("id") for cell in nodes}
    edges = [
        {"source": cell.get("source"), "target": cell.get("target")}
        for cell in root.findall("mxCell")
        if cell.get("edge") == "1" and cell.get("source") in node_ids and cell.get("target") in node_ids
    ]
    positions = topological_positions([{"id": cell.get("id")} for cell in nodes], edges, direction)
    for cell in nodes:
        x, y = positions[cell.get("id")]
        geo = geometry(cell)
        geo.set("x", fmt(x))
        geo.set("y", fmt(y))


def apply_operations(
    tree, operations, catalog=None, cache_dir=DEFAULT_ICON_CACHE, offline=False, auto_icons=True
):
    roots = roots_from_tree(tree)
    if not roots:
        raise DiagramError("No editable mxGraphModel/root found")
    root = roots[0]
    for item in operations:
        op = item.get("op")
        if op == "add_node":
            node = item["node"]
            rendered_node = auto_decorate_node(node, catalog or {}) if auto_icons else node
            add_vertex(
                root, rendered_node, xy=(num(node.get("x"), 70), num(node.get("y"), 70)),
                catalog=catalog, cache_dir=cache_dir, offline=offline,
            )
        elif op == "update_node":
            cell = find_cell(root, item["id"])
            if cell is None or cell.get("vertex") != "1":
                raise DiagramError(f"Unknown node: {item['id']}")
            if "label" in item:
                cell.set("value", str(item["label"]))
            if "type" in item:
                cell.set("style", NODE_STYLES.get(item["type"], NODE_STYLES["service"]))
            if "style" in item:
                cell.set("style", str(item["style"]))
            if "icon" in item or "drawio_shape" in item:
                cell.set("style", node_style(item, catalog or {"aliases": {}}, cache_dir, offline=offline))
            geo = geometry(cell)
            for key in ("width", "height"):
                if key in item:
                    geo.set(key, fmt(num(item[key], num(geo.get(key), 60))))
        elif op == "remove_node":
            cell = find_cell(root, item["id"])
            if cell is None or cell.get("vertex") != "1":
                raise DiagramError(f"Unknown node: {item['id']}")
            for edge in list(root.findall("mxCell")):
                if edge.get("source") == item["id"] or edge.get("target") == item["id"]:
                    root.remove(edge)
            root.remove(cell)
        elif op == "move_node":
            cell = find_cell(root, item["id"])
            if cell is None or cell.get("vertex") != "1":
                raise DiagramError(f"Unknown node: {item['id']}")
            abs_x, abs_y = num(item["x"], 0), num(item["y"], 0)
            parent = find_cell(root, cell.get("parent", "1"))
            if parent is not None and parent.get("id") not in ("0", "1"):
                px, py = absolute_xy(root, parent)
                abs_x, abs_y = abs_x - px, abs_y - py - 28
            geo = geometry(cell)
            geo.set("x", fmt(abs_x))
            geo.set("y", fmt(abs_y))
        elif op == "add_edge":
            add_edge(root, item["edge"])
        elif op == "remove_edge":
            cell = find_cell(root, item["id"])
            if cell is None or cell.get("edge") != "1":
                raise DiagramError(f"Unknown edge: {item['id']}")
            root.remove(cell)
        elif op == "group":
            create_group(root, str(item["id"]), str(item.get("label", item["id"])), item.get("members", []), item.get("style"))
        elif op == "ungroup":
            ungroup(root, item["id"])
        elif op == "set_layout":
            set_layout(root, item["direction"])
        else:
            raise DiagramError(f"Unsupported operation: {op}")
    raise_edges_above_containers(root)


def indent_and_write(tree_or_root, output: Path):
    root = tree_or_root.getroot() if isinstance(tree_or_root, ET.ElementTree) else tree_or_root
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("--spec", type=Path, required=True)
    build_parser.add_argument("--output", type=Path, required=True)
    build_parser.add_argument("--catalog", type=Path, default=DEFAULT_ICON_CATALOG)
    build_parser.add_argument("--icon-cache", type=Path, default=DEFAULT_ICON_CACHE)
    build_parser.add_argument("--offline", action="store_true")
    build_parser.add_argument("--no-auto-icons", action="store_true")
    edit_parser = sub.add_parser("edit")
    edit_parser.add_argument("--input", type=Path, required=True)
    edit_parser.add_argument("--ops", type=Path, required=True)
    edit_parser.add_argument("--output", type=Path, required=True)
    edit_parser.add_argument("--catalog", type=Path, default=DEFAULT_ICON_CATALOG)
    edit_parser.add_argument("--icon-cache", type=Path, default=DEFAULT_ICON_CACHE)
    edit_parser.add_argument("--offline", action="store_true")
    edit_parser.add_argument("--no-auto-icons", action="store_true")
    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("input", type=Path)
    libraries_parser = sub.add_parser("libraries")
    libraries_parser.add_argument("--catalog", type=Path, default=DEFAULT_ICON_CATALOG)
    shapes_parser = sub.add_parser("shapes")
    shapes_parser.add_argument("--catalog", type=Path, default=DEFAULT_ICON_CATALOG)
    icons_parser = sub.add_parser("icons")
    icons_sub = icons_parser.add_subparsers(dest="icon_command", required=True)
    icon_list = icons_sub.add_parser("list")
    icon_list.add_argument("--catalog", type=Path, default=DEFAULT_ICON_CATALOG)
    icon_search = icons_sub.add_parser("search")
    icon_search.add_argument("query")
    icon_search.add_argument("--limit", type=int, default=20)
    icon_search.add_argument("--prefix")
    icon_fetch = icons_sub.add_parser("fetch")
    icon_fetch.add_argument("icon")
    icon_fetch.add_argument("--catalog", type=Path, default=DEFAULT_ICON_CATALOG)
    icon_fetch.add_argument("--icon-cache", type=Path, default=DEFAULT_ICON_CACHE)
    icon_fetch.add_argument("--color")
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            spec = load_json(args.spec)
            catalog = load_catalog(args.catalog)
            auto_icons = bool(spec.get("auto_icons", not args.no_auto_icons))
            root = build(
                spec, catalog=catalog, cache_dir=args.icon_cache,
                offline=args.offline, auto_icons=auto_icons,
            )
            errors = validate_tree(ET.ElementTree(root))
            if errors:
                raise DiagramError("\n".join(errors))
            args.output.parent.mkdir(parents=True, exist_ok=True)
            indent_and_write(root, args.output)
            print(f"Created {args.output}")
        elif args.command == "edit":
            tree = parse_file(args.input, require_editable=True)
            payload = load_json(args.ops)
            operations = payload if isinstance(payload, list) else payload.get("operations", [])
            catalog = load_catalog(args.catalog)
            auto_icons = (
                not args.no_auto_icons
                if isinstance(payload, list)
                else bool(payload.get("auto_icons", not args.no_auto_icons))
            )
            apply_operations(
                tree, operations, catalog=catalog, cache_dir=args.icon_cache,
                offline=args.offline, auto_icons=auto_icons,
            )
            errors = validate_tree(tree)
            if errors:
                raise DiagramError("\n".join(errors))
            args.output.parent.mkdir(parents=True, exist_ok=True)
            indent_and_write(tree, args.output)
            print(f"Created {args.output}")
        elif args.command == "validate":
            tree = parse_file(args.input)
            errors = validate_tree(tree)
            if errors:
                print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
                return 1
            print(f"VALID: {args.input}")
        elif args.command == "libraries":
            catalog = load_catalog(args.catalog)
            for library in catalog.get("libraries", []):
                print(
                    f"{library['id']}\t{library['name']}\t"
                    f"{library.get('category', '')}\t{library.get('activation', '')}"
                )
        elif args.command == "shapes":
            catalog = load_catalog(args.catalog)
            for alias, shape_name in sorted(catalog.get("drawio_shapes", {}).items()):
                print(f"{alias}\t{shape_name}")
        elif args.command == "icons" and args.icon_command == "list":
            catalog = load_catalog(args.catalog)
            for alias, icon_id in sorted(catalog.get("aliases", {}).items()):
                cached = icon_cache_path(icon_id, DEFAULT_ICON_CACHE).exists()
                print(f"{alias}\t{icon_id}\t{'cached' if cached else 'remote'}")
        elif args.command == "icons" and args.icon_command == "search":
            for icon_id in search_iconify(args.query, args.limit, args.prefix):
                print(icon_id)
        elif args.command == "icons" and args.icon_command == "fetch":
            catalog = load_catalog(args.catalog)
            icon_id = normalize_icon_id(args.icon, catalog)
            path = icon_cache_path(icon_id, args.icon_cache, color=args.color)
            if not path.exists():
                fetch_iconify_svg(icon_id, path, color=args.color)
            print(f"FETCHED: {icon_id} -> {path}")
        return 0
    except (DiagramError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
