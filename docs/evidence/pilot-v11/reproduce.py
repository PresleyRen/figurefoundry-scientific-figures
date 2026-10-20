#!/usr/bin/env python3
"""Rebuild the selected Synthetic figure release through documented CLI commands.

Run: python reproduce.py --outdir qa/rebuild
The destination must be a new directory inside this evidence package. Existing
files are never overwritten. The active SVG is retained separately from its
frozen upstream plot specification; style refinement is explicit below.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parent
SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def refine(source, destination):
    """Only text fill and non-data grid stroke color are refined."""
    root = ET.parse(source).getroot()
    changed_text = changed_grid = 0
    for element in root.iter():
        if element.tag == f"{{{SVG}}}text":
            style = element.get("style", "")
            style = re.sub(r"(?:^|;)\s*fill\s*:[^;]*", "", style)
            element.set("style", style.rstrip(";") + "; fill: #222222")
            changed_text += 1
        elif element.tag == f"{{{SVG}}}path":
            style = element.get("style", "")
            if "stroke: #dde2e7" in style:
                element.set("style", style.replace("stroke: #dde2e7", "stroke: #c6cdd5"))
                changed_grid += 1
    if not changed_text or not changed_grid:
        raise ValueError("Expected editable text and grid paths were not found")
    if Path(destination).exists():
        raise FileExistsError(destination)
    ET.ElementTree(root).write(destination, encoding="utf-8", xml_declaration=True)
    return {"text_fill_changes": changed_text, "non_data_grid_color_changes": changed_grid,
            "data_colors": "unchanged", "geometry": "unchanged", "text_content": "unchanged"}


def grayscale_svg(source, destination):
    def gray(match):
        value = match.group(0)[1:]
        if len(value) == 3:
            value = "".join(x * 2 for x in value)
        rgb = [int(value[i:i+2], 16) / 255 for i in [0, 2, 4]]
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055)**2.4 for v in rgb]
        luminance = sum(v * w for v, w in zip(linear, [0.2126, 0.7152, 0.0722]))
        srgb = 12.92 * luminance if luminance <= 0.0031308 else 1.055 * luminance**(1/2.4) - 0.055
        g = round(255 * srgb)
        return f"#{g:02x}{g:02x}{g:02x}"
    text = Path(source).read_text()
    Path(destination).write_text(re.sub(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", gray, text))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", default="qa/rebuild")
    args = parser.parse_args()
    destination = (BASE / args.outdir).resolve()
    if not destination.is_relative_to(BASE):
        parser.error("Output must remain inside the authorized evidence package")
    destination.mkdir(parents=True, exist_ok=True)
    cli = BASE / "source/figurefoundry/scripts/figurefoundry.py"
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
               MPLCONFIGDIR=str(BASE / "runtime/matplotlib"),
               XDG_CACHE_HOME=str(BASE / "runtime/cache"),
               INKSCAPE_PROFILE_DIR=str(BASE / "runtime/inkscape"))
    content = json.loads((BASE / "specs/release-content.json").read_text())
    records = []

    def command(name, argv):
        run = subprocess.run(argv, cwd=BASE, env=env, text=True, capture_output=True)
        record = {"name": name, "command": argv, "cwd": str(BASE), "returncode": run.returncode}
        records.append(record)
        (destination / f"{name}.stdout.txt").write_text(run.stdout)
        (destination / f"{name}.stderr.txt").write_text(run.stderr)
        if run.returncode:
            save_json(destination / "reproduction-log.json", records)
            raise RuntimeError(f"Command failed: {name}: {run.stdout} {run.stderr}")
        return json.loads(run.stdout) if argv[0] == sys.executable else run.stdout

    for identifier, figure in content.items():
        prefix = destination / identifier
        upstream = destination / f"{identifier}-upstream"
        plot = command(identifier + "-plot", [sys.executable, str(cli), "plot", "--spec",
            str(BASE / figure["spec"]), "--out", str(upstream)])
        labels = prefix.with_name(identifier + "-labels.json")
        save_json(labels, plot["expected_labels"])
        before = destination / f"{identifier}-before-polish.svg"
        command(identifier + "-annotate", [sys.executable, str(cli), "annotate", str(upstream.with_suffix(".svg")),
            "--title", figure["title"], "--description", figure["alt_text"], "--out", str(before), "--min-font-pt", "7"])
        changes = refine(before, prefix.with_suffix(".svg"))
        revision = command(identifier + "-revision", [sys.executable, str(cli), "revision", str(before),
            str(prefix.with_suffix(".svg")), "--min-font-pt", "7"])
        save_json(destination / f"{identifier}-revision.json", revision)
        audit = command(identifier + "-audit", [sys.executable, str(cli), "audit", str(prefix.with_suffix(".svg")),
            "--min-font-pt", "7", "--width-mm", str(figure["width_mm"]), "--height-mm", str(figure["height_mm"]),
            "--labels", str(labels)])
        save_json(destination / f"{identifier}-audit.json", audit)
        for extension, dpi in [("png", 300), ("pdf", None)]:
            argv = ["inkscape", str(prefix.with_suffix(".svg")), f"--export-type={extension}",
                    f"--export-filename={prefix.with_suffix('.' + extension)}"]
            if dpi:
                argv.append(f"--export-dpi={dpi}")
            command(identifier + "-" + extension, argv)
        for gray in [False, True]:
            render_source = prefix.with_suffix(".svg")
            stem = identifier
            if gray:
                stem += "-grayscale"
                render_source = destination / (stem + ".svg")
                grayscale_svg(prefix.with_suffix(".svg"), render_source)
            command(stem + "-96dpi", ["inkscape", str(render_source), "--export-type=png",
                f"--export-filename={destination / (stem + '-96dpi.png')}", "--export-dpi=96"])
        save_json(destination / f"{identifier}-release-manifest.json", {
            "data_status": "Synthetic", "active_editable_source": prefix.name + ".svg",
            "upstream_spec": figure["spec"], "shared_defaults": "specs/plot-defaults.json",
            "width_mm": figure["width_mm"], "height_mm": figure["height_mm"],
            "refinement": changes, "caption": figure["caption"], "alt_text": figure["alt_text"],
            "audit_passed": audit["passed"], "style_revision_passed": revision["passed"],
            "files": {ext: {"path": prefix.name + "." + ext, "sha256": sha(prefix.with_suffix("." + ext))}
                      for ext in ["svg", "pdf", "png"]},
            "journal_status": "planning profile; no target venue specified",
            "source_snapshot": "source/figurefoundry; exact copied local runtime, see source/SNAPSHOT.json"})
        print(f"{identifier}: generated SVG/PDF/PNG; final audit and style-only revision passed", flush=True)
    save_json(destination / "reproduction-log.json", records)


if __name__ == "__main__":
    main()
