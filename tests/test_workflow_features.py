"""Independent known-answer checks for quality review and project handovers.

Fixtures are synthetic. No TeX/R/external service is executed; ordinary local
file edits deliberately exercise the immutable scientific snapshot contract.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "figurefoundry" / "scripts"
sys.path.insert(0, str(SCRIPTS))
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "ff-workflow-tests-mpl"))

from ff_project import build_project, project_documents
from ff_quality import annotate_svg, compare_svg_edits, contrast_ratio, palette_report
from ff_svg import audit_svg

SVG = "{http://www.w3.org/2000/svg}"
CLI = SCRIPTS / "figurefoundry.py"


class WorkflowFeatureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="ff-workflow-features-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)

    def write(self, name, content):
        path = self.base / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def json(self, name, value):
        return self.write(name, json.dumps(value, ensure_ascii=False, indent=2))

    def svg(self, name="plot.svg", *, extra="", nested_text=False):
        text = ('<text id="response" x="8" y="12" font-size="3"><tspan id="dose">5</tspan> mg'
                '<tspan id="unit"> / mL</tspan></text>' if nested_text else
                '<text id="response" x="8" y="12" font-size="3">AI/ML response</text>')
        return self.write(name,
            '<svg xmlns="http://www.w3.org/2000/svg" width="80mm" height="50mm" viewBox="0 0 80 50">'
            + extra + '<g id="plot"><path id="curve" d="M 8 40 L 40 25 L 72 10" stroke="#0072B2" fill="none"/>'
            + text + '<text id="fixed" x="8" y="47" font-size="3">Dose (mg)</text></g></svg>')

    def edit(self, source, name, change):
        root = ET.parse(source).getroot()
        change(root)
        target = self.base / name
        ET.ElementTree(root).write(target, encoding="utf-8", xml_declaration=True)
        return target

    def cli(self, *arguments, expected_code=0):
        result = subprocess.run([sys.executable, str(CLI), *map(str, arguments)],
                                cwd=self.base, text=True, capture_output=True)
        self.assertEqual(result.returncode, expected_code, result.stdout + result.stderr)
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            self.fail("CLI did not return a JSON result: " + result.stdout + result.stderr)

    def project(self):
        self.write("evidence.csv", "run,value\n1,2\n2,4\n3,6\n")
        self.write("source.py", "# Synthetic source; observations are in evidence.csv\n")
        self.write("upstream.tex", "% Synthetic immutable upstream geometry: n=3\n")
        self.svg()
        return {"version": 1, "project_id": "synthetic-assay", "question": "How do run-level observations compare?",
                "figures": [{"id": "F1", "question": "What is the mean response?", "claim": "Synthetic mean is 4 mV.",
                    "caption": "Synthetic fixture: three independent runs; raw values 2, 4, 6 mV.",
                    "alt_text": "Synthetic response plot with a fixed dose label.", "units": {"response": "mV"},
                    "statistics": {"estimator": "mean", "n": 3, "independent_unit": "run"},
                    "entities": [{"id": "assay", "label": "Whole assay", "quantity": 1, "representation": "whole"},
                                 {"id": "readout", "label": "Run readouts", "parent": "assay", "quantity": 3,
                                  "quantity_ref": "runs", "representation": "part"}],
                    "relations": [{"source": "assay", "target": "readout", "kind": "contains"}],
                    "quantities": {"runs": 3, "mean_mV": 4}, "evidence_files": ["evidence.csv"],
                    "selected_variant": "native", "variants": [
                        {"id": "native", "source": {"type": "python", "path": "source.py"},
                         "svg": "plot.svg", "expected_labels": ["AI/ML response", "Dose (mg)"]},
                        {"id": "alternative", "source": {"type": "tex", "path": "upstream.tex"}},
                    ]}]}

    def handover(self):
        spec = self.project()
        spec["figures"][0]["variants"] = [{"id": "native", "source": {"type": "tex", "path": "upstream.tex"},
                                            "svg": "plot.svg", "expected_labels": ["AI/ML response", "Dose (mg)"]}]
        baseline = build_project(spec, base_dir=self.base)
        handed = copy.deepcopy(spec)
        handed["figures"][0]["variants"][0]["source"] = {
            "type": "svg", "path": "plot.svg", "frozen_upstream": ["upstream.tex"]}
        report = build_project(handed, base_dir=self.base, baseline=baseline)
        self.assertTrue(report["passed"], report)
        return handed, report

    def test_contrast_and_lightness_have_independent_black_white_endpoints(self):
        # Mathematical sRGB extrema are exact known answers, not a second copy
        # of the conversion formula: black/white = 21:1, any color/self = 1:1.
        self.assertEqual(contrast_ratio("#000000", "#FFFFFF"), 21)
        self.assertEqual(contrast_ratio("#0072B2", "#0072B2"), 1)
        report = palette_report({"palette": {"Black": "#000000", "White": "#FFFFFF"}, "text_color": "#000000"})
        self.assertEqual([role["L_star"] for role in report["roles"]], [0, 100])
        self.assertEqual(report["pairs"][0]["delta_L"], 100)
        same = palette_report({"palette": {"A": "#0072B2", "B": "#0072B2"}})
        self.assertEqual(same["pairs"][0]["grayscale_contrast"], 1)
        self.assertEqual(same["pairs"][0]["delta_L"], 0)
        self.assertTrue(same["pairs"][0]["review_recommended"])
        differentiated = palette_report({"palette": {
            "A": {"color": "#0072B2", "marker": "o"}, "B": {"color": "#0072B2", "marker": "s"}}})
        self.assertFalse(differentiated["pairs"][0]["review_recommended"])
        self.assertEqual(differentiated["pairs"][0]["redundant_channels"], ["marker"])

    def test_style_and_selected_text_are_allowed_but_geometry_or_other_text_is_not(self):
        source = self.svg()
        before = source.read_bytes()
        def valid_edit(root):
            root.find(f".//{SVG}path[@id='curve']").set("stroke", "#D55E00")
            root.find(f".//{SVG}text[@id='response']").text = "Control response"
        styled = self.edit(source, "styled.svg", valid_edit)
        self.assertTrue(compare_svg_edits(source, styled, allowed_text_ids=["response"])["passed"])
        moved = self.edit(source, "moved.svg", lambda root: root.find(f".//{SVG}path").set("d", "M 8 40 L 40 10 L 72 40"))
        self.assertFalse(compare_svg_edits(source, moved, allowed_text_ids=["response"])["passed"])
        mislabeled = self.edit(source, "unselected.svg", lambda root: setattr(root.find(f".//{SVG}text[@id='fixed']"), "text", "Dose (g)"))
        self.assertFalse(compare_svg_edits(source, mislabeled, allowed_text_ids=["response"])["passed"])
        self.assertEqual(source.read_bytes(), before)

    def test_permitted_text_id_must_not_be_an_ancestor_group(self):
        source = self.svg()
        edited = self.edit(source, "changed.svg", lambda root: setattr(root.find(f".//{SVG}text[@id='fixed']"), "text", "Dose (g)"))
        with self.assertRaisesRegex(ValueError, "(?i)(text|tspan)"):
            compare_svg_edits(source, edited, allowed_text_ids=["plot"])

    def test_selected_tspan_does_not_allow_changes_to_its_unselected_tail(self):
        source = self.svg(nested_text=True)
        changed = self.edit(source, "dose.svg", lambda root: setattr(root.find(f".//{SVG}tspan[@id='dose']"), "text", "8"))
        self.assertTrue(compare_svg_edits(source, changed, allowed_text_ids=["dose"])["passed"])
        wrong_unit = self.edit(source, "wrong-unit.svg", lambda root: setattr(root.find(f".//{SVG}tspan[@id='dose']"), "tail", " g"))
        self.assertFalse(compare_svg_edits(source, wrong_unit, allowed_text_ids=["dose"])["passed"])

    def test_unselected_inter_tspan_space_is_scientific_text(self):
        source = self.svg(nested_text=True)
        changed = self.edit(source, "missing-space.svg", lambda root: setattr(root.find(f".//{SVG}tspan[@id='dose']"), "tail", "mg"))
        self.assertFalse(compare_svg_edits(source, changed)["passed"])

    def test_alt_text_preserves_scientific_nodes_and_existing_accessibility_references(self):
        source = self.svg(extra='<title id="old-title">Original title</title><title id="shared-title">Panel identity</title>'
                                '<desc id="old-desc">Original description</desc><g aria-labelledby="shared-title"/>')
        before = source.read_bytes()
        root_before = ET.parse(source).getroot()
        before_plot = ET.tostring(root_before.find(f".//{SVG}g[@id='plot']"))
        output = self.base / "accessible.svg"
        report = annotate_svg(source, output, title="Synthetic assay", description="Three runs of the AI/ML assay.")
        self.assertTrue(report["passed"], report)
        root_after = ET.parse(output).getroot()
        self.assertEqual(ET.tostring(root_after.find(f".//{SVG}g[@id='plot']")), before_plot)
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(root_after.get("aria-labelledby"), "old-title")
        self.assertEqual(root_after.get("aria-describedby"), "old-desc")
        self.assertTrue(audit_svg(output, expected_labels=["AI/ML response", "Dose (mg)"])["passed"])

    def test_variant_selection_changes_the_documented_active_source(self):
        spec = self.project()
        baseline = build_project(spec, base_dir=self.base)
        selected = copy.deepcopy(spec)
        selected["figures"][0]["selected_variant"] = "alternative"
        report = build_project(selected, base_dir=self.base, baseline=baseline)
        self.assertTrue(report["passed"], report)
        active = [variant for variant in report["figures"][0]["variants"] if variant["selected"]]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["source"]["path"], "upstream.tex")
        self.assertIn("upstream.tex", project_documents(report)["FIGURE_INDEX.md"])
        self.assertEqual(set(project_documents(report)), {"FIGURE_INDEX.md", "CAPTIONS.md", "ALT_TEXT.md"})

    def test_snapshot_does_not_alias_mutable_quantities_or_entities(self):
        spec = self.project()
        baseline = build_project(spec, base_dir=self.base)
        spec["figures"][0]["quantities"]["runs"] = 4
        spec["figures"][0]["entities"][1]["quantity"] = 4
        spec["figures"][0]["entities"][1]["label"] = "Four readouts"
        revised = build_project(spec, base_dir=self.base, baseline=baseline)
        self.assertEqual(baseline["snapshot"]["science"]["F1"]["quantities"]["runs"], 3)
        self.assertFalse(revised["passed"])
        self.assertIn("science", revised["revision"]["changes"])

    def test_evidence_file_edit_is_detected_from_actual_bytes(self):
        spec = self.project()
        baseline = build_project(spec, base_dir=self.base)
        old_hash = baseline["snapshot"]["evidence"]["evidence.csv"]
        self.write("evidence.csv", "run,value\n1,2\n2,4\n3,99\n")
        revised = build_project(spec, base_dir=self.base, baseline=baseline)
        self.assertFalse(revised["passed"])
        self.assertIn("evidence", revised["revision"]["changes"])
        self.assertNotEqual(revised["snapshot"]["evidence"]["evidence.csv"], old_hash)

    def test_source_switch_freezes_the_previous_tex_bytes(self):
        handed, baseline = self.handover()
        self.write("upstream.tex", "% Synthetic geometry changed: n=4\n")
        revised = build_project(handed, base_dir=self.base, baseline=baseline)
        self.assertFalse(revised["passed"])
        self.assertTrue(any(change.startswith("frozen_upstream:") for change in revised["revision"]["changes"]))

    def test_removed_or_aliased_freeze_declaration_cannot_release_a_frozen_file(self):
        for replacement in ([], ["./upstream.tex"]):
            with self.subTest(frozen_upstream=replacement):
                handed, baseline = self.handover()
                self.write("upstream.tex", "% Changed after handover: n=99\n")
                revised_spec = copy.deepcopy(handed)
                revised_spec["figures"][0]["variants"][0]["source"]["frozen_upstream"] = replacement
                revised = build_project(revised_spec, base_dir=self.base, baseline=baseline)
                self.assertFalse(revised["passed"], revised)
                self.assertTrue(any("frozen_upstream" in change for change in revised["revision"]["changes"]))

    def test_active_source_cannot_equal_frozen_source_through_a_path_alias(self):
        spec = self.project()
        spec["figures"][0]["variants"][0]["source"] = {
            "type": "tex", "path": "./upstream.tex", "frozen_upstream": ["upstream.tex"]}
        with self.assertRaisesRegex(ValueError, "(?i)(active|frozen)"):
            build_project(spec, base_dir=self.base)

    def test_a_handover_rejects_changes_made_before_the_freeze_and_keeps_legacy_locks(self):
        spec = self.project()
        spec["figures"][0]["selected_variant"] = "alternative"
        baseline = build_project(spec, base_dir=self.base)
        self.write("upstream.tex", "% Changed while switching source: n=99\n")
        spec["figures"][0]["selected_variant"] = "native"
        spec["figures"][0]["variants"][0]["source"]["frozen_upstream"] = ["./upstream.tex"]
        report = build_project(spec, base_dir=self.base, baseline=baseline)
        self.assertFalse(report["passed"])
        self.assertIn("frozen_upstream:upstream.tex", report["revision"]["changes"])
        handed, stable = self.handover()
        legacy = copy.deepcopy(stable)
        legacy["snapshot"].pop("frozen_upstream")
        self.write("upstream.tex", "% Changed after legacy handover: n=99\n")
        self.assertFalse(build_project(handed, base_dir=self.base, baseline=legacy)["passed"])

    def test_two_figures_cannot_select_and_freeze_the_same_active_source(self):
        spec = self.project()
        other = copy.deepcopy(spec["figures"][0])
        other["id"] = "F2"
        other["variants"][0]["source"] = {"type": "svg", "path": "plot.svg", "frozen_upstream": ["source.py"]}
        spec["figures"].append(other)
        report = build_project(spec, base_dir=self.base)
        self.assertFalse(report["passed"])
        self.assertTrue(any("active sources" in error for error in report["errors"]))

    def test_parent_chain_validation_reports_unknown_later_nodes_without_stopiteration(self):
        spec = self.project()
        self.assertTrue(build_project(spec, base_dir=self.base)["passed"])
        spec["figures"][0]["entities"] = [{"id": "part", "label": "Part", "parent": "whole"},
                                            {"id": "whole", "label": "Whole", "parent": "missing"}]
        with self.assertRaisesRegex(ValueError, "(?i)parent"):
            build_project(spec, base_dir=self.base)

    def test_entity_quantity_and_whole_part_declarations_have_consistent_meanings(self):
        for change in ({"quantity": 99}, {"quantity_ref": "absent"}, {"representation": "whole"},
                       {"representation": "unknown"}, {"quantity": True}):
            with self.subTest(change=change):
                spec = self.project()
                spec["figures"][0]["entities"][1].update(change)
                with self.assertRaises(ValueError):
                    build_project(spec, base_dir=self.base)
        spec = self.project()
        spec["figures"][0]["entities"][0]["representation"] = "detail"
        with self.assertRaisesRegex(ValueError, "(?i)parent"):
            build_project(spec, base_dir=self.base)

    def test_shared_style_is_resolved_from_actual_selected_plot_specs(self):
        from ff_plots import render_plots
        from ff_style import resolve_plot_style
        spec = self.project()
        palette = {"AI/ML": {"color": "#0072B2", "marker": "o", "linestyle": "-"},
                   "Control": {"color": "#D55E00", "marker": "s", "linestyle": "--"}}
        spec["style"] = {"palette": palette, "text_color": "#000000", "background": "#FFFFFF"}
        self.json("shared-style.json", {"version": 1, "palette": palette})
        self.write("points.csv", "method,x,y\nAI/ML,1,2\nAI/ML,2,4\nControl,1,2\nControl,2,4\n")
        spec["figures"] = [copy.deepcopy(spec["figures"][0]) for _ in range(2)]
        for index, figure in enumerate(spec["figures"], 1):
            figure["id"] = f"F{index}"
            figure.update(question="Do identical groups retain one semantic style across figures?",
                          claim="Synthetic groups share the observations 2 and 4.",
                          caption="Synthetic style check; each group has two supplied coordinates.",
                          evidence_files=["points.csv"], statistics={"n_per_group": 2},
                          entities=[], relations=[], quantities={"n_per_group": 2})
            plot_spec = {"defaults": "../shared-style.json", "formats": ["svg"], "data_status": "synthetic",
                         "title": f"Synthetic style fixture {index}", "figure": {"width_mm": 90, "height_mm": 60},
                         "panels": [{"kind": "scatter", "data": "../points.csv", "x": "x", "y": "y", "hue": "method"}]}
            source = self.json(f"specs/figure-{index}.json", plot_spec)
            rendered = render_plots(resolve_plot_style(plot_spec, base_dir=source.parent), self.base / f"figure-{index}", base_dir=source.parent)
            figure["variants"] = [{"id": "native", "source": {"type": "json", "path": f"specs/figure-{index}.json"},
                                     "svg": f"figure-{index}.svg", "expected_labels": rendered["expected_labels"]}]
        baseline = build_project(spec, base_dir=self.base)
        self.assertTrue(baseline["passed"], baseline)
        self.assertTrue(all(figure["style_identity"]["checked"] for figure in baseline["figures"]))
        hashes = [figure["style_identity"]["style_sha256"] for figure in baseline["figures"]]
        self.assertEqual(hashes[0], hashes[1])
        second = self.base / "specs/figure-2.json"
        changed = json.loads(second.read_text())
        changed["palette"] = {"AI/ML": {"color": "#D55E00", "marker": "s", "linestyle": "-"}}
        self.json("specs/figure-2.json", changed)
        revised = build_project(spec, base_dir=self.base, baseline=baseline)
        self.assertFalse(revised["passed"])
        self.assertTrue(revised["figures"][1]["style_identity"]["mismatches"])
        changed["palette"] = {"AI/ML": "#0072B2"}
        self.json("specs/figure-2.json", changed)
        only_declared = build_project(spec, base_dir=self.base, baseline=baseline)
        self.assertTrue(only_declared["passed"], only_declared)
        # AI/ML declares only color; Control inherits all three properties.
        self.assertEqual(only_declared["figures"][1]["style_identity"]["compared_properties"], 4)

    def test_quality_cli_returns_numeric_results_and_respects_edit_scope(self):
        colors = self.json("palette.json", {"palette": {"A": "#000000", "B": "#FFFFFF"}, "text_color": "#000000"})
        self.assertEqual(self.cli("palette", "--spec", colors)["text"]["contrast"], 21)
        source = self.svg()
        annotated = self.base / "annotated.svg"
        self.assertTrue(self.cli("annotate", source, "--out", annotated, "--title", "Synthetic assay",
                                 "--description", "Three runs of a synthetic assay")["passed"])
        edited = self.edit(source, "new-label.svg", lambda root: setattr(root.find(f".//{SVG}text[@id='response']"), "text", "Control response"))
        self.assertTrue(self.cli("revision", source, edited, "--allow-text-id", "response")["passed"])
        self.assertFalse(self.cli("revision", source, edited, expected_code=2)["passed"])

    def test_project_cli_protects_inputs_and_writes_notes_only_for_valid_revision(self):
        spec = self.project()
        source = self.json("project.json", spec)
        before = source.read_bytes()
        baseline_path = self.base / "baseline.json"
        notes = self.base / "notes"
        self.assertTrue(self.cli("project", "--spec", source, "--out", baseline_path, "--notes-dir", notes)["passed"])
        self.assertEqual({p.name for p in notes.iterdir()}, {"FIGURE_INDEX.md", "CAPTIONS.md", "ALT_TEXT.md"})
        self.assertFalse(self.cli("project", "--spec", source, "--out", source, "--overwrite", expected_code=2)["passed"])
        self.assertEqual(source.read_bytes(), before)
        self.assertFalse(self.cli("project", "--spec", source, "--baseline", baseline_path,
                                  "--out", baseline_path, "--overwrite", expected_code=2)["passed"])
        self.write("evidence.csv", "run,value\n1,99\n")
        bad_notes = self.base / "invalid-notes"
        failed = self.cli("project", "--spec", source, "--baseline", baseline_path,
                          "--out", self.base / "failed.json", "--notes-dir", bad_notes, expected_code=2)
        self.assertFalse(failed["passed"])
        self.assertFalse(bad_notes.exists())
        self.assertTrue((self.base / "failed.json").is_file())


if __name__ == "__main__":
    unittest.main()
