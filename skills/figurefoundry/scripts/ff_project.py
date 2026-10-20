"""Manuscript figure plans, source handovers, captions and revision snapshots."""
from __future__ import annotations

import hashlib
import json
import math
import re
from copy import deepcopy
from pathlib import Path

from ff_quality import palette_report
from ff_style import resolve_plot_style
from ff_svg import audit_svg

ROLES = {"overview", "main-result", "ablation", "robustness", "efficiency", "mechanism",
         "graphical-abstract", "toc", "supplement", "diagnostic"}
SOURCE_TYPES = {"json", "python", "r", "tex", "svg", "drawio", "plotly"}
SCIENCE_FIELDS = ("question", "claim", "units", "statistics", "entities", "relations", "quantities")


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty text")
    return value


def _id(value, name):
    value = _text(value, name)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value):
        raise ValueError(f"{name} uses letters, digits, underscores and hyphens")
    return value


def _paths(value, name):
    if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
        raise ValueError(f"{name} must be an array of file paths")
    if len(value) != len(set(value)):
        raise ValueError(f"{name} contains duplicate paths")
    return value


def _path_key(path, base):
    _text(path, "source path")
    source = (base / path).resolve()
    try:
        return source.relative_to(base.resolve()).as_posix()
    except ValueError:
        return source.as_posix()


def _file(path, base, files):
    key = _path_key(path, base)
    source = (base / path).resolve()
    if not source.is_file():
        raise ValueError(f"Project source file does not exist: {path}")
    content = source.read_bytes()
    value = {"path": path, "canonical_path": key, "sha256": hashlib.sha256(content).hexdigest(),
             "bytes": len(content)}
    files[key] = value
    return value


def _entities(figure):
    entities = figure.get("entities", [])
    relations = figure.get("relations", [])
    quantities = figure.get("quantities", {})
    if not isinstance(entities, list) or any(not isinstance(e, dict) for e in entities):
        raise ValueError("entities must be an array of objects")
    if not isinstance(quantities, dict):
        raise ValueError("quantities must be an object of named finite numbers")
    for key, value in quantities.items():
        _text(key, "quantity name")
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            raise ValueError("Locked quantities must be finite numeric values")
    ids = [_id(e.get("id"), "entity id") for e in entities]
    if len(ids) != len(set(ids)):
        raise ValueError("Entity IDs must be unique within a figure")
    by_id = {entity["id"]: entity for entity in entities}
    # Validate every link before traversing any chain. Otherwise an unknown
    # parent on a later entity can escape as an unhandled StopIteration.
    for entity in entities:
        _text(entity.get("label"), "entity label")
        if entity.get("parent") is not None and entity["parent"] not in ids:
            raise ValueError(f"Unknown parent of entity {entity['id']}")
        if "representation" in entity:
            representation = entity["representation"]
            if representation not in {"whole", "part", "detail"}:
                raise ValueError("Entity representation must be whole, part, or detail")
            if representation in {"part", "detail"} and entity.get("parent") is None:
                raise ValueError("Part/detail entity representations require a parent")
            if representation == "whole" and entity.get("parent") is not None:
                raise ValueError("A whole entity representation cannot also declare a parent")
        if "quantity" in entity:
            value = entity["quantity"]
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
                raise ValueError("Entity quantity must be a nonnegative finite number")
        if "quantity_ref" in entity:
            key = _text(entity["quantity_ref"], "entity quantity_ref")
            if key not in quantities:
                raise ValueError(f"Unknown entity quantity_ref: {key}")
            if quantities[key] < 0:
                raise ValueError("Entity quantity_ref must reference a nonnegative quantity")
            if "quantity" in entity and entity["quantity"] != quantities[key]:
                raise ValueError(f"Entity {entity['id']} quantity does not match quantity_ref {key}")
    for entity in entities:
        seen, node = set(), entity
        while node.get("parent"):
            if node["id"] in seen:
                raise ValueError("Entity parent relations contain a cycle")
            seen.add(node["id"])
            node = by_id[node["parent"]]
    if not isinstance(relations, list) or any(not isinstance(r, dict) for r in relations):
        raise ValueError("relations must be an array of objects")
    for relation in relations:
        if relation.get("source") not in ids or relation.get("target") not in ids:
            raise ValueError("Scientific relations must reference declared entity IDs")
        _text(relation.get("kind"), "relation kind")


