"""Conservative, offline checks for editable scientific SVG documents.

This module does not render SVG, fetch resources, repair files, or certify a
journal submission.  The supported font audit covers native text/tspan elements,
simple CSS selectors, absolute SVG lengths, and inherited affine transforms.
Unsupported mechanisms that could invalidate those checks fail explicitly.
Only the Python standard library is required.
"""

from __future__ import annotations

import math
import re
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

SVG_NS = "http://www.w3.org/2000/svg"
MAX_BYTES = 16 * 1024 * 1024
MAX_ELEMENTS = 200_000
MAX_DEPTH = 128
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
NUMBER_RE = re.compile(NUMBER)
LENGTH_RE = re.compile(rf"^({NUMBER})(%|[A-Za-z]*)$")
PATH_TOKEN_RE = re.compile(rf"[MmZzLlHhVvCcSsQqTtAa]|{NUMBER}")
UNITS = {"": 1.0, "px": 1.0, "pt": 96 / 72, "pc": 16.0,
         "in": 96.0, "cm": 96 / 2.54, "mm": 96 / 25.4, "q": 96 / 101.6}
IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
FONT_KEYWORDS = {"xx-small": 9.0, "x-small": 10.0, "small": 13.0,
                 "medium": 16.0, "large": 18.0, "x-large": 24.0,
                 "xx-large": 32.0, "xxx-large": 48.0}
INHERITED = {"visibility", "fill", "stroke", "fill-opacity", "stroke-opacity"}
PRESENTATION = INHERITED | {"font", "font-size", "font-family", "display",
                          "opacity", "stroke-width", "transform-origin"}
CSS_VALUE_ATTRIBUTES = {"fill", "stroke", "filter", "clip-path", "mask", "cursor",
                        "marker", "marker-start", "marker-mid", "marker-end", "style"}
NUMERIC_ATTRIBUTES = {"stroke-miterlimit", "pathlength", "stddeviation", "basefrequency",
                      "surfacescale", "diffuseconstant", "specularconstant", "specularexponent",
                      "limitingconeangle", "azimuth", "elevation", "pointsatx", "pointsaty",
                      "pointsatz", "k1", "k2", "k3", "k4", "kernelmatrix", "divisor",
                      "bias", "targetx", "targety", "order", "numoctaves", "seed",
                      "tablevalues", "slope", "intercept", "amplitude", "exponent"}
FORBIDDEN_ELEMENTS = {"script", "foreignobject", "image", "feimage", "iframe",
                      "object", "embed", "audio", "video", "animate", "set",
                      "animatetransform", "animatemotion", "discard"}
LENGTH_ATTRIBUTES = {"x", "y", "x1", "y1", "x2", "y2", "cx", "cy", "r", "rx",
                     "ry", "width", "height", "dx", "dy", "stroke-width",
                     "stroke-dashoffset", "markerwidth", "markerheight", "refx", "refy"}
NONNEGATIVE = {"r", "rx", "ry", "width", "height", "stroke-width",
               "markerwidth", "markerheight"}
LIMITATIONS = [
    "Static checks do not certify journal acceptance, scientific accuracy, or visual quality.",
    "Font sizes are conservative geometric estimates; installed fonts, glyph coverage, "
    "clipping, overlaps, and rendered bounds require visual inspection.",
    "Paths cannot reliably be distinguished as letters versus scientific geometry; "
    "supply every required label through expected_labels to detect missing live text.",
]


def _local(name):
    return name.rsplit("}", 1)[-1]


def _normal(text):
    return " ".join(unicodedata.normalize("NFC", text).split())


def _numbers(value):
    """Parse a complete SVG numeric list, rejecting unparsed or nonfinite input."""
    values, end = [], 0
    for match in NUMBER_RE.finditer(value):
        gap = value[end:match.start()]
        if (gap.strip(" ,\t\r\n") or gap.count(",") > 1
                or (not values and "," in gap)):
            raise ValueError("contains invalid numeric syntax")
        number = float(match.group())
        if not math.isfinite(number):
            raise ValueError("contains a nonfinite number")
        values.append(number)
        end = match.end()
    if value[end:].strip(" \t\r\n"):
        raise ValueError("contains invalid or nonfinite numeric syntax")
    return values


