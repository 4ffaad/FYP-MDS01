#!/usr/bin/env python3
"""Render static SVG previews from the editable Draw.io graph specifications."""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path


def style_values(style: str) -> dict[str, str]:
    return dict(
        part.split("=", 1)
        for part in style.split(";")
        if "=" in part
    )


def box(node: dict) -> tuple[float, float, float, float]:
    return tuple(float(node[key]) for key in ("x", "y", "width", "height"))


def label_lines(label: str) -> list[str]:
    return label.replace("\\n", "\n").splitlines()


def render(spec_path: Path) -> Path:
    graph = json.loads(spec_path.read_text())
    width = int(graph.get("page_width", 1600))
    height = int(graph.get("page_height", 900))
    nodes = {node["id"]: node for node in graph["nodes"]}
    svg: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 z" fill="#61758A"/></marker><filter id="shadow" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#0F172A" flood-opacity="0.10"/></filter></defs>',
        '<rect width="100%" height="100%" fill="#FFFFFF"/>',
    ]

    for group in graph.get("groups", []):
        members = [nodes[item] for item in group["members"] if item in nodes]
        if not members:
            continue
        x, y, w, h = (
            float(group.get("x", min(float(n["x"]) for n in members) - 24)),
            float(group.get("y", min(float(n["y"]) for n in members) - 50)),
            float(group.get("width", max(float(n["x"]) + float(n["width"]) for n in members) - min(float(n["x"]) for n in members) + 48)),
            float(group.get("height", max(float(n["y"]) + float(n["height"]) for n in members) - min(float(n["y"]) for n in members) + 74)),
        )
        values = style_values(group.get("style", ""))
        fill = values.get("swimlaneFillColor", values.get("fillColor", "#F8FAFC"))
        stroke = values.get("strokeColor", "#CBD5E1")
        title_color = values.get("fontColor", "#334155")
        svg.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
        )
        svg.append(
            f'<path d="M{x+1},{y+39} H{x+w-1}" stroke="{stroke}" stroke-width="1.5"/>'
        )
        svg.append(
            f'<text x="{x+18}" y="{y+27}" fill="{title_color}" font-family="Arial, sans-serif" font-size="15" font-weight="700">{html.escape(group["label"])}</text>'
        )

    def anchor(node: dict, side: str) -> tuple[float, float]:
        x, y, w, h = box(node)
        if side == "right":
            return x + w, y + h / 2
        if side == "left":
            return x, y + h / 2
        if side == "bottom":
            return x + w / 2, y + h
        return x + w / 2, y

    for edge in graph.get("edges", []):
        source = nodes.get(edge["source"])
        target = nodes.get(edge["target"])
        if source is None or target is None:
            continue
        sx0, sy0, sw, sh = box(source)
        tx0, ty0, tw, th = box(target)
        if abs((tx0 + tw / 2) - (sx0 + sw / 2)) > abs((ty0 + th / 2) - (sy0 + sh / 2)):
            forward = (tx0 + tw / 2) >= (sx0 + sw / 2)
            start = anchor(source, "right" if forward else "left")
            end = anchor(target, "left" if forward else "right")
            middle = (start[0] + end[0]) / 2
            points = [start, (middle, start[1]), (middle, end[1]), end]
        else:
            forward = (ty0 + th / 2) >= (sy0 + sh / 2)
            start = anchor(source, "bottom" if forward else "top")
            end = anchor(target, "top" if forward else "bottom")
            middle = (start[1] + end[1]) / 2
            points = [start, (start[0], middle), (end[0], middle), end]
        if edge.get("points"):
            points = [start] + [(float(p["x"]), float(p["y"])) for p in edge["points"]] + [end]
        d = "M " + " L ".join(f"{x:g} {y:g}" for x, y in points)
        svg.append(f'<path d="{d}" fill="none" stroke="#61758A" stroke-width="2" marker-end="url(#arrow)"/>')
        if edge.get("label"):
            mid = points[len(points) // 2]
            text = html.escape(edge["label"])
            label_width = min(220, max(50, len(edge["label"]) * 6.4 + 14))
            svg.append(f'<rect x="{mid[0]-label_width/2:g}" y="{mid[1]-13:g}" width="{label_width:g}" height="22" rx="5" fill="#FFFFFF" stroke="#DCE4EC"/>')
            svg.append(f'<text x="{mid[0]:g}" y="{mid[1]+2:g}" text-anchor="middle" fill="#40566D" font-family="Arial, sans-serif" font-size="11">{text}</text>')

    for node in graph["nodes"]:
        x, y, w, h = box(node)
        values = style_values(node.get("style", ""))
        if values.get("whiteSpace") == "wrap" or node.get("type"):
            fill = values.get("fillColor", "#FFFFFF")
            stroke = values.get("strokeColor", "#94A3B8")
            color = values.get("fontColor", "#0F172A")
            stroke_width = values.get("strokeWidth", "1.5")
            radius = 12 if values.get("rounded") == "1" else 3
            if "rhombus" in values.get("shape", ""):
                points = f"{x+w/2},{y} {x+w},{y+h/2} {x+w/2},{y+h} {x},{y+h/2}"
                svg.append(f'<polygon points="{points}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" filter="url(#shadow)"/>')
            elif "cylinder" in values.get("shape", ""):
                svg.append(f'<path d="M{x},{y+12} C{x},{y-4} {x+w},{y-4} {x+w},{y+12} L{x+w},{y+h-12} C{x+w},{y+h+4} {x},{y+h+4} {x},{y+h-12} Z" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" filter="url(#shadow)"/><ellipse cx="{x+w/2}" cy="{y+12}" rx="{w/2}" ry="12" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>')
            else:
                svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" filter="url(#shadow)"/>')
        else:
            color = values.get("fontColor", "#10243A")
        font_size = int(values.get("fontSize", "14"))
        bold = "font-weight=\"700\"" if values.get("fontStyle", "0") != "0" else ""
        lines = label_lines(node.get("label", ""))
        line_height = font_size + 4
        content_height = max(1, len(lines)) * line_height
        baseline = y + (h - content_height) / 2 + font_size * 0.82
        align = values.get("align", "center")
        tx = x + 14 if align == "left" else (x + w / 2)
        anchor_text = "start" if align == "left" else "middle"
        for index, line in enumerate(lines):
            svg.append(f'<text x="{tx:g}" y="{baseline + index*(font_size+4):g}" text-anchor="{anchor_text}" fill="{values.get("fontColor", "#0F172A")}" font-family="Arial, sans-serif" font-size="{font_size}" {bold}>{html.escape(line)}</text>')

    svg.append("</svg>")
    output_name = {
        "system-architecture.json": "system-architecture-preview.svg",
    }.get(spec_path.name, spec_path.with_suffix(".svg").name)
    output = spec_path.with_name(output_name)
    output.write_text("\n".join(svg))
    return output


if __name__ == "__main__":
    if len(sys.argv) > 1:
        paths = [Path(arg) for arg in sys.argv[1:]]
    else:
        paths = sorted(Path(__file__).parent.glob("*.json"))
    for path in paths:
        print(render(path))