def _palette_identity(palette):
    if not isinstance(palette, dict):
        raise ValueError("Style palette must be an object")
    result = {}
    for role, value in palette.items():
        _text(role, "palette role")
        entry = {"color": value} if isinstance(value, str) else value
        if not isinstance(entry, dict):
            raise ValueError("Palette entries must be colors or style objects")
        style = {}
        for prop in ("color", "marker", "linestyle"):
            if prop not in entry or entry[prop] is None:
                continue
            setting = _text(entry[prop], f"palette {role}.{prop}")
            style[prop] = setting.upper() if prop == "color" and re.fullmatch(r"#[0-9a-fA-F]{6}", setting) else setting
        result[role] = style
    return result


def _source_style_identity(variant, base, files):
    """Inspect the actual selected JSON plot source, including shared defaults."""
    source = variant["source"]
    identity = {"checked": False, "source": source["path"], "mismatches": [],
                "scope": "Declared color/marker/linestyle in the selected JSON plot source; SVG paint is not reverse-engineered"}
    if source["type"] != "json":
        identity["reason"] = "Selected source is not a JSON plot specification"
        return identity
    path = (base / source["path"]).resolve()
    def reject(value):
        raise ValueError(f"Non-finite JSON number {value} is not allowed")
    spec = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject)
    if not isinstance(spec, dict) or not isinstance(spec.get("panels"), list) or not spec["panels"]:
        identity["reason"] = "Selected JSON source is not a nonempty native plot specification"
        return identity
    resolved = resolve_plot_style(spec, base_dir=path.parent)
    provenance = resolved["style_provenance"]
    if provenance.get("defaults"):
        defaults = path.parent / provenance["defaults"]["path"]
        _file(_path_key(str(defaults), base), base, files)
    identity.update(checked=True, style_sha256=provenance["style_sha256"],
                    palette=_palette_identity(resolved.get("palette", {})),
                    style_provenance=provenance, compared_properties=0)
    return identity


def _compare_style_identity(identity, identifier, contract, seen):
    if not identity["checked"]:
        return
    for role, style in identity["palette"].items():
        for prop, actual in style.items():
            expected = contract.get(role, {}).get(prop)
            reference = "project.style.palette"
            if expected is None and (role, prop) in seen:
                expected, reference = seen[(role, prop)]
            if expected is not None:
                identity["compared_properties"] += 1
                if actual != expected:
                    identity["mismatches"].append({"role": role, "property": prop,
                        "expected": expected, "actual": actual, "reference": reference})
            seen.setdefault((role, prop), (actual, identifier))


