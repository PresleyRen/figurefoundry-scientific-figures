#!/usr/bin/env python3
"""Independent stdlib check of supplied Synthetic data, statistics and SVG marks."""
from pathlib import Path
import csv
import hashlib
import json
import math
import re
import statistics
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parents[1]
NS = "{http://www.w3.org/2000/svg}"
METHODS = ["Baseline", "Context", "Proposed"]
COLORS = {"Baseline": "#666a73", "Context": "#d55e00", "Proposed": "#0072b2"}
checks = []


def check(condition, label):
    checks.append({"check": label, "passed": bool(condition)})
    if not condition:
        raise AssertionError(label)


def near(a, b, tolerance=1e-9):
    return abs(a - b) <= tolerance


def read(name):
    with (BASE / "data" / name).open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        for key in row.keys() - {"method"}:
            row[key] = float(row[key])
            check(math.isfinite(row[key]), f"{name}: finite {key}")
    return rows


def summary(rows, keys):
    grouped = {}
    for row in rows:
        grouped.setdefault(tuple(row[k] for k in keys), []).append(row["success"])
    return {
        key: {"mean": statistics.mean(values), "sd": statistics.stdev(values),
              "n": len(values), "min": min(values), "max": max(values)}
        for key, values in grouped.items()
    }


def points(path):
    # FigureFoundry/Matplotlib uses only M/L/z for these data paths.
    d = path.get("d")
    commands = re.findall(r"[A-Za-z]", re.sub(r"[eE][+-]?\d+", "", d))
    check(set(commands) <= {"M", "L", "z", "Z"}, "Data path uses M/L/Z geometry")
    values = [float(x) for x in re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?", d)]
    return list(zip(values[::2], values[1::2]))


def rect_for(root, element):
    clip = element.get("clip-path", "")
    match = re.fullmatch(r"url\(#(.+)\)", clip)
    check(match is not None, "Data marks declare a local axes clip")
    clipnode = next(e for e in root.iter() if e.get("id") == match.group(1))
    rect = clipnode.find(NS + "rect")
    return tuple(float(rect.get(k)) for k in ["x", "y", "width", "height"])


learning = read("learning.csv")
endpoints = read("endpoints.csv")
check(len(learning) == 126 and len(endpoints) == 18, "126 learning rows and 18 endpoint rows")
check({r["method"] for r in learning} == set(METHODS), "Exactly three expected methods")
check(len({(r["method"], r["seed"], r["epoch"]) for r in learning}) == 126,
      "No duplicated method/seed/epoch")
check(len({(r["method"], r["seed"]) for r in endpoints}) == 18,
      "No duplicated endpoint method/seed")
for method in METHODS:
    for seed in range(1, 7):
        check({r["epoch"] for r in learning if r["method"] == method and r["seed"] == seed}
              == set(range(0, 31, 5)), f"Complete seven epochs: {method} seed {seed}")
last = {(r["method"], r["seed"]): r["success"] for r in learning if r["epoch"] == 30}
check(all(last[(r["method"], r["seed"])] == r["success"] for r in endpoints),
      "All 18 endpoints equal epoch-30 observations exactly")
learn_summary = summary(learning, ["method", "epoch"])
end_summary = summary(endpoints, ["method"])

for name, summaries, keys in [
    ("figure-1-upstream", learn_summary, ["method", "epoch"]),
    ("figure-2-upstream", end_summary, ["method"]),
    ("figure-2-stacked-v2", end_summary, ["method"]),
]:
    manifest = json.loads((BASE / "figures" / (name + ".manifest.json")).read_text())
    stats = manifest["provenance"]["panels"][0]["statistics"]
    check(stats["independent_unit"] == "seed" and stats["uncertainty"] == "sd",
          f"{name}: independent unit and SD explicitly declared")
    for group in stats["groups"]:
        key = tuple(group[k] for k in keys)
        expected = summaries[key]
        check(group["n"] == 6 and group["observations"] == 6 and group["missing"] == 0,
              f"{name}: six complete runs in {key}")
        check(near(group["estimate"], expected["mean"])
              and near(group["lower"], expected["mean"] - expected["sd"])
              and near(group["upper"], expected["mean"] + expected["sd"]),
              f"{name}: independent mean and n-1 SD agree for {key}")

# Check actual SVG mean-curve coordinates, independently of the plot manifest.
root = ET.parse(BASE / "figures/figure-1.svg").getroot()
axes = next(e for e in root.iter() if e.get("id") == "axes_1")
curve_checks = 0
for group in axes.findall(NS + "g"):
    if not group.get("id", "").startswith("line2d_"):
        continue
    path = group.find(NS + "path")
    if path is None:
        continue
    for method, color in COLORS.items():
        if f"stroke: {color}" not in path.get("style", "").lower():
            continue
        x0, y0, width, height = rect_for(root, path)
        coords = points(path)
        check(len(coords) == 7, f"{method}: seven SVG mean vertices")
        for (px, py), epoch in zip(coords, range(0, 31, 5)):
            recovered_x = -0.8 + (px - x0) / width * 31.6
            recovered_y = 85 - (py - y0) / height * 45
            check(near(recovered_x, epoch, 1e-5)
                  and near(recovered_y, learn_summary[(method, epoch)]["mean"], 1e-5),
                  f"{method} epoch {epoch}: SVG mean vertex equals source statistic")
            curve_checks += 1
check(curve_checks == 21, "All 21 SVG curve means checked")

svg_reports = []
for name in ["figure-2-horizontal-v2", "figure-2-stacked-v2", "figure-2"]:
    root = ET.parse(BASE / "figures" / (name + ".svg")).getroot()
    scatter = next(e for e in root.iter() if e.get("id") == "axes_2")
    observed = 0
    for group in scatter.findall(NS + "g"):
        if not group.get("id", "").startswith("PathCollection_"):
            continue
        uses = list(group.iter(NS + "use"))
        check(len(uses) == 6, f"{name}: six points per scatter group")
        for use in uses:
            method = next(m for m, c in COLORS.items() if f"fill: {c}" in use.get("style", "").lower())
            clipped = next(e for e in group.iter() if e.get("clip-path"))
            x0, y0, width, height = rect_for(root, clipped)
            x = 0.5 + (float(use.get("x")) - x0) / width * 6
            y = 85 - (float(use.get("y")) - y0) / height * 35
            seed = round(x)
            check(near(x, seed, 1e-5) and near(y, last[(method, seed)], 1e-5),
                  f"{name}: SVG scatter {method} seed {seed} equals original endpoint")
            observed += 1
    check(observed == 18, f"{name}: all 18 endpoints present once")
    bars = next(e for e in root.iter() if e.get("id") == "axes_1")
    bar_count = 0
    for group in bars.findall(NS + "g"):
        path = group.find(NS + "path")
        if path is None:
            continue
        for method, color in COLORS.items():
            if f"fill: {color}" not in path.get("style", "").lower():
                continue
            x0, y0, width, height = rect_for(root, path)
            ys = [p[1] for p in points(path)]
            value = 100 - (min(ys) - y0) / height * 100
            baseline = 100 - (max(ys) - y0) / height * 100
            check(near(value, end_summary[(method,)]["mean"], 1e-5) and near(baseline, 0, 1e-5),
                  f"{name}: {method} bar height equals mean and starts at zero")
            bar_count += 1
    check(bar_count == 3, f"{name}: all three bar heights checked")
    svg_reports.append({"figure": name, "endpoint_points_checked": observed, "bar_heights_checked": bar_count})

styles = [json.loads((BASE / "figures" / (n + ".manifest.json")).read_text())["provenance"]["spec"]["style_provenance"]["style_sha256"]
          for n in ["figure-1-upstream", "figure-2-upstream", "figure-2-stacked-v2"]]
check(len(set(styles)) == 1, "Shared semantic style SHA is identical in all independent plot commands")
source_hashes = {name: hashlib.sha256((BASE / "data" / name).read_bytes()).hexdigest()
                 for name in ["learning.csv", "endpoints.csv"]}
report = {
    "data_status": "Synthetic", "passed": True, "check_count": len(checks),
    "independent_verification": "Python standard library; no FigureFoundry statistics or renderer imports",
    "source_sha256": source_hashes, "learning_rows": len(learning), "endpoint_rows": len(endpoints),
    "missing_rows": 0, "excluded_rows": 0,
    "final_summary": {key[0]: values for key, values in end_summary.items()},
    "learning_summary": [{"method": key[0], "epoch": key[1], **value} for key, value in learn_summary.items()],
    "svg_curve_vertices_checked": curve_checks, "svg_endpoint_checks": svg_reports,
    "style_sha256": styles[0], "checks": checks,
}
(BASE / "qa/independent-data-check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({k: report[k] for k in ["passed", "check_count", "final_summary", "svg_curve_vertices_checked", "svg_endpoint_checks"]}, indent=2))
