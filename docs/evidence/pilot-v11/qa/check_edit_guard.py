#!/usr/bin/env python3
"""Demonstrate live SVG editing and the documented revision guard on QA copies."""
from pathlib import Path
import copy
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parents[1]
QA = BASE / "qa"
S = "{http://www.w3.org/2000/svg}"
ET.register_namespace("", S[1:-1])
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
CLI = BASE / "source/figurefoundry/scripts/figurefoundry.py"
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", XDG_CACHE_HOME=str(BASE / "runtime/cache"),
           INKSCAPE_PROFILE_DIR=str(BASE / "runtime/inkscape"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(root, name):
    path = QA / name
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    return path


master = BASE / "figures/figure-2.svg"
original_hash = sha(master)
root = ET.parse(master).getroot()
title = next(e for e in root.iter(S + "text") if e.text == "Synthetic final results and run variation")
# The native plot gives stable IDs to parent groups. Add a concrete text-node
# ID in both disposable copies to exercise the documented --allow-text-id API.
title.set("id", "pilot-edit-title")
reference = write(root, "editability-reference.svg")
edited = copy.deepcopy(root)
title = next(e for e in edited.iter() if e.get("id") == "pilot-edit-title")
title.text = "Synthetic editable text test"
page = next(e for e in edited.iter() if e.get("id") == "patch_1").find(S + "path")
assert "fill: #ffffff" in page.get("style")
page.set("style", page.get("style").replace("fill: #ffffff", "fill: #fff4ce"))
edited_path = write(edited, "editability-text-and-shape.svg")

tampered = ET.parse(master).getroot()
scatter = next(e for e in tampered.iter() if e.get("id") == "axes_2")
group = next(e for e in scatter.findall(S + "g") if e.get("id", "").startswith("PathCollection_"))
point = next(group.iter(S + "use"))
old_y = float(point.get("y"))
point.set("y", str(old_y + 10))
tamper_path = write(tampered, "negative-data-point-move.svg")

records = []


def command(name, arguments, expected_exit):
    argv = [sys.executable, str(CLI), *arguments]
    result = subprocess.run(argv, cwd=BASE, env=env, capture_output=True, text=True)
    parsed = json.loads(result.stdout)
    (QA / f"{name}.json").write_text(json.dumps(parsed, ensure_ascii=False, indent=2) + "\n")
    record = {"name": name, "command": argv, "returncode": result.returncode,
              "expected_returncode": expected_exit, "expected_result_observed": result.returncode == expected_exit,
              "report": f"qa/{name}.json"}
    records.append(record)
    assert result.returncode == expected_exit, (record, parsed)
    return parsed


command("guard-unapproved-text", ["revision", str(reference), str(edited_path), "--min-font-pt", "7"], 2)
command("guard-permitted-text", ["revision", str(reference), str(edited_path), "--allow-text-id", "pilot-edit-title", "--min-font-pt", "7"], 0)
negative = command("guard-data-point", ["revision", str(master), str(tamper_path), "--min-font-pt", "7"], 2)
assert negative["passed"] is False
render = ["inkscape", str(edited_path), "--export-type=png", f"--export-filename={QA / 'editability-text-and-shape-96dpi.png'}", "--export-dpi=96"]
result = subprocess.run(render, cwd=BASE, env=env, capture_output=True, text=True)
records.append({"name": "render-editability-copy", "command": render, "returncode": result.returncode})
assert result.returncode == 0
(QA / "editability-render.stderr.txt").write_text(result.stderr)
assert sha(master) == original_hash
report = {"passed": True, "master_sha256_before": original_hash, "master_sha256_after": sha(master),
          "master_unchanged": True, "text_node_id": "pilot-edit-title",
          "shape_edit": "Native page path fill changed from white to pale yellow in a disposable copy",
          "negative_data_edit": {"element": "first Baseline scatter use in axes_2", "property": "y", "before": old_y, "after": old_y + 10},
          "commands": records,
          "scope": "QA copies only. Negative fixtures are not scientific outputs and are not selected project variants."}
(QA / "editability-and-guard-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"passed": True, "master_unchanged": True, "expected_revision_exit_codes": [2, 0, 2]}, indent=2))