def _length(value, *, relative_to=None, root_font=16.0, allow_percent=False):
    value = value.strip().lower()
    if value in FONT_KEYWORDS and relative_to is not None:
        return FONT_KEYWORDS[value]
    if value in {"inherit", "unset"} and relative_to is not None:
        return relative_to
    if value in {"smaller", "larger"} and relative_to is not None:
        return relative_to * (1 / 1.2 if value == "smaller" else 1.2)
    match = LENGTH_RE.fullmatch(value)
    if not match:
        raise ValueError(f"unsupported or invalid length {value!r}")
    number, unit = float(match[1]), match[2]
    if not math.isfinite(number):
        raise ValueError("nonfinite length")
    if unit in UNITS:
        result = number * UNITS[unit]
    elif unit == "%" and relative_to is not None:
        result = number * relative_to / 100
    elif unit == "%" and allow_percent:
        result = number  # Syntax check only, never used for physical measurement.
    elif unit == "em" and relative_to is not None:
        result = number * relative_to
    elif unit == "rem" and relative_to is not None:
        result = number * root_font
    else:
        raise ValueError(f"unsupported or context-dependent unit {unit!r}")
    if not math.isfinite(result):
        raise ValueError("length overflows finite geometry")
    return result


def _multiply(left, right):
    a, b, c, d, e, f = left
    g, h, i, j, k, l = right
    result = (a*g+c*h, b*g+d*h, a*i+c*j, b*i+d*j,
              a*k+c*l+e, b*k+d*l+f)
    if not all(math.isfinite(n) for n in result):
        raise ValueError("transform overflows finite geometry")
    return result


def _transform(value):
    result, end = IDENTITY, 0
    for match in re.finditer(r"([A-Za-z]+)\s*\(([^()]*)\)", value):
        if value[end:match.start()].strip(" ,\t\r\n"):
            raise ValueError("invalid transform syntax")
        name, args = match[1].lower(), _numbers(match[2])
        if name == "matrix" and len(args) == 6:
            item = tuple(args)
        elif name == "translate" and len(args) in {1, 2}:
            item = (1, 0, 0, 1, args[0], args[1] if len(args) == 2 else 0)
        elif name == "scale" and len(args) in {1, 2}:
            item = (args[0], 0, 0, args[-1], 0, 0)
        elif name == "rotate" and len(args) in {1, 3}:
            angle = math.radians(args[0] % 360)
            c, s = math.cos(angle), math.sin(angle)
            item = (c, s, -s, c, 0, 0)
            if len(args) == 3:
                x, y = args[1:]
                item = _multiply((1, 0, 0, 1, x, y),
                                 _multiply(item, (1, 0, 0, 1, -x, -y)))
        elif name in {"skewx", "skewy"} and len(args) == 1:
            angle = math.radians(args[0] % 360)
            if abs(math.cos(angle)) < 1e-12:
                raise ValueError("singular skew transform")
            tangent = math.tan(angle)
            item = ((1, 0, tangent, 1, 0, 0) if name == "skewx"
                    else (1, tangent, 0, 1, 0, 0))
        else:
            raise ValueError(f"unsupported transform or invalid arguments: {name}")
        result = _multiply(result, item)
        end = match.end()
    if value[end:].strip(" ,\t\r\n"):
        raise ValueError("invalid transform syntax")
    return result


def _scales(matrix):
    a, b, c, d = matrix[:4]
    norm = max(abs(a), abs(b), abs(c), abs(d))
    if norm == 0:
        return 0.0, 0.0
    a, b, c, d = (v / norm for v in (a, b, c, d))
    trace = a*a + b*b + c*c + d*d
    delta = math.hypot(a*a+b*b-c*c-d*d, 2*(a*c+b*d))
    largest = math.sqrt(max(0, (trace + delta) / 2))
    smallest = abs(a*d-b*c) / largest if largest else 0.0
    return smallest * norm, largest * norm


