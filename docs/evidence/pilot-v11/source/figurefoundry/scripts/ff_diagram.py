"""Render an explicitly specified scientific diagram as editable, native SVG.

Coordinates are millimetres; text size is specified in points.  This module
deliberately does not infer biological, experimental, or software topology.
"""
from __future__ import annotations

import math
import re
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
PT_MM = 25.4 / 72.0
FONT_FAMILY = "Arial, Helvetica, Noto Sans CJK SC, Microsoft YaHei, sans-serif"
PALETTE = {
    "input": "#EAF2F8", "process": "#E8F1EC", "evidence": "#FFF3DB",
    "output": "#EEEAF7", "control": "#FBEDEC", "neutral": "#F3F5F7",
}


def _tag(name):
    return f"{{{SVG_NS}}}{name}"


def _number(value, name, *, positive=False, nonnegative=False):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number, not a boolean")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    if positive and result <= 0:
        raise ValueError(f"{name} must be positive")
    if nonnegative and result < 0:
        raise ValueError(f"{name} cannot be negative")
    return result


def _fmt(value):
    return f"{float(value):.6f}".rstrip("0").rstrip(".") or "0"


def _element(parent, tag, **attributes):
    return ET.SubElement(parent, _tag(tag), {
        key.replace("_", "-"): str(value) for key, value in attributes.items()
        if value is not None
    })


def _xml_text(value, name):
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a text string")
    if any(ord(character) < 32 and character not in "\t\n\r" or 0xD800 <= ord(character) <= 0xDFFF or ord(character) in {0xFFFE, 0xFFFF} for character in value):
        raise ValueError(f"{name} contains characters that are invalid in XML")
    return value


def _identifier(value, prefix, index):
    token = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-") or "item"
    return f"{prefix}-{index + 1}-{token}"


def _color(value, name):
    value = str(value)
    if re.fullmatch(r"#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})", value):
        return value
    if value.lower() in {"white", "black", "gray", "grey", "navy", "blue", "teal", "green", "purple", "orange", "red", "none"}:
        return value
    raise ValueError(f"{name} must be a solid #RGB/#RRGGBB or basic named color")


def _advance(character):
    """Conservative sans-serif width estimate in em; no font service needed."""
    if unicodedata.combining(character):
        return 0.0
    if unicodedata.east_asian_width(character) in {"W", "F"}:
        return 1.0
    if character.isspace():
        return 0.32
    if character in "ilI.,:;!'|`":
        return 0.30
    if character in "MW@%&#":
        return 0.92
    if character.isupper():
        return 0.70
    return 0.59


def _text_width(text, font_mm):
    return sum(_advance(character) for character in text) * font_mm


def _wrap(text, max_width_mm, font_mm):
    if max_width_mm <= 0:
        raise ValueError("Label has no available horizontal space")
    lines = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        remaining = paragraph
        while remaining:
            width, fit = 0.0, 0
            for character in remaining:
                next_width = width + _advance(character) * font_mm
                if next_width > max_width_mm + 1e-9:
                    break
                width, fit = next_width, fit + 1
            if fit == 0:
                raise ValueError("Label box is narrower than one character")
            if fit == len(remaining):
                lines.append(remaining.rstrip())
                break
            # Prefer a complete Latin word; CJK and long tokens wrap by character.
            candidate = remaining[:fit]
            boundary = max(candidate.rfind(" "), candidate.rfind("\t"))
            if boundary > fit * 0.4:
                fit = boundary
            lines.append(remaining[:fit].rstrip())
            remaining = remaining[fit:].lstrip()
    return lines


