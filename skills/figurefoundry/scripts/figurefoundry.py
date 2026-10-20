#!/usr/bin/env python3
"""FigureFoundry: journal-aware scientific figures with editable SVG masters."""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import shutil
import sys
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.1.0"


def read_json(path):
    def invalid(value):
        raise ValueError(f"Non-finite JSON number {value} is not allowed.")
    return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=invalid)


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))


def writable_output(path, overwrite):
    path = Path(path)
    if path.suffix.lower() != ".svg":
        raise ValueError("Native diagram/composition output must end in .svg")
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite {path}; select a new name or use --overwrite.")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def report_output(path, overwrite, *, protected=()):
    path = Path(path)
    if path.suffix.lower() != ".json":
        raise ValueError("Report output must end in .json")
    if path.resolve() in {Path(item).resolve() for item in protected}:
        raise ValueError("Choose a report output separate from its input files.")
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite {path}; select a new name or use --overwrite.")
    return path


def write_text_atomic(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=f".{path.name}.", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_report(path, value):
    write_text_atomic(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--version", action="version", version=f"FigureFoundry {VERSION}")
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("plot", "diagram", "compose"):
        q = sub.add_parser(name, help={"plot": "Plot data from a JSON specification",
                                      "diagram": "Render a native SVG diagram",
                                      "compose": "Compose SVG panels without rasterizing"}[name])
        q.add_argument("--spec", required=True, type=Path)
        q.add_argument("--out", required=True, type=Path)
        q.add_argument("--overwrite", action="store_true")
        if name in {"diagram", "compose"}:
            q.add_argument("--min-font-pt", type=float, default=None,
                           help="Override spec.min_font_pt; defaults to 6 when both are omitted")
    q = sub.add_parser("audit", help="Read-only SVG structure, labels and font-size audit")
    q.add_argument("svg", type=Path)
    q.add_argument("--min-font-pt", type=float, default=6)
    q.add_argument("--width-mm", type=float)
    q.add_argument("--height-mm", type=float)
    q.add_argument("--labels", type=Path, help="JSON array containing all required visible labels")
    q.add_argument("--allow-no-text", action="store_true", help="Only for deliberately unlabelled geometric assets")
    q = sub.add_parser("inspect", help="Inspect source table shape and missing values")
    q.add_argument("data", type=Path)
    q.add_argument("--sheet", default="0")
    q = sub.add_parser("journal", help="Review a source-checked journal profile's completeness")
    q.add_argument("--profile", required=True, type=Path)
    q = sub.add_parser("capabilities", help="Locate stable capability IDs, modules, docs and tests")
    q.add_argument("--query", default="")
    q = sub.add_parser("coverage", help="Locate each source Skill feature, integration and extension point")
    q.add_argument("--source", help="Source ID, for example S08")
    q.add_argument("--query", default="")
    q = sub.add_parser("atlas", help="Find specialty plots by scientific question or Chinese/English keywords")
    q.add_argument("--query", default="")
    q = sub.add_parser("palette", help="Measure text contrast and grayscale role separation")
    q.add_argument("--spec", required=True, type=Path)
    q = sub.add_parser("annotate", help="Add accessible title and description to a new editable SVG")
    q.add_argument("svg", type=Path)
    q.add_argument("--title", required=True)
    q.add_argument("--description", required=True)
    q.add_argument("--out", required=True, type=Path)
    q.add_argument("--min-font-pt", type=float, default=6)
    q.add_argument("--overwrite", action="store_true")
    q = sub.add_parser("revision", help="Compare geometry and unselected text after SVG styling edits")
    q.add_argument("before", type=Path)
    q.add_argument("after", type=Path)
    q.add_argument("--allow-text-id", action="append", default=[])
    q.add_argument("--min-font-pt", type=float, default=6)
    q = sub.add_parser("project", help="Check a figure set, select variants and export captions/alt text")
    q.add_argument("--spec", required=True, type=Path)
    q.add_argument("--out", required=True, type=Path)
    q.add_argument("--baseline", type=Path)
    q.add_argument("--notes-dir", type=Path)
    q.add_argument("--overwrite", action="store_true")
    q = sub.add_parser("references", help="Extract local paper HTML figures, captions and source evidence")
    q.add_argument("--html", required=True, type=Path)
    q.add_argument("--source-url", required=True)
    q.add_argument("--context-blocks", type=int, default=2)
    q.add_argument("--include-ungrouped", action="store_true")
    q.add_argument("--out", required=True, type=Path)
    q.add_argument("--overwrite", action="store_true")
    q = sub.add_parser("benchmark-source", help="Validate literature benchmark provenance and transformations")
    q.add_argument("--record", required=True, type=Path)
    q.add_argument("--out", type=Path)
    q.add_argument("--overwrite", action="store_true")
    q = sub.add_parser("inventory", help="Locate plot/export/style calls in Python or notebooks")
    q.add_argument("sources", nargs="+", type=Path)
    sub.add_parser("doctor", help="Report available native and optional backend dependencies")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "plot":
            from ff_plots import render_plots
            from ff_style import load_plot_spec
            result = render_plots(load_plot_spec(args.spec), args.out, base_dir=args.spec.resolve().parent,
                                  overwrite=args.overwrite)
        elif args.command == "diagram":
            from ff_diagram import render_diagram
            from ff_svg import audit_svg
            spec = read_json(args.spec)
            if not isinstance(spec, dict):
                raise ValueError("Diagram specification must be a JSON object.")
            minimum = args.min_font_pt if args.min_font_pt is not None else spec.get("min_font_pt", 6)
            if isinstance(minimum, bool):
                raise ValueError("min_font_pt must be a finite positive number.")
            minimum = float(minimum)
            if not math.isfinite(minimum) or minimum <= 0:
                raise ValueError("min_font_pt must be a finite positive number.")
            spec = dict(spec, min_font_pt=minimum)
            result = render_diagram(spec, writable_output(args.out, args.overwrite))
            labels = [n.get("label", n["id"]) for n in spec.get("nodes", [])]
            result["audit"] = audit_svg(args.out, min_font_pt=minimum, expected_labels=labels)
            result["passed"] = result["audit"]["passed"]
        elif args.command == "compose":
            from ff_compose import compose_svgs
            spec = read_json(args.spec)
            if not isinstance(spec, dict):
                raise ValueError("Composition specification must be a JSON object.")
            minimum = args.min_font_pt if args.min_font_pt is not None else spec.get("min_font_pt", 6)
            if isinstance(minimum, bool):
                raise ValueError("min_font_pt must be a finite positive number.")
            minimum = float(minimum)
            if not math.isfinite(minimum) or minimum <= 0:
                raise ValueError("min_font_pt must be a finite positive number.")
            panels = [dict(p, path=str((args.spec.resolve().parent / p["path"]).resolve())) for p in spec["panels"]]
            result = compose_svgs(panels, writable_output(args.out, args.overwrite),
                                  width_mm=spec["width_mm"], height_mm=spec["height_mm"],
                                  min_font_pt=minimum)
        elif args.command == "audit":
            from ff_svg import audit_svg
            labels = read_json(args.labels) if args.labels else None
            if labels is not None and (not isinstance(labels, list) or any(not isinstance(x, str) for x in labels)):
                raise ValueError("--labels requires a JSON array of strings.")
            result = audit_svg(args.svg, min_font_pt=args.min_font_pt, width_mm=args.width_mm,
                               height_mm=args.height_mm, require_text=not args.allow_no_text, expected_labels=labels)
        elif args.command == "inspect":
            from ff_data import read_table
            sheet = int(args.sheet) if args.sheet.isdigit() else args.sheet
            frame, source = read_table(args.data, sheet=sheet)
            result = {"source": source, "dtypes": {str(k): str(v) for k, v in frame.dtypes.items()}}
        elif args.command == "journal":
            from ff_journal import review_profile
            result = review_profile(read_json(args.profile))
        elif args.command == "capabilities":
            registry = read_json(SKILL_ROOT / "assets" / "capabilities.json")
            query = args.query.casefold()
            result = {"version": registry["version"], "matches": [entry for entry in registry["capabilities"]
                      if query in json.dumps(entry, ensure_ascii=False).casefold()]}
        elif args.command == "coverage":
            registry = read_json(SKILL_ROOT / "assets" / "source-coverage.json")
            query = args.query.casefold()
            selected = args.source.upper() if args.source else None
            result = {"version": registry["version"], "matches": [
                dict(feature, source_id=source["id"], source_name=source["name"], source_url=source["url"])
                for source in registry["sources"] if selected is None or source["id"] == selected
                for feature in source["features"]
                if query in json.dumps(feature, ensure_ascii=False).casefold()]}
        elif args.command == "atlas":
            atlas = read_json(SKILL_ROOT / "assets" / "specialty-routes.json")
            query = args.query.casefold()
            result = {"matches": [route for route in atlas["routes"]
                                   if query in json.dumps(route, ensure_ascii=False).casefold()]}
        elif args.command == "palette":
            from ff_quality import palette_report
            result = palette_report(read_json(args.spec))
        elif args.command == "annotate":
            from ff_quality import annotate_svg
            result = annotate_svg(args.svg, args.out, title=args.title, description=args.description,
                                  min_font_pt=args.min_font_pt, overwrite=args.overwrite)
        elif args.command == "revision":
            from ff_quality import compare_svg_edits
            result = compare_svg_edits(args.before, args.after, allowed_text_ids=args.allow_text_id,
                                       min_font_pt=args.min_font_pt)
        elif args.command == "project":
            from ff_project import build_project, project_documents
            protected = [args.spec] + ([args.baseline] if args.baseline else [])
            target = report_output(args.out, args.overwrite, protected=protected)
            result = build_project(read_json(args.spec), base_dir=args.spec.resolve().parent,
                                   baseline=read_json(args.baseline) if args.baseline else None)
            notes = project_documents(result) if result["passed"] and args.notes_dir else {}
            for name in notes:
                path = args.notes_dir / name
                if path.exists() and not args.overwrite:
                    raise FileExistsError(f"Refusing to overwrite {path}; select a new directory or use --overwrite.")
            write_report(target, result)
            for name, content in notes.items():
                write_text_atomic(args.notes_dir / name, content)
        elif args.command == "references":
            from ff_reference import extract_figures
            target = report_output(args.out, args.overwrite, protected=[args.html])
            result = extract_figures(args.html, args.source_url, context_blocks=args.context_blocks,
                                     include_ungrouped=args.include_ungrouped)
            write_report(target, result)
        elif args.command == "benchmark-source":
            from ff_reference import validate_benchmark_record
            target = report_output(args.out, args.overwrite, protected=[args.record]) if args.out else None
            result = validate_benchmark_record(read_json(args.record))
            if target:
                write_report(target, result)
        elif args.command == "inventory":
            from ff_inventory import inventory_sources
            result = inventory_sources(args.sources)
        else:
            required = {name: importlib.util.find_spec(name) is not None
                        for name in ("matplotlib", "numpy", "pandas", "scipy", "openpyxl")}
            result = {"version": VERSION, "native_data_plotting_available": all(required.values()),
                      "native_svg_diagrams_and_audit": True, "python_packages": required,
                      "optional_packages": {name: importlib.util.find_spec(name) is not None for name in ("seaborn", "plotly", "xlrd")},
                      "optional_executables": {name: shutil.which(name) is not None for name in ("inkscape", "Rscript", "pdflatex", "dvisvgm", "dot")},
                      "note": "Presence is not an integration test. Optional backend export still requires a final SVG audit."}
        emit(result)
        return 0 if result.get("passed", True) else 2
    except (ValueError, KeyError, TypeError, OSError, ImportError) as exc:
        emit({"passed": False, "error": str(exc), "error_type": type(exc).__name__})
        return 2


if __name__ == "__main__":
    sys.exit(main())
