#!/usr/bin/env python3
"""Rebuild all public examples from explicitly synthetic, seeded data.

Run at repository root: python examples/generate_examples.py
The script intentionally replaces only generated demo files under examples/.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "figurefoundry-mpl"))
ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
sys.path.insert(0, str(ROOT / "skills" / "figurefoundry" / "scripts"))
import numpy as np
import pandas as pd
from ff_plots import render_plots
from ff_diagram import render_diagram
from ff_compose import compose_svgs
from ff_svg import audit_svg


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    (EXAMPLES / "data").mkdir(exist_ok=True)
    (EXAMPLES / "outputs").mkdir(exist_ok=True)
    rng = np.random.default_rng(1729)
    methods = ["Baseline", "Context", "Proposed"]
    colors = {"Baseline": "#666A73", "Context": "#D55E00", "Proposed": "#0072B2"}
    learning, endpoints = [], []
    for j, method in enumerate(methods):
        for seed in range(1, 7):
            deviation = rng.normal(0, 1.4)
            for epoch in range(0, 31, 5):
                score = 44 + 9 * j + (15 + 1.3 * j) * (1 - np.exp(-epoch / 9)) + deviation + rng.normal(0, 0.45)
                learning.append({"method": method, "seed": seed, "epoch": epoch, "success": round(score, 3)})
            endpoints.append({"method": method, "seed": seed, "success": round(score, 3),
                              "latency": round(45 + 16 * j + rng.normal(0, 2), 3)})
    cells = [{"method": method, "task": task, "success": value}
             for method, values in zip(methods, ([58, 54, 49, 61], [68, 63, 57, 72], [79, 75, 69, 81]))
             for task, value in zip(["Reasoning", "Retrieval", "Planning", "Tools"], values)]
    pareto = [{"method": method, "cost": cost, "success": score} for method, cost, score in
              [("Base", 1.0, 58), ("Context", 1.5, 68), ("Proposed", 2.0, 80), ("Large", 3.2, 81), ("Variant", 2.6, 73)]]
    for name, rows in (("learning", learning), ("endpoints", endpoints), ("tasks", cells), ("pareto", pareto)):
        pd.DataFrame(rows).to_csv(EXAMPLES / "data" / (name + ".csv"), index=False)
    line_panel = {"kind": "line", "data": "data/learning.csv", "x": "epoch", "y": "success", "hue": "method",
                  "unit": "seed", "estimator": "mean", "error": "ci95", "hue_order": methods,
                  "xlabel": "Training epoch", "ylabel": "Task success (%)", "title": "Learning dynamics",
                  "legend_loc": "lower right"}
    box_panel = {"kind": "box", "data": "data/endpoints.csv", "x": "method", "y": "success", "order": methods,
                 "xlabel": "Method", "ylabel": "Task success (%)", "title": "Independent run variation"}
    matrix_panel = {"kind": "heatmap", "data": "data/tasks.csv", "x": "task", "y": "method", "value": "success",
                    "x_order": ["Reasoning", "Retrieval", "Planning", "Tools"], "y_order": methods,
                    "xlabel": "Task family", "title": "Performance by task", "number_format": ".0f",
                    "colorbar_label": "Success (%)", "vmin": 45, "vmax": 85, "x_tick_rotation": 20}
    pareto_panel = {"kind": "pareto", "data": "data/pareto.csv", "x": "cost", "y": "success", "label": "method",
                    "xlabel": "Relative inference cost", "ylabel": "Task success (%)", "title": "Quality–cost trade-off",
                    "legend_loc": "lower right"}
    base = {"version": 1, "data_status": "synthetic", "palette": colors,
            "claim": "Demonstrate reproducible vector plots; these are synthetic values, not experimental findings."}
    benchmark = dict(base, title="Synthetic benchmark: evidence in four views",
                     figure={"width_mm": 180, "height_mm": 135, "rows": 2, "cols": 2, "font_pt": 8, "min_font_pt": 6},
                     panels=[line_panel, box_panel, matrix_panel, pareto_panel])
    line = dict(base, title="Synthetic learning curves", figure={"width_mm": 90, "height_mm": 60, "font_pt": 8, "min_font_pt": 6},
                panels=[dict(line_panel, title="")])
    distribution = dict(base, title="Synthetic run distribution", figure={"width_mm": 90, "height_mm": 60, "font_pt": 8, "min_font_pt": 6},
                        panels=[dict(box_panel, title="")])
    for name, spec in (("benchmark", benchmark), ("line", line), ("distribution", distribution)):
        save_json(EXAMPLES / (name + ".json"), spec)
        result = render_plots(spec, EXAMPLES / "outputs" / name, base_dir=EXAMPLES, overwrite=True)
        print(f"{name}: passed={result['svg_audit']['passed']} text={result['svg_audit']['metrics']['text_count']} images=0")
    asymmetric = json.loads((EXAMPLES / "asymmetric.json").read_text())
    result = render_plots(asymmetric, EXAMPLES / "outputs" / "asymmetric", base_dir=EXAMPLES, overwrite=True)
    print(f"asymmetric: passed={result['svg_audit']['passed']}")
    diagram_spec = json.loads((EXAMPLES / "diagram.json").read_text())
    render_diagram(diagram_spec, EXAMPLES / "outputs" / "diagram.svg")
    diagram_audit = audit_svg(EXAMPLES / "outputs" / "diagram.svg", min_font_pt=6,
                              expected_labels=[n["label"] for n in diagram_spec["nodes"]])
    save_json(EXAMPLES / "outputs" / "diagram.audit.json", diagram_audit)
    if not diagram_audit["passed"]:
        raise RuntimeError(diagram_audit["errors"])
    composition = json.loads((EXAMPLES / "composition.json").read_text())
    panels = [dict(p, path=str(EXAMPLES / p["path"])) for p in composition["panels"]]
    result = compose_svgs(panels, EXAMPLES / "outputs" / "composition.svg", width_mm=composition["width_mm"],
                          height_mm=composition["height_mm"], min_font_pt=6)
    # Keep the published log portable; input hashes are in panel manifests.
    result["output"] = "composition.svg"
    for panel in result.get("panels", []):
        if "path" in panel:
            panel["path"] = Path(panel["path"]).name
        if "source" in panel:
            panel["source"] = Path(panel["source"]).name
    save_json(EXAMPLES / "outputs" / "composition.audit.json", result)
    if not result["passed"]:
        raise RuntimeError(result["audit"]["errors"])
    print("diagram/composition: passed=True")


if __name__ == "__main__":
    main()
