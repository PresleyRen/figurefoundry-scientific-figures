"""Compose SVG panels by copying editable vector subtrees, with scoped IDs.

No rasterization, embedded SVG images, JavaScript, network resource fetching,
or nonuniform distortion is used.  The standard-library implementation accepts
static SVG and simple (non-nested) CSS rules produced by common exporters.
"""
from __future__ import annotations

import copy
import hashlib
import math
import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)
PT_MM = 25.4 / 72.0
MAX_SOURCE_BYTES = 50 * 1024 * 1024
_NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_LENGTH = re.compile(rf"^\s*({_NUMBER})\s*(mm|cm|in|pt|pc|px|q)?\s*$", re.I)
_URL = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.I)
_FORBIDDEN = {"image", "foreignobject", "script", "iframe", "object", "embed", "video", "audio", "animate", "animatetransform", "animatemotion", "set"}


def _local(name):
    return name.rsplit("}", 1)[-1]


def _number(value, name, *, positive=False, nonnegative=False):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number, not a boolean")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    if positive and number <= 0:
        raise ValueError(f"{name} must be positive")
    if nonnegative and number < 0:
        raise ValueError(f"{name} cannot be negative")
    return number


def _fmt(value):
    return f"{float(value):.8f}".rstrip("0").rstrip(".") or "0"


def _length_px(value, name):
    match = _LENGTH.fullmatch(str(value))
    if not match:
        raise ValueError(f"{name} needs an absolute SVG length, not a percentage")
    value = _number(match.group(1), name, positive=True)
    factor = {"": 1, "px": 1, "pt": 96 / 72, "pc": 16, "mm": 96 / 25.4,
              "cm": 960 / 25.4, "in": 96, "q": 96 / 101.6}[str(match.group(2) or "").lower()]
    return value * factor


def _source_geometry(root):
    if "viewBox" in root.attrib:
        pieces = re.split(r"[\s,]+", root.attrib["viewBox"].strip())
        if len(pieces) != 4:
            raise ValueError("Source viewBox must have four finite values")
        values = tuple(_number(value, "source viewBox", positive=index >= 2) for index, value in enumerate(pieces))
    elif "width" in root.attrib and "height" in root.attrib:
        values = (0.0, 0.0, _length_px(root.attrib["width"], "source width"), _length_px(root.attrib["height"], "source height"))
    else:
        raise ValueError("Source SVG needs a viewBox or absolute width and height")
    return values


def _rewrite_urls(value, mapping):
    def replace(match):
        reference = match.group(2).strip()
        if not reference.startswith("#") or reference[1:] not in mapping:
            raise ValueError(f"Only existing local SVG URL references are supported: {reference}")
        return f"url(#{mapping[reference[1:]]})"
    result = _URL.sub(replace, value)
    if re.search(r"url\s*\(", _URL.sub("", value), re.I):
        raise ValueError("Malformed CSS url() reference")
    return result


def _rewrite_selector_ids(selector, mapping):
    for old_id in sorted(mapping, key=len, reverse=True):
        selector = re.sub(r"#" + re.escape(old_id) + r"(?![A-Za-z0-9_-])", "#" + mapping[old_id], selector)
    return selector


