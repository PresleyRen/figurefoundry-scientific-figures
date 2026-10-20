"""Independent conflict re-audit using known answers and real export pipelines.

All observations below are synthetic fixtures, not experimental findings. Files
are generated in temporary directories. The observations dictionary is consumed
by the separately run audit reporter; no production manifests are overwritten.
"""
from __future__ import annotations

import copy
import hashlib
import io
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "ff-reaudit-mpl"))
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "figurefoundry" / "scripts"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from ff_compose import compose_svgs
from ff_diagram import render_diagram
from ff_export import export_figure, normalize_generated_svg
from ff_journal import review_profile
from ff_plots import render_plots
from ff_svg import audit_svg

SVG = "{http://www.w3.org/2000/svg}"
OBSERVATIONS = {}


class ReauditConflictTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="ff-reaudit-conflict-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)

    def record(self, **observations):
        OBSERVATIONS[self._testMethodName] = observations

    def csv(self, name, content):
        path = self.base / name
        path.write_text(content, encoding="utf-8")
        return path

    def panel(self, path, *, x=0, y=0, width=89, height=75, label="", **extra):
        return {"path": str(path), "x_mm": x, "y_mm": y, "width_mm": width,
                "height_mm": height, "label": label, **extra}

    def spec(self, panels, title="Synthetic conflict re-audit", **figure):
        return {"data_status": "synthetic", "title": title, "formats": ["svg"],
                "figure": {"width_mm": 89, "height_mm": 70,
                           "font_pt": 8, "min_font_pt": 6, **figure},
                "palette": {"AI/ML": "#0072B2", "Control": "#D55E00"},
                "panels": panels}

    def capture(self, spec, name):
        """Observe actual artists, then run the unmodified final exporter."""
        captured = []

        def observe(fig, *args, **kwargs):
            for ax in fig.axes:
                captured.append({
                    "lines": [{"label": line.get_label(),
                               "x": np.asarray(line.get_xdata()).tolist(),
                               "y": np.asarray(line.get_ydata()).tolist(),
                               "color": line.get_color()}
                              for line in ax.lines],
                    "bars": [rectangle.get_height() for rectangle in ax.patches
                             if hasattr(rectangle, "get_height")],
                    "offsets": [np.asarray(collection.get_offsets()).tolist()
                                for collection in ax.collections],
                    "limits": [list(ax.get_xlim()), list(ax.get_ylim())],
                    "spines": {name: spine.get_visible() for name, spine in ax.spines.items()},
                })
            return export_figure(fig, *args, **kwargs)

        with patch("ff_plots.export_figure", side_effect=observe):
            result = render_plots(spec, self.base / name, base_dir=self.base)
        return result, captured

    def test_outlined_chart_cannot_gain_editability_from_new_panel_letter(self):
        fig, ax = plt.subplots(figsize=(90 / 25.4, 60 / 25.4))
        self.addCleanup(plt.close, fig)
        ax.plot([0, 1, 2], [0, 1, 0], marker="o")
        ax.set_xlabel("Dose (mg)")
        ax.set_ylabel("Response (mV)")
        with matplotlib.rc_context({"svg.fonttype": "path"}):
            stream = io.StringIO()
            fig.savefig(stream, format="svg")
        source = self.base / "outlined.svg"
        source.write_text(normalize_generated_svg(stream.getvalue()), encoding="utf-8")
        source_audit = audit_svg(source, min_font_pt=0)
        self.assertEqual(source_audit["metrics"]["visible_text_count"], 0)
        output = self.base / "composite.svg"
        with self.assertRaisesRegex(ValueError, "(?i)(source|panel).*?(text|audit)") as error:
            compose_svgs([self.panel(source, width=90, height=65, label="a")],
                         output, width_mm=90, height_mm=65, min_font_pt=6)
        self.assertFalse(output.exists())
        self.record(conflicts=["CF-01", "CF-11", "CF-12", "CF-14"],
                    source_visible_text=0, rejected=str(error.exception), output_written=False)

    def test_required_source_labels_cannot_be_supplied_by_another_panel(self):
        def source(name, label):
            return self.csv(name,
                '<svg xmlns="http://www.w3.org/2000/svg" width="80mm" height="40mm" viewBox="0 0 80 40">'
                '<path id="curve" d="M 10 30 L 40 10 L 70 30" fill="none" stroke="black"/>'
                '<text x="8" y="35" font-size="3">' + label + '</text></svg>')

        correct = source("correct.svg", "Dose (mg)")
        partial = source("partial.svg", "AI/ML model")
        cases = []
        for field in ("expected_labels", "labels"):
            with self.subTest(field=field):
                output = self.base / (field + ".svg")
                with self.assertRaisesRegex(ValueError, "Required editable label is missing") as error:
                    compose_svgs([
                        self.panel(correct, width=80, height=45, label="a"),
                        self.panel(partial, x=85, width=80, height=45, label="b",
                                   **{field: ["AI/ML model", "Dose (mg)"]})],
                        output, width_mm=165, height_mm=45, min_font_pt=6)
                self.assertFalse(output.exists())
                cases.append({"field": field, "error": str(error.exception)})
        self.record(conflicts=["CF-01", "CF-07", "CF-12", "CF-14"],
                    note="Dose is live in panel a, absent from panel b despite another live label.",
                    cases=cases)

    def test_technical_replicates_spines_and_two_real_panels_keep_known_values(self):
        # Run means: [2, 4, 6] at time 0 and [1, 3, 5] at time 1.
        # The first run has three technical replicates: naive row weighting
        # would give means 3.2 and 2.2 instead of the intended 4 and 3.
        rows = ["method,time,run,response"]
        for method in ("AI/ML", "Control"):
            for time in (0, 1):
                for run, values in ((1, [1, 2, 3]), (2, [4]), (3, [6])):
                    rows += [f"{method},{time},{run},{value - time}" for value in values]
        raw = self.csv("assay.csv", "\n".join(rows) + "\n")
        expected_hash = hashlib.sha256(raw.read_bytes()).hexdigest()
        panel = {"kind": "line", "data": raw.name, "x": "time", "y": "response", "hue": "method",
                 "unit": "run", "within_unit": "mean", "estimator": "mean", "error": "sem",
                 "xlabel": "Time (h)", "ylabel": "Signal (mV)", "xlim": [-0.1, 1.1], "ylim": [0, 7]}
        baseline, artist_a = self.capture(self.spec([panel]), "minimal_spines")
        boxed, artist_b = self.capture(self.spec([dict(panel, spines="all")]), "all_spines")
        summaries = baseline["provenance"]["panels"][0]["statistics"]
        self.assertEqual(summaries, boxed["provenance"]["panels"][0]["statistics"])
        self.assertEqual(summaries["independent_unit"], "run")
        for group in summaries["groups"]:
            self.assertEqual(group["n"], 3)
            self.assertEqual(group["observations"], 5)
            self.assertEqual(group["estimate"], 4 - group["time"])
            self.assertAlmostEqual(group["upper"] - group["estimate"], 2 / math.sqrt(3), places=12)
        self.assertFalse(artist_a[0]["spines"]["top"])
        self.assertTrue(artist_b[0]["spines"]["top"])
        for key in ("lines", "bars", "limits"):
            self.assertEqual(artist_a[0][key], artist_b[0][key])
        curves = [line for line in artist_a[0]["lines"] if line["label"] in ("AI/ML", "Control")]
        self.assertEqual([line["y"] for line in curves], [[4.0, 3.0], [4.0, 3.0]])

        endpoint_rows = [rows[0]] + [row for row in rows[1:] if row.split(",")[1] == "1"]
        endpoint = self.csv("endpoint.csv", "\n".join(endpoint_rows) + "\n")
        endpoint_spec = self.spec([{
            "kind": "bar", "data": endpoint.name, "x": "method", "y": "response",
            "unit": "run", "within_unit": "mean", "estimator": "mean", "error": "sd",
            "xlabel": "Method", "ylabel": "Endpoint signal (mV)", "ylim": [0, 7],
        }], title="Synthetic endpoint comparison")
        bars, artist_c = self.capture(endpoint_spec, "endpoint")
        self.assertEqual(artist_c[0]["bars"], [3.0, 3.0])
        for group in bars["provenance"]["panels"][0]["statistics"]["groups"]:
            self.assertEqual((group["estimate"], group["lower"], group["upper"], group["n"]), (3, 1, 5, 3))

        output = self.base / "final.svg"
        composite = compose_svgs([
            self.panel(self.base / "minimal_spines.svg", label="a", expected_labels=baseline["expected_labels"]),
            self.panel(self.base / "endpoint.svg", x=94, label="b", labels=bars["expected_labels"]),
        ], output, width_mm=183, height_mm=75, min_font_pt=6)
        self.assertTrue(composite["passed"], composite)
        labels = baseline["expected_labels"] + bars["expected_labels"] + ["a", "b"]
        independent = audit_svg(output, min_font_pt=6, width_mm=183, height_mm=75, expected_labels=labels)
        self.assertTrue(independent["passed"], independent)
        root = ET.parse(output).getroot()
        self.assertEqual((root.get("width"), root.get("height"), root.get("viewBox")), ("183mm", "75mm", "0 0 183 75"))
        ids = [element.get("id") for element in root.iter() if element.get("id")]
        self.assertEqual(len(ids), len(set(ids)))
        for element in root.iter():
            for key, value in element.attrib.items():
                if key.endswith("href"):
                    self.assertIn(value[1:], ids)
                for reference in re.findall(r"url\(#([^)]*)\)", value):
                    self.assertIn(reference, ids)
        for index, source_name in enumerate(("minimal_spines.svg", "endpoint.svg"), 1):
            source_file = self.base / source_name
            source_paths = [element.get("d") for element in ET.parse(source_file).iter(SVG + "path")]
            panel_root = root.find(f".//{SVG}g[@id='panel-{index:03d}']")
            self.assertEqual(source_paths, [element.get("d") for element in panel_root.iter(SVG + "path")])
            source_report = composite["panels"][index - 1]
            self.assertEqual(source_report["source_sha256"], hashlib.sha256(source_file.read_bytes()).hexdigest())
            self.assertTrue(source_report["source_audit"]["passed"])
            self.assertGreater(source_report["source_audit"]["metrics"]["expected_labels_checked"], 0)
        self.assertIn("AI/ML", independent["metrics"]["labels"])
        self.assertFalse(set(independent["metrics"]["labels"]) - set(labels))
        self.assertFalse(root.findall(f".//{SVG}image"))
        self.assertFalse(root.findall(f".//{SVG}filter"))
        self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(), expected_hash)
        self.assertEqual(baseline["provenance"]["panels"][0]["source"]["sha256"], expected_hash)
        self.record(conflicts=["CF-03", "CF-05", "CF-07", "CF-08", "CF-09", "CF-10", "CF-12", "CF-15"],
                    independent_means=[4, 3], naive_row_means=[3.2, 2.2], sem=2 / math.sqrt(3),
                    endpoint_means=[3, 3], endpoint_sd=2, n=3,
                    source_sha256=expected_hash, source_unchanged=True,
                    spines_data_and_axis_invariant=True, composed_metrics=independent["metrics"],
                    source_path_geometry_preserved=True, limitation="183 mm is an exact test target, not a verified journal instruction.")

    def test_vector_heatmap_and_native_workflow_compose_with_all_labels(self):
        source = self.csv("matrix.csv", "assay,method,value\nA,AI/ML,0\nB,AI/ML,-2\nA,Control,3\nB,Control,\n")
        spec = self.spec([{"kind": "heatmap", "data": source.name, "x": "assay", "y": "method",
                           "value": "value", "vmin": -3, "vmax": 3, "cmap": "RdBu_r",
                           "colorbar_label": "Change (mV)", "title": "Measured changes"}])
        heatmap = render_plots(spec, self.base / "heatmap", base_dir=self.base)
        self.assertEqual(heatmap["provenance"]["panels"][0]["matrix"], [[0.0, -2.0], [3.0, None]])
        diagram_path = self.base / "workflow.svg"
        diagram = {"width_mm": 89, "height_mm": 70, "font_pt": 8, "min_font_pt": 6,
                   "title": "Synthetic workflow schematic", "nodes": [
                       {"id": "runs", "label": "3 runs", "x": 6, "y": 28, "width": 29, "height": 16},
                       {"id": "measure", "label": "Assays A/B", "x": 49, "y": 28, "width": 32, "height": 16},
                   ], "edges": [{"source": "runs", "target": "measure", "label": "measure"}]}
        render_diagram(diagram, diagram_path)
        diagram_labels = ["Synthetic workflow schematic", "3 runs", "Assays A/B", "measure"]
        output = self.base / "workflow_and_results.svg"
        result = compose_svgs([
            self.panel(diagram_path, label="a", labels=diagram_labels),
            self.panel(self.base / "heatmap.svg", x=94, label="b", expected_labels=heatmap["expected_labels"]),
        ], output, width_mm=183, height_mm=75, min_font_pt=6)
        self.assertTrue(result["passed"], result)
        final = audit_svg(output, min_font_pt=6, expected_labels=diagram_labels + heatmap["expected_labels"])
        self.assertTrue(final["passed"], final)
        self.assertEqual(final["metrics"]["image_count"], 0)
        self.assertGreater(final["metrics"]["path_count"], 250)
        self.assertIn("AI/ML", final["metrics"]["labels"])
        self.record(conflicts=["CF-02", "CF-06", "CF-07", "CF-10", "CF-12", "CF-14", "CF-15"],
                    data_matrix=[[0, -2], [3, None]], missing_cells_not_zero=True,
                    final_metrics=final["metrics"], schematic_distinguished_from_quantitative_data=True)

    def test_null_and_negative_results_cross_chart_types_keep_known_answers(self):
        relationship = self.csv("relationship.csv", "x,y\n1,-2\n2,1\n3,2\n4,1\n5,-2\n")
        classifier = self.csv("classifier.csv", "truth,score\n0,0.5\n1,0.5\n0,0.5\n1,0.5\n")
        volcano = self.csv("volcano.csv", "effect,q\n-2,0.8\n0,1\n2,0.7\n")
        forest = self.csv("forest.csv", "study,effect,lower,upper\nNegative,-2,-3,-1\nCrosses zero,-1,-4,2\n")
        panels = [
            {"kind": "scatter", "data": relationship.name, "x": "x", "y": "y", "fit": "ols", "title": "No linear relation"},
            {"kind": "correlation", "data": relationship.name, "columns": ["x", "y"], "title": "Zero correlation"},
            {"kind": "roc", "data": classifier.name, "truth": "truth", "score": "score", "title": "Tied classifier"},
            {"kind": "pr", "data": classifier.name, "truth": "truth", "score": "score", "title": "Chance precision"},
            {"kind": "volcano", "data": volcano.name, "x": "effect", "p": "q", "p_definition": "supplied adjusted q", "title": "All nonsignificant"},
            {"kind": "forest", "data": forest.name, "label": "study", "effect": "effect", "lower": "lower", "upper": "upper",
             "reference": 0, "interval_definition": "supplied illustrative 95% confidence interval", "title": "Negative effects"},
        ]
        result, artists = self.capture(self.spec(panels, rows=2, cols=3, width_mm=183, height_mm=150), "null_results")
        reports = result["provenance"]["panels"]
        self.assertEqual(reports[0]["fits"][0]["slope"], 0)
        self.assertEqual(reports[0]["fits"][0]["r"], 0)
        self.assertEqual(reports[1]["matrix"], [[1.0, 0.0], [0.0, 1.0]])
        for index in (2, 3):
            self.assertEqual(reports[index]["curves"][0]["auc"], 0.5)
            self.assertEqual(reports[index]["curves"][0]["average_precision"], 0.5)
        self.assertEqual((reports[4]["significant_points"], reports[4]["total_points"]), (0, 3))
        forest_offsets = [offsets for offsets in artists[5]["offsets"] if len(offsets) == 2]
        self.assertIn([[-2.0, 0.0], [-1.0, 1.0]], forest_offsets)
        self.assertTrue(result["svg_audit"]["passed"])
        self.assertEqual(result["svg_audit"]["metrics"]["image_count"], 0)
        self.record(conflicts=["CF-06", "CF-08", "CF-09", "CF-11"],
                    linear_slope=0, correlation=0, auc=0.5, average_precision=0.5,
                    volcano_significant=0, volcano_total=3, forest_effects=[-2, -1],
                    final_metrics=result["svg_audit"]["metrics"])

    def test_missing_timepoint_gap_and_every_observed_mark_survive_composition(self):
        source = self.csv("gaps.csv", "time,value\n0,1\n1,2\n2,\n3,4\n4,5\n")
        spec = self.spec([{"kind": "line", "data": source.name, "x": "time", "y": "value",
                           "xlabel": "Time (h)", "ylabel": "Measured signal"}])
        plot, artists = self.capture(spec, "gaps")
        actual = artists[0]["lines"][0]
        self.assertEqual(actual["x"], [0, 1, 2, 3, 4])
        self.assertTrue(math.isnan(actual["y"][2]))
        self.assertEqual([actual["y"][i] for i in (0, 1, 3, 4)], [1, 2, 4, 5])
        source_root = ET.parse(self.base / "gaps.svg").getroot()
        curve = next(element for element in source_root.iter(SVG + "path")
                     if ("stroke: " + actual["color"].lower()) in element.get("style", "").lower()
                     and "M" in element.get("d", ""))
        # Two disjoint pairs require two moveto segments in the SVG path.
        self.assertEqual(curve.get("d").count("M"), 2)
        output = self.base / "composed_gap.svg"
        composition = compose_svgs([self.panel(self.base / "gaps.svg", label="a", expected_labels=plot["expected_labels"])],
                                   output, width_mm=89, height_mm=75, min_font_pt=6)
        self.assertTrue(composition["passed"], composition)
        final_root = ET.parse(output).getroot()
        self.assertIn(curve.get("d"), [element.get("d") for element in final_root.iter(SVG + "path")])
        self.record(conflicts=["CF-10", "CF-12"], input_rows=5, observed_values=4, missing_values=1,
                    svg_moveto_segments=2, final_curve_identical=True,
                    warnings=plot["provenance"]["panels"][0]["warnings"])

    def test_source_font_is_checked_after_placement_and_viewbox_only_still_works(self):
        # 2 user units at 1 mm/unit is 5.669 pt. Doubling gives 11.339 pt;
        # halving gives 2.835 pt. Only the final physical size decides legibility.
        source = self.csv("small.svg",
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 40">'
            '<rect x="2" y="2" width="76" height="36" fill="none" stroke="black"/>'
            '<text x="8" y="24" font-size="2">Measured signal</text></svg>')
        enlarged = compose_svgs([self.panel(source, width=160, height=80, expected_labels=["Measured signal"])],
                                self.base / "enlarged.svg", width_mm=160, height_mm=80, min_font_pt=6)
        self.assertTrue(enlarged["passed"], enlarged)
        self.assertAlmostEqual(enlarged["audit"]["metrics"]["min_font_pt"], 4 * 72 / 25.4)
        reduced = compose_svgs([self.panel(source, width=40, height=20)], self.base / "reduced.svg",
                               width_mm=40, height_mm=20, min_font_pt=6)
        self.assertFalse(reduced["passed"])
        self.assertAlmostEqual(reduced["audit"]["metrics"]["min_font_pt"], 72 / 25.4)
        for encoding, declaration in (("utf-8", '<?xml-stylesheet type="text/css" href="external.css"?>'),
                                      ("utf-16", '<!DOCTYPE svg>')):
            with self.subTest(unchecked_xml=declaration):
                unsupported = self.base / (encoding + "_unchecked.svg")
                unsupported.write_bytes((declaration + source.read_text()).encode(encoding))
                with self.assertRaises(ValueError):
                    compose_svgs([self.panel(unsupported)], self.base / (encoding + "_bad.svg"),
                                 width_mm=89, height_mm=75, min_font_pt=6)
        self.record(conflicts=["CF-03", "CF-12", "CF-14"], viewbox_only_source_accepted=True,
                    enlargement_font_pt=enlarged["audit"]["metrics"]["min_font_pt"],
                    reduction_font_pt=reduced["audit"]["metrics"]["min_font_pt"],
                    reduction_rejected=reduced["audit"]["errors"])

    def test_width_conflict_needs_resolution_and_never_becomes_certification(self):
        from datetime import date
        profile = {"journal": "Synthetic journal profile for local validation",
                   "article_type": "Research article", "stage": "Final artwork",
                   "width_mm": 183, "height_mm": 75, "min_font_pt": 6,
                   "conflicting_sources": [
                       {"source": "Candidate A", "widths_mm": [89, 183]},
                       {"source": "Candidate B", "widths_mm": [90, 180]},
                   ]}
        original = copy.deepcopy(profile)
        unresolved = review_profile(profile, today=date(2026, 10, 20))
        self.assertFalse(unresolved["passed"])
        resolved = review_profile(dict(profile, resolution="Use candidate A only as a dimensional test target; official verification pending."),
                                  today=date(2026, 10, 20))
        self.assertTrue(resolved["passed"])
        self.assertEqual(profile, original)
        self.assertEqual(resolved["journal_acceptance"], "not-certified")
        self.assertTrue(any("planning" in warning for warning in resolved["warnings"]))
        self.assertEqual(resolved["profile"]["conflicting_sources"], original["conflicting_sources"])
        self.record(conflicts=["CF-04"], unresolved_errors=unresolved["errors"],
                    resolved_warnings=resolved["warnings"], source_candidates_preserved=True,
                    journal_acceptance=resolved["journal_acceptance"],
                    limitation="This deliberately performs no external journal lookup or factual venue compliance claim.")


if __name__ == "__main__":
    unittest.main()
