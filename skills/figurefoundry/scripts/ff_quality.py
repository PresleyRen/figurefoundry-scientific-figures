"""Color diagnostics, accessible SVG descriptions and scoped edit comparison."""
from __future__ import annotations

import hashlib
import itertools
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from ff_svg import audit_svg

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
STYLE_PROPERTIES = frozenset({
    "fill", "stroke", "opacity", "fill-opacity", "stroke-opacity", "stroke-width",
    "stroke-linecap", "stroke-linejoin", "stroke-dasharray", "stroke-dashoffset",
    "font-family", "font-size", "font-style", "font-weight", "font-stretch",
    "letter-spacing", "word-spacing", "text-anchor", "dominant-baseline",
    "paint-order", "stop-color", "stop-opacity",
})


def _positive(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a positive finite number")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a positive finite number") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{name} must be a positive finite number")
    return number


def relative_luminance(color):
    """Linear-light sRGB luminance (W3C WCAG 2.2 relative-luminance formula)."""
    if not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        raise ValueError("Color diagnostics use explicit #RRGGBB sRGB colors")
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return sum(c * w for c, w in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast_ratio(first, second):
    a, b = sorted((relative_luminance(first), relative_luminance(second)))
    return (b + 0.05) / (a + 0.05)


def lightness_L_star(color):
    """CIE L* from relative Y, with the sRGB reference white normalized to 1."""
    luminance = relative_luminance(color)
    return ((24389 / 27) * luminance if luminance <= 216 / 24389
            else 116 * luminance ** (1 / 3) - 16)


def palette_report(spec):
    """Evaluate declared text contrast and report grayscale/shape distinctions."""
    if not isinstance(spec, dict) or not isinstance(spec.get("palette"), dict) or not spec["palette"]:
        raise ValueError("Palette specification needs a nonempty palette object")
    background = spec.get("background", "#FFFFFF")
    text_color = spec.get("text_color", "#222222")
    threshold = _positive(spec.get("minimum_text_contrast", 4.5), "minimum_text_contrast")
    pair_threshold = _positive(spec.get("pair_review_ratio", 1.5), "pair_review_ratio")
    if threshold > 21 or pair_threshold > 21:
        raise ValueError("sRGB contrast-ratio thresholds must be at most 21")
    rows = []
    for role, value in spec["palette"].items():
        if not isinstance(role, str) or not role.strip():
            raise ValueError("Palette roles must be nonempty strings")
        entry = {"color": value} if isinstance(value, str) else value
        if not isinstance(entry, dict) or "color" not in entry:
            raise ValueError(f"Palette role {role} needs a color")
        color = entry["color"]
        rows.append({"role": role, "color": color, "luminance": relative_luminance(color),
                     "L_star": lightness_L_star(color),
                     "background_contrast": contrast_ratio(color, background),
                     "marker": entry.get("marker"), "linestyle": entry.get("linestyle"),
                     "hatch": entry.get("hatch")})
    pairs = []
    for a, b in itertools.combinations(rows, 2):
        redundant = [k for k in ("marker", "linestyle", "hatch")
                     if a.get(k) is not None and b.get(k) is not None and a[k] != b[k]]
        ratio = contrast_ratio(a["color"], b["color"])
        pairs.append({"roles": [a["role"], b["role"]], "grayscale_contrast": ratio,
                      "delta_L": abs(a["L_star"] - b["L_star"]),
                      "redundant_channels": redundant,
                      "review_recommended": ratio < pair_threshold and not redundant})
    text_ratio = contrast_ratio(text_color, background)
    return {"passed": text_ratio >= threshold,
            "text": {"color": text_color, "background": background, "contrast": text_ratio,
                     "minimum": threshold, "passed": text_ratio >= threshold},
            "roles": rows, "pairs": pairs, "pair_review_ratio": pair_threshold,
            "method": "linear sRGB luminance; pair_review_ratio is a user-adjustable design heuristic",
            "lightness_method": "CIE L* from relative Y, reference white Y=1; delta_L is descriptive, not a journal rule or color-vision simulation",
            "formula_source": "https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html"}


def _valid_svg(path, min_font_pt):
    report = audit_svg(path, min_font_pt=min_font_pt)
    if not report["passed"]:
        raise ValueError(f"SVG audit failed for {path}: {report['errors']}")
    return ET.parse(path).getroot(), report


def annotate_svg(source, output, *, title, description, min_font_pt=6, overwrite=False):
    """Add accessible title/description without touching scientific objects."""
    if any(not isinstance(x, str) or not x.strip() for x in (title, description)):
        raise ValueError("title and description must be nonempty text")
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve():
        raise ValueError("Write accessible descriptions to a new SVG to preserve the source")
    if output.suffix.lower() != ".svg":
        raise ValueError("Accessible figure output must end in .svg")
    if output.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {output}")
    root, _ = _valid_svg(source, min_font_pt)
    ids = {e.get("id") for e in root.iter() if e.get("id")}
    label_ids = {}
    for tag, value in (("title", title), ("desc", description)):
        elements = list(root.findall(f"{{{SVG_NS}}}{tag}"))
        node = elements[0] if elements else ET.Element(f"{{{SVG_NS}}}{tag}")
        if not elements:
            root.insert(0, node)
        # Other root descriptions may still label individual groups. Preserve
        # them and their IDs; the root's new ARIA attributes select the primary
        # title/description without breaking existing local references.
        identifier = node.get("id", "ff-" + tag)
        if not node.get("id"):
            while identifier in ids:
                identifier += "-x"
        ids.add(identifier)
        node.set("id", identifier)
        for child in list(node):
            node.remove(child)
        node.text = value
        label_ids[tag] = identifier
    root.set("role", "img")
    root.set("aria-labelledby", label_ids["title"])
    root.set("aria-describedby", label_ids["desc"])
    output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)
    result = audit_svg(output, min_font_pt=min_font_pt)
    return {"passed": result["passed"], "output": str(output), "audit": result,
            "title": title, "description": description,
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest()}