def _scope_stylesheet(css, mapping, panel_id, source_root_id):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    if "@" in css or "\\" in css:
        raise ValueError("CSS at-rules and escaped selectors are unsupported; export inline/static SVG styles")
    rules = list(re.finditer(r"([^{}]+)\{([^{}]*)\}", css))
    remainder = re.sub(r"([^{}]+)\{([^{}]*)\}", "", css).strip()
    if remainder:
        raise ValueError("Nested or malformed CSS is unsupported; export inline/static SVG styles")
    result = []
    for rule in rules:
        selectors, declarations = rule.group(1).strip(), rule.group(2).strip()
        if any(token in declarations.lower() for token in ("expression(", "javascript:", "behavior:", "-moz-binding")):
            raise ValueError("Active CSS is not supported")
        declarations = _rewrite_urls(declarations, mapping)
        scoped = []
        for selector in selectors.split(","):
            selector = _rewrite_selector_ids(selector.strip(), mapping)
            selector = selector.replace(":root", f"#{source_root_id}")
            # The source <svg> becomes a <g>; map a root type selector accordingly.
            selector = re.sub(r"(?<![A-Za-z0-9_.#-])svg(?=[\s>+~:.#\[]|$)", f"g#{source_root_id}", selector)
            if not re.fullmatch(r"(?:\*|[A-Za-z_][\w-]*)?(?:[.#][\w-]+)*", selector) or not selector:
                raise ValueError("Only simple SVG CSS selectors are supported; export descendant/pseudo/attribute rules as inline styles")
            selector = re.sub(r"\.([\w-]+)", lambda match: "." + panel_id + "-src-class-" + match.group(1), selector)
            # Scope on the element itself so the physical-font auditor can
            # evaluate a simple compound selector without an ancestor cascade.
            scoped.append(f"{selector}.{panel_id}-scope")
        result.append(f"{', '.join(scoped)} {{ {declarations} }}")
    return "\n".join(result)


def _audit_source(content, root, geometry, expected_labels):
    """Audit the source's own labels before composition adds any new text.

    A viewBox-only source has no physical font size until it is placed. Supply
    temporary pixel dimensions for its structural/text audit; the composition
    performs the authoritative minimum-font check after its uniform scaling.
    The original source bytes and geometry are never changed.
    """
    from ff_svg import audit_svg

    with tempfile.TemporaryDirectory(prefix="ff-compose-source-audit-") as folder:
        snapshot = Path(folder) / "source.svg"
        snapshot.write_bytes(content)
        source_audit = audit_svg(snapshot, min_font_pt=0, require_text=True,
                                 expected_labels=expected_labels)
        # Audit the original bytes first. Serializing an unchecked XML tree
        # could discard a forbidden processing instruction or declaration.
        missing_dimension_errors = {
            f"Cannot determine physical SVG geometry: root {dimension} must explicitly specify an absolute physical size"
            for dimension in ("width", "height")
        }
        if ("width" not in root.attrib or "height" not in root.attrib) and source_audit["errors"] and all(
                error in missing_dimension_errors for error in source_audit["errors"]):
            audit_root = copy.deepcopy(root)
            audit_root.set("width", f"{_fmt(geometry[2])}px")
            audit_root.set("height", f"{_fmt(geometry[3])}px")
            snapshot.write_bytes(ET.tostring(audit_root, encoding="utf-8"))
            source_audit = audit_svg(snapshot, min_font_pt=0, require_text=True,
                                     expected_labels=expected_labels)
            source_audit["warnings"].append("Source physical dimensions are unspecified; temporary source font metrics do not replace the final composition font audit")
        return source_audit


