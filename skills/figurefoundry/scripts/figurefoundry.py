#!/usr/bin/env python3
"""FigureFoundry: journal-aware scientific figures with editable SVG masters."""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import shutil
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0"


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
    sub.add_parser("doctor", help="Report available native and optional backend dependencies")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "plot":
            from ff_plots import render_plots
            result = render_plots(read_json(args.spec), args.out, base_dir=args.spec.resolve().parent,
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