def _validate_path(value):
    if not value.strip():
        return
    command, values, first, end = None, [], True, 0
    counts = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4,
              "Q": 4, "T": 2, "A": 7, "Z": 0}

    def validate():
        if command is None:
            return
        count = counts[command.upper()]
        if count == 0:
            if values:
                raise ValueError("closepath must not have numeric arguments")
        elif not values or len(values) % count:
            raise ValueError(f"wrong number of arguments for path command {command}")
        if command.upper() == "A":
            for offset in range(0, len(values), 7):
                if values[offset] < 0 or values[offset+1] < 0:
                    raise ValueError("negative elliptical arc radius")
                if values[offset+3] not in (0, 1) or values[offset+4] not in (0, 1):
                    raise ValueError("elliptical arc flags must be 0 or 1")

    for match in PATH_TOKEN_RE.finditer(value):
        gap = value[end:match.start()]
        if gap.strip(" ,\t\r\n") or gap.count(",") > 1 or (first and "," in gap):
            raise ValueError("invalid or nonfinite path geometry")
        token = match.group()
        if len(token) == 1 and token.isalpha():
            validate()
            if first and token.upper() != "M":
                raise ValueError("path must start with moveto")
            command, values, first = token, [], False
        else:
            if command is None:
                raise ValueError("path must start with a command")
            number = float(token)
            if not math.isfinite(number):
                raise ValueError("nonfinite path geometry")
            values.append(number)
        end = match.end()
    if value[end:].strip(" \t\r\n"):
        raise ValueError("invalid or nonfinite path geometry")
    validate()


def _selector(selector, element):
    """Match deliberately limited CSS: *, tag, #id, .class, tag.class, combinations."""
    match = re.fullmatch(r"(\*|[A-Za-z_][\w-]*)?((?:[.#][\w-]+)*)", selector)
    if not match or not selector:
        raise ValueError(f"unsupported CSS selector {selector!r}; use inline styles")
    tag, qualifiers = match.groups()
    if tag and tag != "*" and tag != _local(element.tag):
        return False, (0, 0, 0)
    ids = re.findall(r"#([\w-]+)", qualifiers)
    classes = re.findall(r"\.([\w-]+)", qualifiers)
    matches = (all(element.get("id") == ident for ident in ids)
               and all(cls in element.get("class", "").split() for cls in classes))
    return matches, (len(ids), len(classes), int(bool(tag and tag != "*")))


def _declarations(css):
    """Parse simple declarations without confusing quoted font family names."""
    parts, start, quote, depth = [], 0, None, 0
    for index, char in enumerate(css + ";"):
        if quote:
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == ";" and depth == 0:
            parts.append(css[start:index])
            start = index + 1
    if quote or depth:
        raise ValueError("unbalanced CSS declaration")
    result = []
    for part in parts:
        if not part.strip():
            continue
        if ":" not in part:
            raise ValueError("malformed CSS declaration")
        prop, value = (item.strip() for item in part.split(":", 1))
        prop = prop.lower()
        important = bool(re.search(r"\s*!important\s*$", value, re.I))
        value = re.sub(r"\s*!important\s*$", "", value, flags=re.I).strip()
        if prop == "font":
            if value.lower() in {"inherit", "unset"}:
                size = value.lower()
            else:
                match = re.search(rf"(?:^|\s)({NUMBER}(?:px|pt|pc|mm|cm|in|em|rem|%|q))"
                                  r"(?=\s|/|$)", value, re.I)
                if not match:
                    raise ValueError("unsupported font shorthand; use explicit font-size")
                size = match[1]
            result.append(("font-size", size, important))
        else:
            result.append((prop, value, important))
    return result