def _declarations(value, *, ignore_style):
    result = []
    for part in value.split(";"):
        if not part.strip():
            continue
        if ":" not in part:
            raise ValueError("Malformed SVG style declaration")
        key, val = part.split(":", 1)
        key, val = key.strip().lower(), val.strip()
        if ignore_style and key in STYLE_PROPERTIES:
            continue
        result.append((key, val))
    return tuple(sorted(result))


def _fingerprint(element, allowed_text_ids, inherited=False, parent_text=False):
    tag = element.tag.rsplit("}", 1)[-1]
    if tag == "metadata":
        return None
    editable = inherited or element.get("id") in allowed_text_ids
    attributes = []
    for key, value in element.attrib.items():
        local = key.rsplit("}", 1)[-1]
        if local in STYLE_PROPERTIES:
            continue
        if local == "style":
            value = _declarations(value, ignore_style=True)
            if not value:
                continue
        attributes.append((key, value))
    text = element.text or ""
    if tag == "style":
        css = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        rules = re.findall(r"([^{}]+)\{([^{}]*)\}", css)
        if re.sub(r"[^{}]+\{[^{}]*\}", "", css).strip():
            raise ValueError("Edit comparison accepts simple static CSS rules")
        text = tuple((selector.strip(), _declarations(body, ignore_style=True))
                     for selector, body in rules if _declarations(body, ignore_style=True))
    elif tag in {"text", "tspan"} and editable:
        text = "<permitted text edit>"
    elif tag not in {"text", "tspan", "title", "desc"}:
        text = text.strip()
    children = tuple(v for c in element
                     if (v := _fingerprint(c, allowed_text_ids, editable, tag in {"text", "tspan"})) is not None)
    # A tspan's tail belongs to its parent text node, outside the selected
    # tspan. Preserve meaningful spaces unless the parent itself is editable.
    tail = ("<permitted text edit>" if inherited and parent_text else
            (element.tail or "") if parent_text else (element.tail or "").strip())
    return (element.tag, tuple(sorted(attributes)), text, tail, children)


def compare_svg_edits(before, after, *, allowed_text_ids=(), min_font_pt=6):
    """Accept style changes and explicitly selected text edits; freeze geometry."""
    if isinstance(allowed_text_ids, str):
        raise ValueError("allowed_text_ids must be a sequence of nonempty SVG IDs")
    try:
        allowed_text_ids = list(allowed_text_ids)
    except TypeError as exc:
        raise ValueError("allowed_text_ids must be a sequence of nonempty SVG IDs") from exc
    if any(not isinstance(x, str) or not x for x in allowed_text_ids):
        raise ValueError("allowed_text_ids must be a sequence of nonempty SVG IDs")
    allowed = set(allowed_text_ids)
    first, before_audit = _valid_svg(before, min_font_pt)
    second, after_audit = _valid_svg(after, min_font_pt)
    for root, name in ((first, "before"), (second, "after")):
        found = {e.get("id"): e for e in root.iter() if e.get("id")}
        missing = allowed - found.keys()
        if missing:
            raise ValueError(f"Unknown permitted text IDs in {name}: {sorted(missing)}")
        nontext = [identifier for identifier in allowed
                   if found[identifier].tag.rsplit("}", 1)[-1] not in {"text", "tspan"}]
        if nontext:
            raise ValueError(f"Permitted text IDs must reference text/tspan elements in {name}: {sorted(nontext)}")
    same = _fingerprint(first, allowed) == _fingerprint(second, allowed)
    return {"passed": same, "geometry_and_unselected_text_unchanged": same,
            "allowed_text_ids": sorted(allowed),
            "before_sha256": hashlib.sha256(Path(before).read_bytes()).hexdigest(),
            "after_sha256": hashlib.sha256(Path(after).read_bytes()).hexdigest(),
            "before_audit": before_audit, "after_audit": after_audit,
            "errors": [] if same else ["Geometry, structure, IDs, references or unselected text changed"]}