def _label(parent, label, cx, cy, available_width, available_height, *, font_pt=8.0,
           min_font_pt=6.0, anchor="middle", fill="#22313F", weight="normal"):
    label = _xml_text(label, "Label")
    font_pt = _number(font_pt, "font_pt", positive=True)
    min_font_pt = _number(min_font_pt, "min_font_pt", positive=True)
    if font_pt < min_font_pt:
        raise ValueError("font_pt cannot be smaller than min_font_pt")
    chosen = font_pt
    while True:
        font_mm = chosen * PT_MM
        lines = _wrap(label, available_width, font_mm)
        line_height = font_mm * 1.28
        text_height = font_mm + max(0, len(lines) - 1) * line_height
        if text_height <= available_height + 1e-7:
            break
        if chosen <= min_font_pt + 1e-7:
            raise ValueError(
                f"Label {label!r} cannot fit its box at {min_font_pt:g} pt; "
                "enlarge the node or shorten the label"
            )
        chosen = max(min_font_pt, chosen - 0.25)
    text = _element(parent, "text", x=_fmt(cx), text_anchor=anchor,
                    font_family=FONT_FAMILY, font_size=_fmt(font_mm),
                    fill=fill, font_weight=weight)
    text.set("aria-label", label)
    # Explicit baselines are more portable than dominant-baseline across editors.
    first_y = cy - (len(lines) - 1) * line_height / 2 + font_mm * 0.34
    cursor, previous = 0, None
    for index, line in enumerate(lines):
        position = label.find(line, cursor) if line else cursor
        if position < 0:
            raise ValueError("Label wrapping failed to preserve its source text")
        if previous is not None:
            previous.tail = label[cursor:position] or None
        span = _element(text, "tspan", x=_fmt(cx), y=_fmt(first_y + index * line_height))
        span.text = line
        previous, cursor = span, position + len(line)
    return {"font_pt": chosen, "lines": lines, "width_mm": max((_text_width(line, font_mm) for line in lines), default=0.0), "height_mm": text_height}


def _box(item, name, page_width, page_height):
    required = ("x", "y", "width", "height")
    missing = [key for key in required if key not in item]
    if missing:
        raise ValueError(f"{name} is missing geometry: {', '.join(missing)}")
    result = {key: _number(item[key], f"{name}.{key}", positive=key in {"width", "height"}, nonnegative=key in {"x", "y"}) for key in required}
    if result["x"] + result["width"] > page_width + 1e-7 or result["y"] + result["height"] > page_height + 1e-7:
        raise ValueError(f"{name} extends outside the figure canvas")
    return result


def _anchor(node, toward):
    cx, cy = node["x"] + node["width"] / 2, node["y"] + node["height"] / 2
    dx, dy = toward[0] - cx, toward[1] - cy
    if abs(dx) + abs(dy) < 1e-9:
        raise ValueError("Connected nodes must not have coincident centers")
    half_w, half_h = node["width"] / 2, node["height"] / 2
    if node["shape"] == "ellipse":
        scale = 1 / math.sqrt((dx / half_w) ** 2 + (dy / half_h) ** 2)
    elif node["shape"] == "diamond":
        scale = 1 / (abs(dx) / half_w + abs(dy) / half_h)
    else:
        scale = min(half_w / abs(dx) if dx else math.inf, half_h / abs(dy) if dy else math.inf)
    return cx + dx * scale, cy + dy * scale