class _Audit:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.metrics = {"text_count": 0, "visible_text_count": 0, "path_count": 0,
                        "image_count": 0, "element_count": 0, "width_mm": None,
                        "height_mm": None, "min_font_pt": None, "max_font_pt": None,
                        "labels": [], "expected_labels_checked": 0,
                        "limitations": list(LIMITATIONS)}
        self.refs = []
        self.containment_edges = []
        self.ids = {}
        self.styles = []
        self.font_sizes = []

    def error(self, message):
        if message not in self.errors and len(self.errors) < 200:
            self.errors.append(message)

    def warning(self, message):
        if message not in self.warnings:
            self.warnings.append(message)

    def result(self):
        return {"passed": not self.errors, "errors": self.errors,
                "warnings": self.warnings, "metrics": self.metrics}

    def reference(self, value, owner, context):
        value = value.strip().strip("\"'").strip()
        if not value.startswith("#") or not value[1:] or re.search(r"\s", value):
            self.error(f"External or invalid resource reference in {context}: {value[:100]!r}")
        else:
            self.refs.append((owner, value[1:], context))

    def css_safety(self, css, owner, context):
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        if "\\" in css:
            self.error(f"Unsupported CSS escapes in {context}; use literal, local values")
        if re.search(r"@|\b(?:expression|var)\s*\(|\b(?:behavior|-moz-binding)\s*:", css, re.I):
            self.error(f"Unsupported or active CSS in {context}")
        found = list(re.finditer(r"\burl\s*\(([^()]*)\)", css, re.I))
        if len(found) != len(re.findall(r"\burl\s*\(", css, re.I)):
            self.error(f"Malformed CSS URL in {context}")
        for match in found:
            self.reference(match[1], owner, context)

    def gather(self, root):
        stack = [(root, 0, None, False)]
        while stack:
            element, depth, owner, metadata = stack.pop()
            if depth > MAX_DEPTH:
                self.error(f"SVG exceeds the supported nesting depth of {MAX_DEPTH}")
                return False
            self.metrics["element_count"] += 1
            if self.metrics["element_count"] > MAX_ELEMENTS:
                self.error(f"SVG exceeds the supported element count of {MAX_ELEMENTS}")
                return False
            tag = _local(element.tag).lower()
            context = f"<{tag}>" + (f" #{element.get('id')}" if element.get("id") else "")
            metadata = metadata or tag == "metadata"
            if tag in FORBIDDEN_ELEMENTS:
                self.error(f"Forbidden <{tag}> element; use static native SVG shapes and text")
            if tag in {"text", "path", "image"}:
                self.metrics[f"{tag}_count"] += 1
            if tag == "svg" and element is not root:
                self.error("Nested SVG viewports are unsupported by the physical font audit; "
                           "flatten to groups with explicit transforms")
            if tag == "textpath" or "textLength" in element.attrib or "lengthAdjust" in element.attrib:
                self.error("Text paths or textLength/lengthAdjust need a separate rendering audit; "
                           "use ordinary text/tspan for strict editable output")
            if not metadata and element.tag.startswith("{") and not element.tag.startswith("{"+SVG_NS+"}"):
                self.error(f"Non-SVG visual namespace in {context}")
            ident = element.get("id")
            if ident:
                if re.search(r"\s", ident):
                    self.error(f"Invalid whitespace in SVG id {ident!r}")
                if ident in self.ids:
                    self.error(f"Duplicate SVG id {ident!r}")
                self.ids[ident] = element
                if owner:
                    self.containment_edges.append((owner, ident))
                owner = ident
            for raw_name, value in element.attrib.items():
                name = _local(raw_name).lower()
                if name.startswith("on"):
                    self.error(f"Event-handler attribute {name!r} in {context}")
                if name == "base" and raw_name.startswith("{http://www.w3.org/XML/1998/namespace}"):
                    self.error(f"xml:base is forbidden because it changes resource resolution in {context}")
                if name == "href":
                    self.reference(value, owner, context)
                if re.search(r"\burl\s*\(", value, re.I) or name in CSS_VALUE_ATTRIBUTES:
                    self.css_safety(value, owner, context)
                if name in {"aria-labelledby", "aria-describedby"}:
                    for target in value.split():
                        self.refs.append((None, target, name))
                try:
                    if name in LENGTH_ATTRIBUTES:
                        parts = re.findall(rf"{NUMBER}(?:%|[A-Za-z]+)?", value)
                        remainder = re.sub(rf"{NUMBER}(?:%|[A-Za-z]+)?", "", value)
                        if not parts or remainder.strip(" ,\t\r\n"):
                            raise ValueError("invalid length list")
                        if len(parts) != 1 and name not in {"x", "y", "dx", "dy"}:
                            raise ValueError("expected one length")
                        for part in parts:
                            number = _length(part, allow_percent=True)
                            if name in NONNEGATIVE and number < 0:
                                raise ValueError("negative size or radius")
                    elif name == "d" and tag == "path":
                        _validate_path(value)
                    elif name == "points":
                        values = _numbers(value)
                        if len(values) % 2:
                            raise ValueError("points must contain coordinate pairs")
                    elif name == "viewbox":
                        values = _numbers(value)
                        if len(values) != 4 or values[2] <= 0 or values[3] <= 0:
                            raise ValueError("viewBox requires four numbers and positive dimensions")
                    elif name in NUMERIC_ATTRIBUTES or (name == "values" and tag == "fecolormatrix"):
                        if not _numbers(value):
                            raise ValueError("expected finite numeric geometry")
                    elif name == "offset" and tag == "stop":
                        offset = _length(value, allow_percent=True)
                        maximum = 100 if value.strip().endswith("%") else 1
                        if not 0 <= offset <= maximum:
                            raise ValueError("gradient offset is outside its valid range")
                    elif name in {"opacity", "fill-opacity", "stroke-opacity", "stop-opacity"}:
                        values = _numbers(value)
                        if len(values) != 1 or not 0 <= values[0] <= 1:
                            raise ValueError("opacity must be between 0 and 1")
                    elif name in {"transform", "gradienttransform", "patterntransform"}:
                        _transform(value)
                    elif name == "rotate" and tag in {"text", "tspan"}:
                        if not _numbers(value):
                            raise ValueError("empty text rotation list")
                except (ValueError, OverflowError) as exc:
                    self.error(f"Invalid {name} in {context}: {exc}")
            if tag == "style":
                css = "".join(element.itertext())
                self.css_safety(css, owner, "<style>")
                css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
                rules = list(re.finditer(r"([^{}]+)\{([^{}]*)\}", css))
                if re.sub(r"([^{}]+)\{([^{}]*)\}", "", css).strip():
                    self.error("Unsupported or malformed stylesheet; use simple selectors or inline styles")
                for rule in rules:
                    try:
                        declarations = _declarations(rule[2])
                        for selector in rule[1].split(","):
                            selector = selector.strip()
                            _selector(selector, root)
                            self.styles.append((selector, declarations))
                    except ValueError as exc:
                        self.error(str(exc))
            stack.extend((child, depth+1, owner, metadata) for child in reversed(list(element)))
        return True

    def check_references(self):
        graph = {}
        for owner, child in self.containment_edges:
            graph.setdefault(owner, set()).add(child)
        for owner, target, context in self.refs:
            if target not in self.ids:
                self.error(f"Unresolved local reference #{target} in {context}")
            if owner:
                graph.setdefault(owner, set()).add(target)
        # Iterative DFS avoids Python recursion failures on hostile reference chains.
        finished = set()
        for start in graph:
            active, pending = set(), [(start, False)]
            while pending:
                node, leaving = pending.pop()
                if leaving:
                    active.discard(node)
                    finished.add(node)
                elif node in active:
                    self.error(f"Cyclic SVG resource reference involving #{node}")
                elif node not in finished:
                    active.add(node)
                    pending.append((node, True))
                    pending.extend((child, False) for child in graph.get(node, ()))
        # A <use> can instance arbitrary objects. Fonts in referenced text are not
        # counted as native in-place runs: callers must flatten those instances.

    def style(self, element):
        ranked = {}

        def add(declarations, specificity, order):
            for index, (prop, value, important) in enumerate(declarations):
                priority = (int(important), specificity, order, index)
                if prop not in ranked or priority >= ranked[prop][0]:
                    ranked[prop] = (priority, value)

        try:
            presentation = ";".join(f"{prop}:{element.get(prop)}" for prop in PRESENTATION
                                    if prop in element.attrib)
            add(_declarations(presentation), (0, 0, 0, 0), -1)
            for index, (selector, declarations) in enumerate(self.styles):
                matches, specificity = _selector(selector, element)
                if matches:
                    add(declarations, (0,)+specificity, index)
            add(_declarations(element.get("style", "")), (1, 0, 0, 0), len(self.styles))
        except ValueError as exc:
            self.error(f"Invalid style on <{_local(element.tag)}>: {exc}")
        result = {prop: item[1] for prop, item in ranked.items()}
        for prop in {"transform", "transform-origin", "font-size-adjust", "zoom",
                     "writing-mode", "text-orientation", "width", "height", "x", "y",
                     "cx", "cy", "r", "rx", "ry", "d"} & result.keys():
            self.error(f"Unsupported CSS {prop!r}; the physical text audit cannot certify it")
        for prop in {"stroke-width", "stroke-dashoffset"} & result.keys():
            try:
                number = _length(result[prop], allow_percent=True)
                if prop == "stroke-width" and number < 0:
                    raise ValueError("negative stroke width")
            except ValueError as exc:
                self.error(f"Invalid CSS {prop}: {exc}")
        return result

    def measure_text(self, root, base_matrix):
        # Keep a shared label buffer across descendant tspans; hidden runs are
        # excluded, while tail text inherits the enclosing element's style.
        initial = {"visibility": "visible", "fill": "black", "stroke": "none",
                   "fill-opacity": "1", "stroke-opacity": "1"}
        measure_physical = base_matrix is not None
        base_matrix = base_matrix or IDENTITY

        def visit(element, matrix, inherited, font, root_font, suppressed,
                  opacity, in_defs, buffer=None):
            tag = _local(element.tag).lower()
            style = self.style(element)
            computed = dict(inherited)
            computed.update((key, value) for key, value in style.items()
                            if key in INHERITED and value not in {"inherit", "unset"})
            suppressed = suppressed or style.get("display", "").lower() == "none"
            in_defs = in_defs or tag in {"defs", "symbol", "clippath", "mask", "pattern",
                                       "marker", "metadata", "style", "title", "desc"}
            try:
                local_opacity = style.get("opacity", "1")
                values = _numbers(local_opacity)
                if len(values) != 1 or not 0 <= values[0] <= 1:
                    raise ValueError("opacity must be between 0 and 1")
                opacity *= values[0]
                if "font-size" in style:
                    font = _length(style["font-size"], relative_to=font, root_font=root_font)
                if font <= 0:
                    raise ValueError("font-size must be positive")
                if element is root:
                    root_font = font
                matrix = _multiply(matrix, _transform(element.get("transform", "")))
                for prop in ("fill-opacity", "stroke-opacity"):
                    values = _numbers(computed[prop])
                    if len(values) != 1 or not 0 <= values[0] <= 1:
                        raise ValueError(f"{prop} must be between 0 and 1")
            except (ValueError, OverflowError) as exc:
                self.error(f"Cannot measure text style/transform on <{tag}>: {exc}")
            visible = (not suppressed and not in_defs and opacity > 0
                       and computed.get("visibility", "visible").lower() not in {"hidden", "collapse"})
            fill_visible = computed.get("fill", "black").lower() not in {"none", "transparent"}
            stroke_visible = computed.get("stroke", "none").lower() not in {"none", "transparent"}
            try:
                visible = visible and ((fill_visible and float(computed["fill-opacity"]) > 0)
                                       or (stroke_visible and float(computed["stroke-opacity"]) > 0))
            except ValueError:
                visible = False
            own_buffer = tag == "text"
            if own_buffer:
                buffer = []

            def append_run(value):
                if buffer is not None and visible and value:
                    buffer.append(value)
                if measure_physical and buffer is not None and visible and value and value.strip():
                    low, high = _scales(matrix)
                    minimum, maximum = font * low, font * high
                    if not math.isfinite(minimum) or not math.isfinite(maximum):
                        self.error("Font transform overflows finite physical dimensions")
                    else:
                        self.font_sizes.append((minimum, maximum))

            append_run(element.text)
            if tag == "use":
                target = element.get("href", element.get("{http://www.w3.org/1999/xlink}href", ""))
                referenced = self.ids.get(target[1:]) if target.startswith("#") else None
                if referenced is not None and any(_local(node.tag).lower() in {"text", "tspan"}
                                                  for node in referenced.iter()):
                    self.error("Text instanced through <use> has unsupported instance font metrics; "
                               "flatten it to ordinary text/tspan")
            for child in element:
                visit(child, matrix, computed, font, root_font, suppressed,
                      opacity, in_defs, buffer)
                append_run(child.tail)
            if own_buffer:
                label = _normal("".join(buffer))
                if label:
                    self.metrics["visible_text_count"] += 1
                    self.metrics["labels"].append(label)

        visit(root, base_matrix, initial, 16.0, 16.0, False, 1.0, False)