def build_project(spec, *, base_dir=".", baseline=None):
    """Index an explicit figure plan and compare science/data against a snapshot."""
    if not isinstance(spec, dict) or spec.get("version", 1) != 1:
        raise ValueError("Project specification must be a version-1 JSON object")
    project_id = _id(spec.get("project_id"), "project_id")
    question = _text(spec.get("question"), "project question")
    figures = spec.get("figures")
    if not isinstance(figures, list) or not figures or any(not isinstance(f, dict) for f in figures):
        raise ValueError("Project needs a nonempty figures array")
    ids = [_id(f.get("id"), "figure id") for f in figures]
    if len(ids) != len(set(ids)):
        raise ValueError("Figure IDs must be unique")
    base = Path(base_dir).resolve()
    files, evidence, science, reports, errors, warnings = {}, {}, {}, [], [], []
    frozen_sources, selected_sources, seen_styles = {}, set(), {}
    style_review = palette_report(spec["style"]) if spec.get("style") is not None else None
    style_contract = _palette_identity(spec["style"]["palette"]) if style_review else {}
    if style_review and not style_review["passed"]:
        errors.append("Project text/background contrast is below the declared threshold")
    for figure in figures:
        identifier = figure["id"]
        role = figure.get("role", "main-result")
        if role not in ROLES:
            raise ValueError(f"Unknown figure role: {role}")
        _text(figure.get("question"), f"{identifier}.question")
        _text(figure.get("claim"), f"{identifier}.claim")
        _text(figure.get("caption"), f"{identifier}.caption")
        _text(figure.get("alt_text"), f"{identifier}.alt_text")
        _entities(figure)
        evidence_paths = _paths(figure.get("evidence_files", []), "evidence_files")
        for path in evidence_paths:
            evidence[_path_key(path, base)] = _file(path, base, files)
        variants = figure.get("variants")
        if not isinstance(variants, list) or not variants or any(not isinstance(v, dict) for v in variants):
            raise ValueError(f"{identifier} needs a nonempty variants array")
        variant_ids = [_id(v.get("id"), "variant id") for v in variants]
        if len(variant_ids) != len(set(variant_ids)):
            raise ValueError(f"Duplicate variant ID in {identifier}")
        selected = figure.get("selected_variant")
        if selected not in variant_ids:
            raise ValueError(f"{identifier}.selected_variant must name an existing variant")
        variants_report = []
        for variant in variants:
            source = variant.get("source")
            if not isinstance(source, dict) or source.get("type") not in SOURCE_TYPES:
                raise ValueError("Each variant source needs a known type and path")
            source_file = _file(source.get("path"), base, files)
            frozen = _paths(source.get("frozen_upstream", []), "frozen_upstream")
            if source_file["canonical_path"] in {_path_key(path, base) for path in frozen}:
                raise ValueError("The active source cannot also be a frozen upstream file")
            for path in frozen:
                frozen_file = _file(path, base, files)
                frozen_sources[frozen_file["canonical_path"]] = frozen_file["sha256"]
            if variant["id"] == selected:
                selected_sources.add(source_file["canonical_path"])
            item = {"id": variant["id"], "source": deepcopy(source), "selected": variant["id"] == selected,
                    "rationale": str(variant.get("rationale", "")), "state": "planned"}
            if variant.get("svg"):
                svg = _file(variant["svg"], base, files)
                audit = audit_svg(base / variant["svg"], min_font_pt=figure.get("min_font_pt", 6),
                                  expected_labels=variant.get("expected_labels"))
                item.update(svg=svg, audit=audit, state="rendered")
                if not audit["passed"]:
                    errors.append(f"{identifier}/{variant['id']} SVG audit failed: {audit['errors']}")
            variants_report.append(item)
        selected_variant = next(variant for variant in variants if variant["id"] == selected)
        style_identity = _source_style_identity(selected_variant, base, files)
        _compare_style_identity(style_identity, identifier, style_contract, seen_styles)
        if style_identity["mismatches"]:
            errors.append(f"{identifier} selected plot source disagrees with shared semantic style: {style_identity['mismatches']}")
        if not style_identity["checked"]:
            warnings.append(f"{identifier} style identity not checked: {style_identity['reason']}")
        science[identifier] = deepcopy({key: figure.get(key) for key in SCIENCE_FIELDS})
        science[identifier]["evidence_files"] = [_path_key(path, base) for path in evidence_paths]
        reports.append({"id": identifier, "role": role, "question": figure["question"],
                        "claim": figure["claim"], "caption": figure["caption"], "alt_text": figure["alt_text"],
                        "selected_variant": selected, "variants": variants_report,
                        "entities": deepcopy(figure.get("entities", [])), "relations": deepcopy(figure.get("relations", [])),
                        "quantities": deepcopy(figure.get("quantities", {})), "style_identity": style_identity})
    competing_sources = selected_sources & frozen_sources.keys()
    if competing_sources:
        errors.append("Selected active sources are also frozen upstream files: " + ", ".join(sorted(competing_sources)))
    snapshot = {"project_id": project_id, "question": question, "science": science,
                "evidence": {k: v["sha256"] for k, v in evidence.items()},
                "files": {k: v["sha256"] for k, v in files.items()},
                "frozen_upstream": dict(frozen_sources)}
    revision = {"checked_against_baseline": baseline is not None, "changes": []}
    if baseline is not None:
        if not isinstance(baseline, dict) or not isinstance(baseline.get("snapshot"), dict):
            raise ValueError("Baseline must be a previous project report with a snapshot")
        if baseline.get("passed") is False:
            raise ValueError("A failed project report cannot serve as a frozen baseline")
        old = baseline["snapshot"]
        for key in ("project_id", "question", "science", "evidence"):
            if snapshot[key] != old.get(key):
                revision["changes"].append(key)
        old_files = {_path_key(path, base): digest for path, digest in old.get("files", {}).items()}
        old_frozen = {_path_key(path, base): digest for path, digest in old.get("frozen_upstream", {}).items()}
        # Compatibility with reports written before frozen_upstream was a
        # snapshot field. Their source handover records and file hashes still
        # contain the original, auditable lock identities.
        for figure in baseline.get("figures", []):
            for variant in figure.get("variants", []):
                for path in variant.get("source", {}).get("frozen_upstream", []):
                    key = _path_key(path, base)
                    if key in old_files:
                        old_frozen.setdefault(key, old_files[key])
        locks = {path: old_files.get(path, digest) for path, digest in frozen_sources.items()}
        locks.update(old_frozen)
        snapshot["frozen_upstream"] = dict(locks)
        for path, digest in locks.items():
            if path in old_frozen and path not in frozen_sources:
                revision["changes"].append("frozen_upstream_declaration_removed:" + path)
            if path in selected_sources:
                revision["changes"].append("frozen_upstream_reactivated:" + path)
            source = base / path
            if not source.is_file():
                revision["changes"].append("frozen_upstream_missing:" + path)
                continue
            current = _file(path, base, files)
            snapshot["files"][path] = current["sha256"]
            if current["sha256"] != digest:
                revision["changes"].append("frozen_upstream:" + path)
        revision["changes"] = list(dict.fromkeys(revision["changes"]))
        if revision["changes"]:
            errors.append("Revision changed frozen scientific inputs: " + ", ".join(revision["changes"]))
    return {"schema_version": 1, "passed": not errors, "errors": errors, "warnings": warnings,
            "project_id": project_id, "question": question, "style_review": style_review,
            "figures": reports, "files": list(files.values()), "snapshot": snapshot, "revision": revision}


def project_documents(report):
    """Return linked figure index, captions and alternative text as plain Markdown."""
    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ")
    index = [f"# {report['project_id']} · Figure index", "", report["question"], "",
             "| Figure | Role | Question | Selected variant | Active source |", "|---|---|---|---|---|"]
    captions, alt = ["# Figure captions", ""], ["# Figure alternative text", ""]
    for figure in report["figures"]:
        selected = next(v for v in figure["variants"] if v["selected"])
        index.append("| " + " | ".join(cell(x) for x in (figure["id"], figure["role"], figure["question"],
                                                         figure["selected_variant"], selected["source"]["path"])) + " |")
        captions.extend([f"## {figure['id']}", "", figure["caption"], ""])
        alt.extend([f"## {figure['id']}", "", figure["alt_text"], ""])
    return {"FIGURE_INDEX.md": "\n".join(index) + "\n", "CAPTIONS.md": "\n".join(captions),
            "ALT_TEXT.md": "\n".join(alt)}