def _prepare_source(path, index, expected_labels=None):
    path = Path(path)
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ValueError(f"Cannot read SVG panel: {path}") from exc
    if size > MAX_SOURCE_BYTES:
        raise ValueError(f"SVG panel exceeds {MAX_SOURCE_BYTES // (1024 * 1024)} MiB")
    content = path.read_bytes()
    if re.search(br"<!\s*(?:DOCTYPE|ENTITY)\b", content, re.I):
        raise ValueError("DTD/entity declarations are not accepted; export a standalone SVG without a DTD")
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid SVG XML in {path}: {exc}") from exc
    if _local(root.tag).lower() != "svg" or not root.tag.startswith("{" + SVG_NS + "}"):
        raise ValueError("Each panel must be an SVG document in the SVG namespace")
    geometry = _source_geometry(root)
    source_audit = _audit_source(content, root, geometry, expected_labels)
    if not source_audit["passed"]:
        raise ValueError(f"Panel {index + 1} source failed SVG/text audit: " + "; ".join(source_audit["errors"]))
    source_sha256 = hashlib.sha256(content).hexdigest()
    prefix = f"panel-{index + 1:03d}-src-"
    mapping = {}
    for element in root.iter():
        name = _local(element.tag).lower()
        if name in _FORBIDDEN:
            raise ValueError(f"Panel contains forbidden/non-vector element <{name}>")
        if "id" in element.attrib:
            identifier = element.attrib["id"]
            if not identifier or any(character.isspace() for character in identifier):
                raise ValueError("SVG ids must be nonempty and contain no whitespace")
            if identifier in mapping:
                raise ValueError(f"Duplicate source SVG id: {identifier}")
            mapping[identifier] = prefix + identifier
        for key, value in element.attrib.items():
            if _local(key).lower().startswith("on"):
                raise ValueError("SVG event handlers are not accepted")
            if any(token in value.lower() for token in ("javascript:", "expression(", "-moz-binding")):
                raise ValueError("Active SVG/CSS content is not accepted")
    panel_id = f"panel-{index + 1:03d}"
    source_root_id = mapping.get(root.get("id"), prefix + "content-root")
    if source_root_id in mapping.values() and not root.get("id"):
        source_root_id = prefix + "content-root-generated"
        while source_root_id in mapping.values():
            source_root_id += "-x"
    for element in root.iter():
        original_classes = element.get("class", "").split()
        element.set("class", " ".join([panel_id + "-src-class-" + value for value in original_classes] + [panel_id + "-scope"]))
        for key, value in list(element.attrib.items()):
            name = _local(key).lower()
            if name == "id":
                element.set(key, mapping[value])
            elif name == "href":
                if not value.startswith("#") or value[1:] not in mapping:
                    raise ValueError("SVG href attributes must reference an existing local id")
                element.set(key, "#" + mapping[value[1:]])
            elif name in {"aria-labelledby", "aria-describedby"}:
                refs = value.split()
                if any(reference not in mapping for reference in refs):
                    raise ValueError(f"Unresolved accessibility reference: {value}")
                element.set(key, " ".join(mapping[reference] for reference in refs))
            else:
                element.set(key, _rewrite_urls(value, mapping))
        if _local(element.tag).lower() == "style":
            element.text = _scope_stylesheet(element.text or "", mapping, panel_id, source_root_id)
    return root, geometry, mapping, source_root_id, panel_id, source_audit, source_sha256