def audit_svg(path, *, min_font_pt=5.0, width_mm=None, height_mm=None,
              require_text=True, expected_labels=None):
    """Return an auditable report without mutating the SVG.

    Root dimensions use CSS's 96 px per inch for unitless/px lengths. ``viewBox``
    and ``preserveAspectRatio`` determine user-unit to physical-point scaling.
    Inherited affine transforms use their smallest singular value for a
    conservative minimum font size. Width/height targets allow 0.1 mm or 0.1%
    tolerance, whichever is larger. Required labels are Unicode-normalized,
    whitespace-normalized exact native text-element contents (including tspans).

    ``passed`` means the implemented static checks passed; it never certifies
    journal requirements, statistics, unclipped rendering, or scientific truth.
    Unsupported font-affecting CSS and nested SVG viewports fail explicitly.
    """
    audit = _Audit()
    try:
        min_font_pt = float(min_font_pt)
        if not math.isfinite(min_font_pt) or min_font_pt < 0:
            raise ValueError("min_font_pt must be finite and nonnegative")
        targets = {}
        for key, value in (("width_mm", width_mm), ("height_mm", height_mm)):
            if value is not None:
                value = float(value)
                if not math.isfinite(value) or value <= 0:
                    raise ValueError(f"{key} target must be finite and positive")
                targets[key] = value
        if expected_labels is None:
            expected = []
        elif isinstance(expected_labels, str):
            expected = [expected_labels]
        else:
            expected = list(expected_labels)
        if any(not isinstance(item, str) or not _normal(item) for item in expected):
            raise ValueError("expected_labels must contain nonempty strings")
        source = Path(path)
        if source.stat().st_size > MAX_BYTES:
            raise ValueError(f"SVG exceeds the supported size of {MAX_BYTES} bytes")
        with source.open("rb") as handle:
            data = handle.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError(f"SVG exceeds the supported size of {MAX_BYTES} bytes")
    except (OSError, ValueError, TypeError, OverflowError) as exc:
        audit.error(f"Cannot audit SVG: {exc}")
        return audit.result()
    audit.metrics["file_size_bytes"] = len(data)
    audit.metrics["expected_labels_checked"] = len(expected)
    # Removing NULs for this scan also detects ASCII declaration keywords in
    # UTF-16/32. No entity declaration reaches ElementTree's parser.
    scanned = data.replace(b"\x00", b"")
    if re.search(br"<!\s*(?:DOCTYPE|ENTITY)\b", scanned, re.I):
        audit.error("DTD and entity declarations are forbidden; export standalone SVG without a DOCTYPE")
        return audit.result()
    if re.search(br"<\?\s*(?!xml(?:\s|\?))", scanned, re.I):
        audit.error("External or unsupported XML processing instruction")
        return audit.result()
    try:
        root = ET.fromstring(data)
    except (ET.ParseError, ValueError) as exc:
        audit.error(f"Malformed XML: {exc}")
        return audit.result()
    if root.tag not in {"svg", "{"+SVG_NS+"}svg"}:
        audit.error("The document root must be an SVG element in the SVG namespace")
        return audit.result()
    if not audit.gather(root):
        return audit.result()
    audit.check_references()
    base_matrix = IDENTITY
    try:
        physical = []
        for attribute in ("width", "height"):
            if attribute not in root.attrib:
                raise ValueError(f"root {attribute} must explicitly specify an absolute physical size")
            css_px = _length(root.get(attribute))
            if css_px <= 0:
                raise ValueError(f"root {attribute} must be positive")
            value_mm = css_px * 25.4 / 96
            audit.metrics[attribute+"_mm"] = value_mm
            physical.append(css_px * 72 / 96)
            key = attribute+"_mm"
            if key in targets and abs(value_mm-targets[key]) > max(0.1, targets[key]*0.001):
                audit.error(f"Physical {attribute} is {value_mm:.4g} mm; expected {targets[key]:.4g} mm")
        if "viewBox" in root.attrib:
            try:
                viewbox = _numbers(root.get("viewBox"))
            except ValueError as exc:
                raise ValueError(f"invalid viewBox: {exc}") from exc
            if len(viewbox) != 4 or viewbox[2] <= 0 or viewbox[3] <= 0:
                raise ValueError("viewBox needs four finite numbers with positive width and height")
            audit.metrics["viewbox"] = viewbox
            sx, sy = physical[0]/viewbox[2], physical[1]/viewbox[3]
            aspect = root.get("preserveAspectRatio", "xMidYMid meet").split()
            if aspect and aspect[0] == "defer":
                aspect = aspect[1:]
            if aspect == ["none"]:
                pass
            elif (1 <= len(aspect) <= 2
                  and re.fullmatch(r"x(?:Min|Mid|Max)Y(?:Min|Mid|Max)", aspect[0])
                  and (len(aspect) == 1 or aspect[1] in {"meet", "slice"})):
                sx = sy = (max(sx, sy) if aspect[-1] == "slice" else min(sx, sy))
            else:
                raise ValueError("unsupported preserveAspectRatio syntax")
            base_matrix = (sx, 0, 0, sy, 0, 0)
        else:
            # Without a viewBox, user units are CSS px at 96 dpi.
            base_matrix = (0.75, 0, 0, 0.75, 0, 0)
            audit.metrics["viewbox"] = None
        if not all(math.isfinite(item) for item in base_matrix):
            raise ValueError("nonfinite viewport scaling")
    except (ValueError, OverflowError) as exc:
        audit.error(f"Cannot determine physical SVG geometry: {exc}")
        base_matrix = None
    audit.measure_text(root, base_matrix)
    if require_text and not audit.metrics["visible_text_count"]:
        audit.error("No visible native SVG text was found; labels may be outlined paths or rasterized")
    actual = set(audit.metrics["labels"])
    for label in expected:
        if _normal(label) not in actual:
            audit.error(f"Required editable label is missing: {label!r}")
    if audit.font_sizes:
        smallest = min(item[0] for item in audit.font_sizes)
        largest = max(item[1] for item in audit.font_sizes)
        audit.metrics["min_font_pt"] = smallest
        audit.metrics["max_font_pt"] = largest
        if smallest + 1e-6 < min_font_pt:
            audit.error(f"Smallest effective font is {smallest:.4g} pt; minimum is {min_font_pt:.4g} pt")
    if not expected and require_text:
        audit.warning("Only the presence of editable text was checked. Supply expected_labels "
                      "to verify all intended labels and detect partially outlined exports.")
    audit.warning("Visual inspection remains required for clipping, overlap, glyph availability, "
                  "and journal-specific presentation requirements.")
    return audit.result()


__all__ = ["audit_svg"]