def render_diagram(spec: dict, output: Path) -> dict:
    """Validate an explicit diagram specification and write a native SVG.

    Node geometry is mandatory. Labels are wrapped and, if necessary, fitted
    down to ``min_font_pt`` (default 6); an impossible label raises ValueError.
    Dashed feedback edges remain directed according to source and target.
    """
    if not isinstance(spec, dict):
        raise ValueError("Diagram specification must be an object")
    width = _number(spec.get("width_mm", 180), "width_mm", positive=True)
    height = _number(spec.get("height_mm", 110), "height_mm", positive=True)
    font_pt = _number(spec.get("font_pt", 8), "font_pt", positive=True)
    min_font_pt = _number(spec.get("min_font_pt", 6), "min_font_pt", positive=True)
    if min_font_pt > font_pt:
        raise ValueError("min_font_pt must not exceed font_pt")
    auxiliary_font_pt = max(7.0, min_font_pt)
    auxiliary_font_mm = auxiliary_font_pt * PT_MM
    title = _xml_text(spec.get("title", ""), "title")
    raw_nodes = spec.get("nodes")
    raw_edges = spec.get("edges", [])
    raw_groups = spec.get("groups", [])
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise ValueError("nodes must be a nonempty array")
    if not isinstance(raw_edges, list) or not isinstance(raw_groups, list):
        raise ValueError("edges and groups must be arrays")
    warnings, nodes, by_id = [], [], {}
    for index, item in enumerate(raw_nodes):
        if not isinstance(item, dict):
            raise ValueError("Each node must be an object")
        identifier = item.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("Every node needs a nonempty string id")
        _xml_text(identifier, "Node id")
        if identifier in by_id:
            raise ValueError(f"Duplicate node id: {identifier}")
        node = dict(item, **_box(item, f"node {identifier}", width, height))
        node["shape"] = item.get("shape", "roundrect")
        if not isinstance(node["shape"], str) or node["shape"] not in {"rect", "roundrect", "ellipse", "diamond", "cylinder"}:
            raise ValueError(f"Unsupported node shape: {node['shape']}")
        node["label"] = item.get("label", identifier)
        if not isinstance(node["label"], str) or not node["label"].strip():
            raise ValueError(f"Node {identifier} requires a nonempty text label")
        role = item.get("role", "process")
        if not isinstance(role, str) or role not in PALETTE:
            raise ValueError(f"Unknown semantic role: {role}")
        node["fill"] = _color(item.get("fill", PALETTE[role]), "node fill")
        node["svg_id"] = _identifier(identifier, "node", index)
        nodes.append(node)
        by_id[identifier] = node
    for edge in raw_edges:
        if not isinstance(edge, dict):
            raise ValueError("Each edge must be an object")
        if not isinstance(edge.get("source"), str) or not isinstance(edge.get("target"), str) or edge.get("source") not in by_id or edge.get("target") not in by_id:
            raise ValueError(f"Edge refers to a missing source/target: {edge}")
        if edge["source"] == edge["target"]:
            raise ValueError("Self-loops require a separate explicitly positioned state node")
        if not isinstance(edge.get("kind", "forward"), str) or edge.get("kind", "forward") not in {"forward", "feedback", "undirected", "bidirectional"}:
            raise ValueError(f"Unsupported edge kind: {edge.get('kind')}")
        if not isinstance(edge.get("label", ""), str):
            raise ValueError("Edge label must be a text string")
    root = ET.Element(_tag("svg"), {
        "width": f"{_fmt(width)}mm", "height": f"{_fmt(height)}mm",
        "viewBox": f"0 0 {_fmt(width)} {_fmt(height)}", "version": "1.1",
        "role": "img", "aria-labelledby": "figure-title",
    })
    _element(root, "title", id="figure-title").text = title or "Scientific diagram"
    _element(root, "desc").text = "Native editable vector diagram; connections follow the supplied specification. Dashed directed edges indicate feedback."
    definitions = _element(root, "defs")
    arrow = _element(definitions, "marker", id="edge-arrow", markerWidth="4", markerHeight="4", refX="3.5", refY="2", orient="auto", markerUnits="strokeWidth", viewBox="0 0 4 4")
    _element(arrow, "path", d="M 0 0 L 4 2 L 0 4 Z", fill="#516172")
    arrow_start = _element(definitions, "marker", id="edge-arrow-start", markerWidth="4", markerHeight="4", refX="0.5", refY="2", orient="auto", markerUnits="strokeWidth", viewBox="0 0 4 4")
    _element(arrow_start, "path", d="M 4 0 L 0 2 L 4 4 Z", fill="#516172")
    group_layer = _element(root, "g", id="diagram-groups")
    group_ids = set()
    for index, item in enumerate(raw_groups):
        if not isinstance(item, dict):
            raise ValueError("Each group must be an object")
        identifier = item.get("id", f"group-{index + 1}")
        if not isinstance(identifier, str) or not identifier.strip() or identifier in group_ids:
            raise ValueError("Group ids must be unique nonempty strings")
        group_ids.add(identifier)
        box = _box(item, f"group {identifier}", width, height)
        group = _element(group_layer, "g", id=_identifier(identifier, "group", index))
        _element(group, "rect", x=_fmt(box["x"]), y=_fmt(box["y"]), width=_fmt(box["width"]), height=_fmt(box["height"]), rx="2", fill=_color(item.get("fill", "#F7F9FC"), "group fill"), stroke="#C5CDD8", stroke_width="0.25", stroke_dasharray="1.2 0.9")
        if item.get("label"):
            _label(group, item["label"], box["x"] + 2, box["y"] + 3,
                   box["width"] - 4, min(5, box["height"] - 2), font_pt=auxiliary_font_pt,
                   min_font_pt=min_font_pt, anchor="start", fill="#536274")
    edge_layer = _element(root, "g", id="diagram-edges")
    label_layer = _element(root, "g", id="diagram-edge-labels")
    for index, edge in enumerate(raw_edges):
        source, target = by_id[edge["source"]], by_id[edge["target"]]
        kind = edge.get("kind", "forward")
        sc = (source["x"] + source["width"] / 2, source["y"] + source["height"] / 2)
        tc = (target["x"] + target["width"] / 2, target["y"] + target["height"] / 2)
        start, end = _anchor(source, tc), _anchor(target, sc)
        label_x, label_y = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2 - 1.8
        route_points = None
        if "points" in edge:
            supplied = edge["points"]
            if not isinstance(supplied, list) or len(supplied) < 1:
                raise ValueError("Edge points must be a nonempty array of [x, y] waypoints")
            route_points = []
            for point in supplied:
                if not isinstance(point, (list, tuple)) or len(point) != 2:
                    raise ValueError("Each edge waypoint must have two coordinates")
                px, py = _number(point[0], "waypoint x", nonnegative=True), _number(point[1], "waypoint y", nonnegative=True)
                if px > width or py > height:
                    raise ValueError("Edge waypoint extends outside the canvas")
                route_points.append((px, py))
            start, end = _anchor(source, route_points[0]), _anchor(target, route_points[-1])
            middle = route_points[len(route_points) // 2]
            label_x, label_y = middle[0], middle[1] - 1.8
        elif kind == "feedback":
            top, bottom = min(source["y"], target["y"]), max(source["y"] + source["height"], target["y"] + target["height"])
            if top >= (19 if title else 11):
                route_y = top - 8
                start, end = (sc[0], source["y"]), (tc[0], target["y"])
                label_y = route_y - 2
            elif height - bottom >= 11:
                route_y = bottom + 8
                start, end = (sc[0], source["y"] + source["height"]), (tc[0], target["y"] + target["height"])
                label_y = route_y + 2
            else:
                raise ValueError("Feedback route needs at least 11 mm outside its nodes, or explicit points")
            route_points = [(start[0], route_y), (end[0], route_y)]
            label_x = (start[0] + end[0]) / 2
        points = [start] + (route_points or []) + [end]
        path_data = "M " + " L ".join(f"{_fmt(x)} {_fmt(y)}" for x, y in points)
        edge_id = _identifier(f"{edge['source']}-to-{edge['target']}", "edge", index)
        group = _element(edge_layer, "g", id=edge_id)
        group.set("data-kind", kind)
        _element(group, "title").text = f"{edge['source']} → {edge['target']} ({kind})"
        path = _element(group, "path", d=path_data, fill="none", stroke="#516172", stroke_width="0.38", stroke_linejoin="round", stroke_dasharray="1.5 1" if kind == "feedback" else None)
        if kind != "undirected":
            path.set("marker-end", "url(#edge-arrow)")
        if kind == "bidirectional":
            path.set("marker-start", "url(#edge-arrow-start)")
        label = edge.get("label") or ("feedback" if kind == "feedback" else "")
        if label:
            max_width = min(55.0, width - 6)
            lines = _wrap(label, max_width, auxiliary_font_mm)
            label_w = max((_text_width(line, auxiliary_font_mm) for line in lines), default=0) + 2
            label_h = auxiliary_font_mm * (1 + (len(lines) - 1) * 1.28) + 1.2
            if label_w > width - 2 or label_h > height - 2:
                raise ValueError("Edge label cannot fit the figure canvas")
            label_x = min(max(label_x, label_w / 2 + 1), width - label_w / 2 - 1)
            label_y = min(max(label_y, label_h / 2 + 1), height - label_h / 2 - 1)
            label_group = _element(label_layer, "g", id=f"{edge_id}-label")
            _element(label_group, "rect", x=_fmt(label_x - label_w / 2), y=_fmt(label_y - label_h / 2), width=_fmt(label_w), height=_fmt(label_h), rx="0.8", fill="white", opacity="0.96")
            _label(label_group, label, label_x, label_y, label_w - 1.5, label_h,
                   font_pt=auxiliary_font_pt, min_font_pt=min_font_pt)
    node_layer = _element(root, "g", id="diagram-nodes")
    label_reports = []
    for node in nodes:
        group = _element(node_layer, "g", id=node["svg_id"])
        group.set("data-node-id", node["id"])
        _element(group, "title").text = node["label"]
        x, y, w, h = (node[key] for key in ("x", "y", "width", "height"))
        attrs = {"fill": node["fill"], "stroke": "#516172", "stroke_width": "0.32"}
        if node["shape"] in {"rect", "roundrect"}:
            _element(group, "rect", x=_fmt(x), y=_fmt(y), width=_fmt(w), height=_fmt(h), rx="1.8" if node["shape"] == "roundrect" else "0", **attrs)
        elif node["shape"] == "ellipse":
            _element(group, "ellipse", cx=_fmt(x + w / 2), cy=_fmt(y + h / 2), rx=_fmt(w / 2), ry=_fmt(h / 2), **attrs)
        elif node["shape"] == "diamond":
            points = [(x + w / 2, y), (x + w, y + h / 2), (x + w / 2, y + h), (x, y + h / 2)]
            _element(group, "polygon", points=" ".join(f"{_fmt(px)},{_fmt(py)}" for px, py in points), **attrs)
        else:
            cap = min(3, h * 0.15)
            d = f"M {_fmt(x)} {_fmt(y + cap)} A {_fmt(w / 2)} {_fmt(cap)} 0 0 1 {_fmt(x + w)} {_fmt(y + cap)} L {_fmt(x + w)} {_fmt(y + h - cap)} A {_fmt(w / 2)} {_fmt(cap)} 0 0 1 {_fmt(x)} {_fmt(y + h - cap)} Z"
            _element(group, "path", d=d, **attrs)
            _element(group, "ellipse", cx=_fmt(x + w / 2), cy=_fmt(y + cap), rx=_fmt(w / 2), ry=_fmt(cap), **attrs)
        usable_w, usable_h = w - 4, h - 4
        if node["shape"] == "diamond":
            # An inscribed rectangle keeps every line inside sloping boundaries.
            usable_w, usable_h = w * 0.56 - 2, h * 0.42 - 1
        elif node["shape"] == "ellipse":
            usable_w, usable_h = w * 0.82 - 2, h * 0.68 - 1
        elif node["shape"] == "cylinder":
            usable_h = h - 2 * min(3, h * 0.15) - 2
        label_report = _label(group, node["label"], x + w / 2, y + h / 2,
                              usable_w, usable_h, font_pt=node.get("font_pt", font_pt), min_font_pt=min_font_pt)
        label_report["node_id"] = node["id"]
        label_reports.append(label_report)
        if label_report["font_pt"] < node.get("font_pt", font_pt):
            warnings.append(f"Label for {node['id']} fitted to {label_report['font_pt']:g} pt; enlarge the node to retain the requested size")
    if title:
        title_group = _element(root, "g", id="diagram-heading")
        _label(title_group, title, width / 2, 5.5, width - 8, 7, font_pt=max(9.0, min_font_pt), min_font_pt=min_font_pt, weight="bold")
        if any(node["y"] < 10 for node in nodes):
            warnings.append("A node occupies the title region (top 10 mm); review the layout")
    for first_index, first in enumerate(nodes):
        for second in nodes[first_index + 1:]:
            if min(first["x"] + first["width"], second["x"] + second["width"]) > max(first["x"], second["x"]) and min(first["y"] + first["height"], second["y"] + second["height"]) > max(first["y"], second["y"]):
                warnings.append(f"Node bounding boxes overlap: {first['id']} and {second['id']}")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    preserved = [(element, element.text, element.tail) for text in root.iter(_tag("text")) for element in text.iter()]
    ET.indent(root, space="  ")
    for element, content, tail in preserved:
        element.text, element.tail = content, tail
    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)
    return {"output": str(output), "width_mm": width, "height_mm": height,
            "node_count": len(nodes), "edge_count": len(raw_edges), "group_count": len(raw_groups),
            "labels": label_reports, "warnings": warnings,
            "review_notes": ["Visually review routing and label placement; automatic text width is a conservative estimate, and installed fonts may differ."]}