def compose_svgs(panels: list[dict], output, *, width_mm, height_mm, min_font_pt=5.0) -> dict:
    """Place static SVG panels into one editable native vector SVG.

    Each panel uses ``path,x_mm,y_mm,width_mm,height_mm`` and optional ``label``.
    ``expected_labels`` (or its ``labels`` alias) supplies the source's complete
    editable-label inventory. Each source must contain its own native text;
    headings and labels in neighboring panels cannot satisfy this requirement.
    A labelled panel reserves a 5 mm heading band. Contents are uniformly scaled
    and centered in the remaining rectangle. Final font failures appear in
    ``audit`` and set ``passed=False``; input errors raise before writing output.
    """
    width_mm = _number(width_mm, "width_mm", positive=True)
    height_mm = _number(height_mm, "height_mm", positive=True)
    min_font_pt = _number(min_font_pt, "min_font_pt", positive=True)
    if not isinstance(panels, list) or not panels:
        raise ValueError("panels must be a nonempty array")
    output = Path(output)
    prepared, warnings = [], []
    for index, panel in enumerate(panels):
        if not isinstance(panel, dict):
            raise ValueError("Each panel must be an object")
        missing = [key for key in ("path", "x_mm", "y_mm", "width_mm", "height_mm") if key not in panel]
        if missing:
            raise ValueError(f"Panel {index + 1} is missing: {', '.join(missing)}")
        if not isinstance(panel["path"], (str, Path)):
            raise ValueError("Panel path must be a filesystem path")
        if Path(panel["path"]).resolve() == output.resolve():
            raise ValueError("Composition output must not overwrite a source panel")
        placement = {key: _number(panel[key], f"panel {index + 1} {key}", positive=key in {"width_mm", "height_mm"}, nonnegative=key in {"x_mm", "y_mm"}) for key in ("x_mm", "y_mm", "width_mm", "height_mm")}
        if placement["x_mm"] + placement["width_mm"] > width_mm + 1e-7 or placement["y_mm"] + placement["height_mm"] > height_mm + 1e-7:
            raise ValueError(f"Panel {index + 1} extends outside the composition canvas")
        label = panel.get("label", "")
        if not isinstance(label, str):
            raise ValueError("Panel labels must be text strings")
        label_band = 5.0 if label else 0.0
        if placement["height_mm"] <= label_band:
            raise ValueError("Panel height must exceed the label heading band")
        if label and len(label) * 9 * PT_MM > placement["width_mm"] - 2:
            raise ValueError("Panel label is too long; use a short letter or identifier")
        required_labels = []
        for field in ("expected_labels", "labels"):
            if field in panel:
                values = panel[field]
                if not isinstance(values, (list, tuple)) or any(not isinstance(value, str) or not value.strip() for value in values):
                    raise ValueError(f"Panel {index + 1} {field} must be an array of nonempty strings")
                required_labels.extend(values)
        required_labels = list(dict.fromkeys(required_labels))
        source, viewbox, mapping, source_root_id, panel_id, source_audit, source_sha256 = _prepare_source(
            panel["path"], index, required_labels or None)
        if not required_labels:
            warnings.append(f"Panel {index + 1}: no complete expected_labels inventory supplied; source native-text presence is checked, but partially outlined labels need review")
        vx, vy, vw, vh = viewbox
        scale_x = placement["width_mm"] / vw
        scale_y = (placement["height_mm"] - label_band) / vh
        scale = min(scale_x, scale_y)
        tx = placement["x_mm"] + (placement["width_mm"] - vw * scale) / 2
        ty = placement["y_mm"] + label_band + (placement["height_mm"] - label_band - vh * scale) / 2
        if abs(scale_x - scale_y) > 1e-6 * max(scale_x, scale_y):
            warnings.append(f"Panel {index + 1}: requested box has a different aspect ratio; uniform scaling preserves geometry and adds whitespace")
        prepared.append({"source": source, "viewbox": viewbox, "mapping": mapping,
                         "source_root_id": source_root_id, "panel_id": panel_id,
                         "placement": placement, "label": label, "scale": scale,
                         "tx": tx, "ty": ty, "source_path": str(Path(panel["path"])),
                         "source_audit": source_audit, "source_sha256": source_sha256,
                         "expected_labels": required_labels})
    for index, first in enumerate(prepared):
        a = first["placement"]
        for second_index, second in enumerate(prepared[index + 1:], index + 1):
            b = second["placement"]
            if min(a["x_mm"] + a["width_mm"], b["x_mm"] + b["width_mm"]) > max(a["x_mm"], b["x_mm"]) and min(a["y_mm"] + a["height_mm"], b["y_mm"] + b["height_mm"]) > max(a["y_mm"], b["y_mm"]):
                warnings.append(f"Panel rectangles {index + 1} and {second_index + 1} overlap; visually review intentional overlap")
    root = ET.Element(f"{{{SVG_NS}}}svg", {
        "width": f"{_fmt(width_mm)}mm", "height": f"{_fmt(height_mm)}mm",
        "viewBox": f"0 0 {_fmt(width_mm)} {_fmt(height_mm)}", "version": "1.1",
        "role": "img", "aria-labelledby": "composition-title",
    })
    ET.SubElement(root, f"{{{SVG_NS}}}title", {"id": "composition-title"}).text = "Scientific figure panel composition"
    definitions = ET.SubElement(root, f"{{{SVG_NS}}}defs")
    reports = []
    for item in prepared:
        placement, source = item["placement"], item["source"]
        panel_group = ET.SubElement(root, f"{{{SVG_NS}}}g", {"id": item["panel_id"]})
        if item["label"]:
            label = ET.SubElement(panel_group, f"{{{SVG_NS}}}text", {
                "id": item["panel_id"] + "-heading", "x": _fmt(placement["x_mm"] + 1),
                "y": _fmt(placement["y_mm"] + 3.5), "font-family": "Arial, Helvetica, sans-serif",
                "font-size": _fmt(9 * PT_MM), "font-weight": "bold", "fill": "#22313F",
            })
            label.text = item["label"]
        vx, vy, vw, vh = item["viewbox"]
        outer = ET.SubElement(panel_group, f"{{{SVG_NS}}}g", {
            "transform": f"translate({_fmt(item['tx'])} {_fmt(item['ty'])}) scale({_fmt(item['scale'])}) translate({_fmt(-vx)} {_fmt(-vy)})",
        })
        viewport_id = item["panel_id"] + "-viewport"
        clip = ET.SubElement(definitions, f"{{{SVG_NS}}}clipPath", {"id": viewport_id, "clipPathUnits": "userSpaceOnUse"})
        ET.SubElement(clip, f"{{{SVG_NS}}}rect", {"x": _fmt(vx), "y": _fmt(vy), "width": _fmt(vw), "height": _fmt(vh)})
        viewport = ET.SubElement(outer, f"{{{SVG_NS}}}g", {"clip-path": f"url(#{viewport_id})"})
        root_attributes = {key: value for key, value in source.attrib.items()
                           if _local(key) not in {"width", "height", "viewBox", "version", "x", "y", "preserveAspectRatio", "overflow"}}
        root_attributes["id"] = item["source_root_id"]
        # The initial SVG font size is 16 user units.  Keep that initial value
        # when the source document's root viewport becomes a transformed group.
        root_attributes.setdefault("font-size", "16")
        content = ET.SubElement(viewport, f"{{{SVG_NS}}}g", root_attributes)
        for child in source:
            content.append(copy.deepcopy(child))
        reports.append({"source": item["source_path"], "source_sha256": item["source_sha256"],
                        "source_audit": item["source_audit"], "expected_labels": item["expected_labels"],
                        "id": item["panel_id"],
                        "placement": placement, "uniform_scale": item["scale"],
                        "content_bounds_mm": {"x": item["tx"], "y": item["ty"], "width": vw * item["scale"], "height": vh * item["scale"]},
                        "renamed_ids": len(item["mapping"]), "label": item["label"]})
    output.parent.mkdir(parents=True, exist_ok=True)
    preserved = [(element, element.text, element.tail) for text in root.iter(f"{{{SVG_NS}}}text") for element in text.iter()]
    ET.indent(root, space="  ")
    for element, content, tail in preserved:
        element.text, element.tail = content, tail
    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)
    final_labels = list(dict.fromkeys(
        label for item in prepared
        for label in item["source_audit"]["metrics"]["labels"] + item["expected_labels"] + [item["label"]]
        if label.strip()))
    try:
        from ff_svg import audit_svg
    except ImportError:
        audit = {"passed": False, "errors": [], "warnings": ["ff_svg is unavailable; final physical font sizes require review"], "metrics": {}}
        warnings.append("Final font audit is unavailable; do not claim submission readiness")
    else:
        audit = audit_svg(output, min_font_pt=min_font_pt, width_mm=width_mm, height_mm=height_mm,
                          expected_labels=final_labels)
    return {"output": str(output), "width_mm": width_mm, "height_mm": height_mm,
            "panels": reports, "warnings": warnings, "expected_labels": final_labels, "audit": audit,
            "passed": bool(audit.get("passed", False)),
            "review_notes": ["Inspect the complete composition at its final physical size for collisions, whitespace, clipping, and readable labels."]}
