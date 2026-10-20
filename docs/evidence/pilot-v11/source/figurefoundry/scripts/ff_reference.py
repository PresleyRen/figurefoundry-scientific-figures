"""Local paper-figure evidence intake and explicit literature benchmark records.

Original FigureFoundry implementation using only the Python standard library.
The caller supplies saved HTML and its publication URL. Extraction reads that
file, resolves reference URLs, and returns JSON-compatible evidence.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
from urllib.parse import quote, urljoin, urlsplit, urlunsplit


_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
         "meta", "param", "source", "track", "wbr"}
_IGNORED = {"script", "style", "template", "noscript", "nav", "footer"}
_FIGURE_CLASSES = {"figure", "ltx_figure", "research-figure", "fig"}
_CAPTION_CLASSES = {"ltx_caption", "figcaption", "figure-caption", "caption"}
_CONTEXT_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6"}
_DOI = re.compile(r"10\.\d{4,9}/\S+", re.IGNORECASE)


@dataclass(eq=False)
class _Element:
    tag: str
    attrs: dict
    start: int
    parent: "_Element | None" = None
    end: int = 0
    children: list = field(default_factory=list)


class _PaperHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Element("#document", {}, 0)
        self.stack = [self.root]
        self.clock = 0

    def handle_starttag(self, tag, attrs):
        self.clock += 1
        # HTML permits omitted paragraph end tags. Keep the next block
        # separate from the preceding evidence paragraph.
        if tag in {"p", "div", "figure", "section", "h1", "h2", "h3", "h4"}:
            for index in range(len(self.stack) - 1, 0, -1):
                if self.stack[index].tag == "p":
                    for element in self.stack[index:]:
                        element.end = self.clock
                    del self.stack[index:]
                    break
                if self.stack[index].tag in {"figure", "div", "section"}:
                    break
        element = _Element(tag, dict(attrs), self.clock, self.stack[-1], self.clock)
        self.stack[-1].children.append(element)
        if tag not in _VOID:
            self.stack.append(element)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        self.clock += 1
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                for element in self.stack[index:]:
                    element.end = self.clock
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.clock += 1
        self.stack[-1].children.append(data)

    def close(self):
        super().close()
        self.clock += 1
        for element in self.stack:
            element.end = self.clock


def _classes(element):
    return set((element.attrs.get("class") or "").split())


def _hidden(element):
    return ("hidden" in element.attrs
            or (element.attrs.get("aria-hidden") or "").lower() == "true")


def _elements(element):
    """Yield visible document elements without active/template subtrees."""
    if element.tag in _IGNORED or _hidden(element):
        return
    yield element
    for child in element.children:
        if isinstance(child, _Element):
            yield from _elements(child)


def _text(element):
    if element.tag in _IGNORED or _hidden(element):
        return ""
    chunks = []
    for child in element.children:
        if isinstance(child, str):
            chunks.append(child)
        elif child.tag == "br":
            chunks.append(" ")
        else:
            chunks.append(_text(child))
    return "".join(chunks)


def _clean(text):
    return " ".join(text.split())


def _ancestors(element):
    parent = element.parent
    while parent is not None:
        yield parent
        parent = parent.parent


def _is_figure(element):
    return (element.tag == "figure" or bool(_classes(element) & _FIGURE_CLASSES)
            or element.attrs.get("role") == "figure")


def _is_caption(element):
    return element.tag == "figcaption" or bool(_classes(element) & _CAPTION_CLASSES)


def _http_url(value, base=None):
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        return None
    try:
        candidate = urljoin(base, value) if base else value
        parts = urlsplit(candidate)
        if (parts.scheme.lower() not in {"http", "https"} or not parts.hostname
                or parts.username is not None or parts.password is not None
                or any(char.isspace() for char in parts.netloc)):
            return None
        parts.port
    except ValueError:
        return None
    return candidate


def _fragment_url(source_url, dom_id):
    if not dom_id:
        return source_url
    parts = urlsplit(source_url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query,
                       quote(dom_id, safe="-._~:")))


def _srcset(value):
    """Parse ordinary URL + density/width candidates, preserving URL commas."""
    candidates = []
    remainder = value or ""
    while remainder:
        remainder = remainder.lstrip(" \t\r\n\f,")
        if not remainder:
            break
        match = re.match(r"\S+", remainder)
        raw = match.group(0)
        remainder = remainder[match.end():]
        if raw.endswith(","):
            raw, descriptor = raw.rstrip(","), ""
        else:
            descriptor, separator, remainder = remainder.partition(",")
            descriptor = descriptor.strip()
            if not separator:
                remainder = ""
        candidates.append((raw, descriptor))
    return candidates


def _image_record(element, image_id, base_url, subfigure_id=None):
    raw = element.attrs.get("src")
    attribute = "src"
    if not raw:
        raw, attribute = element.attrs.get("data-src"), "data-src"
    alternatives = []
    srcsets = [element.attrs.get("srcset", "")]
    if element.parent and element.parent.tag == "picture":
        srcsets += [node.attrs.get("srcset", "") for node in element.parent.children
                    if isinstance(node, _Element) and node.tag == "source"]
    for srcset in srcsets:
        for candidate, descriptor in _srcset(srcset):
            alternatives.append({"source_raw": candidate, "descriptor": descriptor,
                                 "source_url": _http_url(candidate, base_url)})
    source_url = _http_url(raw, base_url)
    if not raw:
        fallback = next((item for item in alternatives if item["source_url"]), None)
        if fallback:
            source_url, raw, attribute = fallback["source_url"], fallback["source_raw"], "srcset"
    alt = element.attrs.get("alt")
    alt_status = "missing" if alt is None else ("present" if alt.strip() else "empty")
    issues = []
    if source_url is None:
        issues.append("No usable HTTP(S) image source URL.")
    if alt_status != "present":
        issues.append(f"Image alt text is {alt_status}.")
    if any(item["source_url"] is None for item in alternatives):
        issues.append("Some srcset candidates have no usable HTTP(S) URL.")
    return {
        "id": image_id, "dom_id": element.attrs.get("id"),
        "source_attribute": attribute if raw else None,
        "source_raw": raw, "source_url": source_url,
        "srcset": alternatives, "alt": alt, "alt_status": alt_status,
        "title": element.attrs.get("title"),
        "width": element.attrs.get("width"), "height": element.attrs.get("height"),
        "subfigure_id": subfigure_id, "issues": issues,
    }


_REVIEW_ITEMS = (
    ("scientific-question", "What question, claim, audience and five-second takeaway does this figure serve?"),
    ("panel-role", "Identify method, data, comparison, theory bound and qualitative evidence panels."),
    ("entities-and-counts", "Record named entities, ownership, whole/detail identities, counts, units and denominators."),
    ("relations", "For each important edge, record endpoints and whether it means flow, update, influence, causation or comparison."),
    ("agent-update", "For an Agent figure, record mutable objects, frozen invariants, before/after states, update signal/operator/cadence, persistence, acceptance/rejection and stability evidence; otherwise mark not-applicable."),
    ("semantic-style", "Map method/baseline/bound/status roles to colors, markers and line styles; check these identities across the paper."),
    ("layout-and-readability", "Review anchor, reading order, labels and legends at the intended physical size, then in grayscale and relevant color-vision previews."),
    ("transferable-design", "Separate observed source features, inferred design rationale and the design choices adopted for this project."),
)


def reference_review_template():
    """Return fresh, uncompleted review fields; extraction does not infer them."""
    return {
        "status": "pending", "observations": [], "inferences": [], "decisions": [],
        "checks": [{"id": identifier, "question": question, "status": "pending",
                    "evidence": [], "notes": ""} for identifier, question in _REVIEW_ITEMS],
    }


def extract_figures(html_path, source_url, *, context_blocks=2,
                    include_ungrouped=False, encoding="utf-8"):
    """Extract grouped reference figures from a locally saved paper HTML file.

    source_url is the original HTTP(S) paper/HTML URL, used for provenance
    and relative asset resolution. Outermost figure containers are records;
    nested figures retain captions and image references as subfigures.
    include_ungrouped opts into images outside figure containers.
    Context contains nearby document paragraphs/headings, excluding captions.
    """
    if not _http_url(source_url):
        raise ValueError("source_url must be a complete HTTP(S) publication URL.")
    if isinstance(context_blocks, bool) or not isinstance(context_blocks, int) or context_blocks < 0:
        raise ValueError("context_blocks must be a nonnegative integer.")
    if not isinstance(include_ungrouped, bool):
        raise ValueError("include_ungrouped must be boolean.")
    source_url = source_url.strip()
    path = Path(html_path)
    raw = path.read_bytes()
    parser = _PaperHTML()
    parser.feed(raw.decode(encoding))
    parser.close()
    nodes = list(_elements(parser.root))
    warnings = []
    base_url = source_url
    base_node = next((node for node in nodes if node.tag == "base" and node.attrs.get("href")), None)
    if base_node:
        resolved = _http_url(base_node.attrs["href"], source_url)
        if resolved:
            base_url = resolved
        else:
            warnings.append("Invalid base href ignored; relative assets use source_url.")

    metadata = {"title": None, "authors": [], "doi": None, "canonical_url": None}
    for node in nodes:
        if node.tag == "meta":
            name = (node.attrs.get("name") or node.attrs.get("property") or "").lower()
            content = node.attrs.get("content")
            if name in {"citation_title", "dc.title"} and content:
                metadata["title"] = content
            elif name == "citation_author" and content:
                metadata["authors"].append(content)
            elif name in {"citation_doi", "dc.identifier.doi"} and content:
                metadata["doi"] = content
        elif node.tag == "title" and not metadata["title"]:
            metadata["title"] = _clean(_text(node)) or None
        elif node.tag == "link" and "canonical" in (node.attrs.get("rel") or "").split():
            metadata["canonical_url"] = _http_url(node.attrs.get("href"), base_url)

    containers = [node for node in nodes if _is_figure(node)
                  and not any(parent.tag == "head" for parent in _ancestors(node))]
    container_set = set(containers)
    outer = [node for node in containers
             if not any(parent in container_set for parent in _ancestors(node))]
    context = []
    for node in nodes:
        if node.tag in _CONTEXT_TAGS or "ltx_para" in _classes(node):
            if any(parent in container_set or parent.tag == "head" or _is_caption(parent)
                   for parent in _ancestors(node)):
                continue
            if _is_caption(node):
                continue
            # ltx_para usually wraps p elements: use each closest text block once.
            if any(child is not node and child.tag in _CONTEXT_TAGS for child in _elements(node)):
                continue
            text = _clean(_text(node))
            if text:
                context.append((node, {"tag": node.tag, "dom_id": node.attrs.get("id"), "text": text}))

    def nearby(node):
        before = [record for element, record in context if element.end <= node.start]
        after = [record for element, record in context if element.start > node.end]
        return {"before": before[-context_blocks:] if context_blocks else [],
                "after": after[:context_blocks]}

    def caption(node):
        blocks = [child for child in _elements(node) if _is_caption(child)
                  and next((parent for parent in _ancestors(child) if parent in container_set), None) is node]
        blocks = [child for child in blocks
                  if not any(descendant is not child and _is_caption(descendant)
                             for descendant in _elements(child))]
        return _clean(" ".join(_text(child) for child in blocks))

    records = []
    captured_images = set()
    for number, node in enumerate(outer, 1):
        identifier = f"fig-{number:04d}"
        descendants = list(_elements(node))
        subnodes = [child for child in descendants if child in container_set and child is not node]
        subids = {child: f"{identifier}-s{index:02d}" for index, child in enumerate(subnodes, 1)}
        images = []
        image_nodes = [child for child in descendants if child.tag == "img"]
        image_ids = {}
        for index, child in enumerate(image_nodes, 1):
            image_id = f"{identifier}-image-{index:02d}"
            parent_figure = next((parent for parent in _ancestors(child) if parent in subids), None)
            images.append(_image_record(child, image_id, base_url, subids.get(parent_figure)))
            image_ids[child] = image_id
            captured_images.add(child)
        subfigures = []
        for child in subnodes:
            parent_figure = next((parent for parent in _ancestors(child) if parent in subids), None)
            subfigures.append({
                "id": subids[child], "dom_id": child.attrs.get("id"),
                "parent_id": subids.get(parent_figure, identifier),
                "caption": caption(child),
                "image_ids": [image_ids[image] for image in image_nodes if child in set(_ancestors(image))],
            })
        caption_text = caption(node)
        label_node = next((child for child in descendants if "ltx_tag_figure" in _classes(child)
                           and next((parent for parent in _ancestors(child) if parent in container_set), None) is node), None)
        issues = []
        if not caption_text:
            issues.append("Figure caption is missing.")
        if not images:
            issues.append("Figure contains no img elements; inspect inline or linked vector content.")
        records.append({
            "id": identifier, "dom_id": node.attrs.get("id"), "kind": "figure",
            "source_url": _fragment_url(source_url, node.attrs.get("id")),
            "label": _clean(_text(label_node)) if label_node else None,
            "caption": caption_text, "images": images, "subfigures": subfigures,
            "inline_svg_present": any(child.tag == "svg" for child in descendants),
            "context": nearby(node), "issues": issues,
            "review": reference_review_template(),
        })

    ungrouped = [node for node in nodes if node.tag == "img" and node not in captured_images
                 and not any(parent.tag == "head" for parent in _ancestors(node))]
    if include_ungrouped:
        for number, node in enumerate(ungrouped, 1):
            identifier = f"ungrouped-{number:04d}"
            records.append({
                "id": identifier, "dom_id": node.attrs.get("id"), "kind": "ungrouped-image",
                "source_url": _fragment_url(source_url, node.attrs.get("id")),
                "label": None, "caption": "", "subfigures": [],
                "images": [_image_record(node, f"{identifier}-image-01", base_url)],
                "inline_svg_present": False, "context": nearby(node),
                "issues": ["Image is outside a figure container; establish its scientific role manually."],
                "review": reference_review_template(),
            })
    all_images = [image for record in records for image in record["images"]]
    return {
        "version": 1, "kind": "reference-figure-manifest",
        "source": {"file": path.name, "sha256": hashlib.sha256(raw).hexdigest(),
                   "url": source_url, "asset_base_url": base_url, "encoding": encoding,
                   "retrieval": "local-html", "metadata": metadata},
        "figures": records,
        "summary": {
            "figure_count": len(outer), "record_count": len(records),
            "image_count": len(all_images),
            "missing_alt_count": sum(image["alt_status"] == "missing" for image in all_images),
            "empty_alt_count": sum(image["alt_status"] == "empty" for image in all_images),
            "unresolved_image_count": sum(image["source_url"] is None for image in all_images),
            "ungrouped_image_count": len(ungrouped),
            "included_ungrouped": include_ungrouped,
        },
        "warnings": warnings,
    }


def _normalize_doi(value):
    if not isinstance(value, str):
        return None
    value = value.strip()
    value = re.sub(r"^doi:\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)
    return value if _DOI.fullmatch(value) else None


def validate_benchmark_record(record):
    """Validate explicit provenance for digitized/reported literature data.

    A complete record can state that digitization uncertainty is unknown;
    this produces a warning, never an invented numeric error.
    """
    errors, warnings = [], []
    if not isinstance(record, dict):
        return {"passed": False, "errors": ["record must be a JSON object."],
                "warnings": [], "record": None, "normalized_source": {}}
    try:
        json.dumps(record, allow_nan=False)
    except (TypeError, ValueError):
        return {"passed": False, "errors": ["record must contain finite JSON-compatible values."],
                "warnings": [], "record": None, "normalized_source": {}}

    def text_field(value, path):
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{path} must be a nonempty string.")
            return False
        return True

    text_field(record.get("id"), "id")
    origin = record.get("origin")
    if not isinstance(origin, str) or origin not in {"digitized-literature", "reported-literature"}:
        errors.append("origin must be digitized-literature or reported-literature.")
    source = record.get("source")
    if not isinstance(source, dict):
        errors.append("source must be an object.")
        source = {}
    doi = _normalize_doi(source.get("doi"))
    url = _http_url(source.get("url"))
    if source.get("doi") is not None and not doi:
        errors.append("source.doi must be a DOI such as 10.1234/example or its doi.org URL.")
    if source.get("url") is not None and not url:
        errors.append("source.url must be a complete HTTP(S) URL.")
    if not doi and not url:
        errors.append("source requires a valid doi or url.")
    if not any(isinstance(source.get(key), str) and source[key].strip() for key in ("figure", "table")):
        errors.append("source requires a nonempty figure or table locator.")
    for key in ("figure", "table"):
        if key in source:
            text_field(source[key], f"source.{key}")

    units = record.get("units")
    if not isinstance(units, dict) or not units:
        errors.append("units must map at least one variable or axis to its unit.")
    else:
        for variable, unit in units.items():
            text_field(variable, "units variable name")
            text_field(unit, f"units.{variable}")

    digitization = record.get("digitization")
    if origin == "digitized-literature" or digitization is not None:
        if not isinstance(digitization, dict):
            errors.append("digitization must be an object with a method.")
        else:
            text_field(digitization.get("method"), "digitization.method")
            for key in ("tool", "tool_version"):
                if key in digitization:
                    text_field(digitization[key], f"digitization.{key}")

    transformations = record.get("transformations")
    if not isinstance(transformations, list):
        errors.append("transformations must be an array; use [] when no transformation was applied.")
    else:
        for index, item in enumerate(transformations):
            if isinstance(item, str):
                text_field(item, f"transformations[{index}]")
            elif isinstance(item, dict):
                text_field(item.get("operation"), f"transformations[{index}].operation")
                text_field(item.get("details"), f"transformations[{index}].details")
            else:
                errors.append(f"transformations[{index}] must be a description or operation/details object.")

    uncertainty = record.get("uncertainty")
    if not isinstance(uncertainty, dict):
        errors.append("uncertainty must be an object with status and description.")
    else:
        status = uncertainty.get("status")
        if not isinstance(status, str) or status not in {"estimated", "reported", "unknown", "not-applicable"}:
            errors.append("uncertainty.status must be estimated, reported, unknown or not-applicable.")
        text_field(uncertainty.get("description"), "uncertainty.description")
        if status == "unknown":
            warnings.append("Digitization or reading uncertainty is explicitly unknown; retain that wording with the benchmark.")
        if "value" in uncertainty:
            value = uncertainty["value"]
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or (isinstance(value, float) and not math.isfinite(value)) or value < 0):
                errors.append("uncertainty.value must be a nonnegative finite number.")
            if not isinstance(uncertainty.get("unit"), str) or not uncertainty["unit"].strip():
                errors.append("uncertainty.unit is required when uncertainty.value is supplied.")
            if status == "unknown":
                errors.append("unknown uncertainty cannot also declare a numeric value.")

    data = record.get("data")
    if data is not None:
        if not isinstance(data, dict):
            errors.append("data must be an object when provided.")
        else:
            text_field(data.get("file"), "data.file")
            sha = data.get("sha256")
            if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", sha):
                errors.append("data.sha256 must contain 64 hexadecimal characters.")
    return {
        "passed": not errors, "errors": errors, "warnings": warnings,
        "record": deepcopy(record),
        "normalized_source": {"doi": doi, "url": url or (f"https://doi.org/{doi}" if doi else None)},
        "scope": "Literature benchmark provenance field validation.",
    }

