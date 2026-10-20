"""Independent numerical oracles and real native-SVG export regressions.

All data below are small, synthetic test fixtures with hand-calculable answers.
Outputs live in temporary directories; running tests never updates tracked data.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "ff-plot-tests"))
SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "figurefoundry" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import numpy as np
import pandas as pd

from ff_data import clean_json, summarize
from ff_plots import PLOT_KINDS, Palette, _line_bar, binary_curve, pareto_mask, plt, render_plots
from ff_svg import audit_svg


class IndependentUnitStatisticsTests(unittest.TestCase):
    def test_student_t_ci_uses_three_independent_units_and_df_two(self):
        frame = pd.DataFrame({"condition": ["A"] * 3, "subject": ["s1", "s2", "s3"],
                              "response_mg": [1.0, 3.0, 5.0]})
        result, report = summarize(frame, ["condition"], "response_mg", unit="subject", error="ci95")
        row = result.iloc[0]
        # Mean = 3 mg, sample SD = 2 mg; t_(.975, df=2) = 4.302652729696142.
        half_width = 4.302652729696142 * 2 / math.sqrt(3)
        self.assertEqual(row["estimate"], 3)
        self.assertAlmostEqual(row["lower"], 3 - half_width, places=9)
        self.assertAlmostEqual(row["upper"], 3 + half_width, places=9)
        self.assertEqual(row["n"], 3)
        self.assertEqual(row["observations"], 3)
        self.assertEqual(report["independent_unit"], "subject")
        self.assertEqual(report["confidence_level"], 0.95)
        # CI95 must not silently be replaced by either 1 SD or a normal 1.96 SEM.
        self.assertGreater(half_width, 1.96 * 2 / math.sqrt(3))

    def test_sd_sem_and_confidence_interval_have_distinct_meanings(self):
        frame = pd.DataFrame({"group": ["A"] * 3, "seed": [11, 12, 13], "value": [1, 3, 5]})
        widths = {}
        for uncertainty in ("sd", "sem", "ci95"):
            result, _ = summarize(frame, ["group"], "value", unit="seed", error=uncertainty)
            widths[uncertainty] = result.iloc[0]["upper"] - result.iloc[0]["estimate"]
        self.assertAlmostEqual(widths["sd"], 2)
        self.assertAlmostEqual(widths["sem"], 2 / math.sqrt(3))
        self.assertAlmostEqual(widths["ci95"] / widths["sem"], 4.302652729696142, places=9)

    def test_duplicate_subject_requires_explicit_within_subject_reduction(self):
        frame = pd.DataFrame({"group": ["A"] * 4, "subject": ["s1", "s1", "s2", "s3"],
                              "value": [0, 4, 10, 20]})
        with self.assertRaisesRegex(ValueError, "Repeated unit.*within_unit"):
            summarize(frame, ["group"], "value", unit="subject", error="ci95")

    def test_unequal_technical_replication_does_not_reweight_subjects(self):
        frame = pd.DataFrame({"group": ["A"] * 6,
                              "subject": ["s1", "s1", "s1", "s1", "s2", "s3"],
                              "value": [0, 0, 0, 0, 10, 20]})
        result, report = summarize(frame, ["group"], "value", unit="subject",
                                   within_unit="mean", error="ci95")
        row = result.iloc[0]
        # Independent subject means are [0, 10, 20]; raw row mean would be 5.
        self.assertEqual(row["estimate"], 10)
        self.assertEqual(row["n"], 3)
        self.assertEqual(row["observations"], 6)
        self.assertAlmostEqual(row["upper"], 10 + 4.302652729696142 * 10 / math.sqrt(3), places=8)
        self.assertEqual(report["within_unit"], "mean")

    def test_repeated_subject_across_conditions_is_allowed(self):
        frame = pd.DataFrame({"group": ["A", "A", "B", "B"],
                              "subject": ["s1", "s2", "s1", "s2"], "value": [1, 3, 2, 4]})
        result, _ = summarize(frame, ["group"], "value", unit="subject", error="sd")
        self.assertEqual(result["n"].tolist(), [2, 2])
        self.assertEqual(result["estimate"].tolist(), [2, 3])

    def test_uncertainty_requires_declared_independence_and_no_singleton_zero_ci(self):
        frame = pd.DataFrame({"group": ["A"], "subject": ["s1"], "value": [7.0]})
        with self.assertRaisesRegex(ValueError, "independent unit"):
            summarize(frame, ["group"], "value", error="ci95")
        result, report = summarize(frame, ["group"], "value", unit="subject", error="ci95")
        row = result.iloc[0]
        self.assertEqual(row["estimate"], 7)
        self.assertEqual(row["n"], 1)
        self.assertTrue(math.isnan(row["lower"]))
        self.assertTrue(math.isnan(row["upper"]))
        self.assertIsNone(report["groups"][0]["lower"])
        self.assertTrue(any("uncertainty unavailable" in warning for warning in report["warnings"]))

    def test_missing_values_remain_missing_and_do_not_increase_n(self):
        frame = pd.DataFrame({"group": ["A"] * 3, "subject": ["s1", "s2", "s3"],
                              "value": [1, np.nan, 5]})
        result, report = summarize(frame, ["group"], "value", unit="subject", error="sd")
        row = result.iloc[0]
        self.assertEqual(row["n"], 2)
        self.assertEqual(row["missing"], 1)
        self.assertEqual(row["observations"], 3)
        self.assertEqual(row["estimate"], 3)
        self.assertTrue(any("no imputation" in warning for warning in report["warnings"]))
        self.assertTrue(pd.isna(frame.loc[1, "value"]))

    def test_seeded_median_bootstrap_is_reproducible_and_uses_unit_estimates(self):
        frame = pd.DataFrame({"group": ["A"] * 3, "subject": ["s1", "s2", "s3"],
                              "value": [0, 2, 4]})
        options = dict(unit="subject", estimator="median", error="bootstrap95",
                       seed=314159, bootstrap_draws=2000)
        first, first_report = summarize(frame, ["group"], "value", **options)
        second, second_report = summarize(frame, ["group"], "value", **options)
        pd.testing.assert_frame_equal(first, second)
        self.assertEqual(first_report, second_report)
        self.assertEqual(first.iloc[0]["estimate"], 2)
        # Enumerating the 3^3 bootstrap samples gives median 0 or 4 with
        # probability 7/27 each; the 95% percentile interval spans [0, 4].
        self.assertEqual(first.iloc[0]["lower"], 0)
        self.assertEqual(first.iloc[0]["upper"], 4)
        self.assertEqual(first_report["random_seed"], 314159)
        with self.assertRaisesRegex(ValueError, "use bootstrap95 for medians"):
            summarize(frame, ["group"], "value", unit="subject", estimator="median", error="ci95")

    def test_zero_effect_and_zero_sd_are_valid_results_when_n_exceeds_one(self):
        frame = pd.DataFrame({"group": ["Null"] * 3, "subject": ["s1", "s2", "s3"],
                              "value": [0, 0, 0]})
        result, _ = summarize(frame, ["group"], "value", unit="subject", error="ci95")
        self.assertEqual(result.iloc[0][["estimate", "lower", "upper", "n"]].tolist(), [0, 0, 0, 3])


class PlotSemanticsTests(unittest.TestCase):
    def setUp(self):
        self.fig, self.ax = plt.subplots()
        self.addCleanup(plt.close, self.fig)

    def test_integer_line_coordinates_preserve_values_and_missing_breaks(self):
        frame = pd.DataFrame({"time": [0, 1, 2, 3, 4], "response": [1.0, 2.0, np.nan, 4.0, 5.0]})
        report = {"warnings": []}
        _line_bar(self.ax, frame, {"kind": "line", "x": "time", "y": "response"}, Palette(), report)
        np.testing.assert_array_equal(self.ax.lines[0].get_xdata(), [0, 1, 2, 3, 4])
        np.testing.assert_allclose(self.ax.lines[0].get_ydata(), [1, 2, np.nan, 4, 5], equal_nan=True)
        # The rendered path must start a second subpath after the missing value.
        commands = [code for _, code in self.ax.lines[0].get_path().iter_segments(remove_nans=True)]
        self.assertEqual(commands.count(1), 2)  # matplotlib.path.Path.MOVETO
        self.assertTrue(any("1 missing y values remain gaps" in warning for warning in report["warnings"]))

    def test_aggregated_numeric_x_values_are_not_lost_to_row_type_coercion(self):
        frame = pd.DataFrame({"time": [0, 0, 1, 1, 2, 2], "subject": ["s1", "s2"] * 3,
                              "response": [1.0, 3.0, np.nan, np.nan, 5.0, 7.0]})
        report = {"warnings": []}
        _line_bar(self.ax, frame, {"kind": "line", "x": "time", "y": "response",
                                   "unit": "subject", "estimator": "mean", "error": "ci95"},
                  Palette(), report)
        np.testing.assert_allclose(self.ax.lines[0].get_ydata(), [2, np.nan, 6], equal_nan=True)
        self.assertEqual([group["n"] for group in report["statistics"]["groups"]], [2, 0, 2])

    def test_explicit_zero_effect_numeric_bar_keeps_zero_height(self):
        frame = pd.DataFrame({"dose": [0, 0, 1, 1], "subject": ["s1", "s2"] * 2,
                              "response": [0, 0, 0, 0]})
        report = {"warnings": []}
        _line_bar(self.ax, frame, {"kind": "bar", "x": "dose", "y": "response", "unit": "subject",
                                   "estimator": "mean", "error": "ci95"}, Palette(), report)
        self.assertEqual([patch.get_height() for patch in self.ax.patches], [0, 0])

    def test_all_tied_scores_yield_auc_and_ap_equal_to_chance_prevalence(self):
        curve = binary_curve([0, 1, 0, 1], [0.5, 0.5, 0.5, 0.5])
        np.testing.assert_array_equal(curve["fpr"], [0, 1])
        np.testing.assert_array_equal(curve["tpr"], [0, 1])
        self.assertEqual(curve["auc"], 0.5)
        self.assertEqual(curve["average_precision"], 0.5)

    def test_tie_permutation_does_not_change_the_curve(self):
        first = binary_curve([1, 0, 1, 0], [0.9, 0.9, 0.4, 0.4])
        second = binary_curve([0, 1, 0, 1], [0.9, 0.9, 0.4, 0.4])
        for key in ("fpr", "tpr", "recall", "precision"):
            np.testing.assert_array_equal(first[key], second[key])
        self.assertEqual(first["auc"], 0.5)

    def test_inverted_classifier_has_zero_auc_without_a_performance_gate(self):
        curve = binary_curve([1, 1, 0, 0], [0.1, 0.2, 0.8, 0.9])
        self.assertEqual(curve["auc"], 0)
        self.assertAlmostEqual(curve["average_precision"], 5 / 12)

    def test_precision_recall_average_precision_has_known_ranked_answer(self):
        # Ranking P, N, P, N: AP = (1 + 2/3) / 2; three of four P/N pairs are concordant.
        curve = binary_curve([1, 0, 1, 0], [0.9, 0.8, 0.7, 0.6])
        np.testing.assert_allclose(curve["recall"], [0, 0.5, 0.5, 1, 1])
        np.testing.assert_allclose(curve["precision"], [1, 1, 0.5, 2/3, 0.5])
        self.assertAlmostEqual(curve["average_precision"], 5 / 6)
        self.assertEqual(curve["auc"], 0.75)
        self.assertEqual((curve["positive_n"], curve["negative_n"]), (2, 2))

    def test_undefined_binary_curves_are_rejected_explicitly(self):
        for truth, scores in (([1, 1], [0.1, 0.2]), ([0, 1], [0.2, np.nan]), ([], [])):
            with self.subTest(truth=truth):
                with self.assertRaises(ValueError):
                    binary_curve(truth, scores)

    def test_pareto_dominance_preserves_duplicate_frontier_points(self):
        mask = pareto_mask([1, 2, 2, 3, 4, 2], [1, 2, 2, 1, 4, 0],
                           minimize_x=True, minimize_y=False)
        np.testing.assert_array_equal(mask, [True, True, True, False, True, False])

    def test_pareto_direction_and_strict_tie_dominance(self):
        np.testing.assert_array_equal(pareto_mask([1, 1, 2], [1, 2, 2]), [False, True, False])
        np.testing.assert_array_equal(pareto_mask([1, 2, 2, 3], [4, 2, 2, 5], minimize_y=True),
                                      [True, True, True, False])
        with self.assertRaisesRegex(ValueError, "finite"):
            pareto_mask([1, np.nan], [2, 3])


class NativePlotExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ff-native-plots-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def render(self, kind, csv, fields, *, stem=None):
        data_path = self.base / f"{stem or kind}.csv"
        data_path.write_text(csv, encoding="utf-8")
        before = hashlib.sha256(data_path.read_bytes()).hexdigest()
        panel = {"kind": kind, "data": data_path.name, "xlabel": "X quantity (s)",
                 "ylabel": "Response (a.u.)", "title": f"Panel {kind}", **fields}
        spec = {"version": 1, "data_status": "synthetic", "title": f"Synthetic {kind} check",
                "formats": ["svg"], "figure": {"width_mm": 130, "height_mm": 90,
                                                "font_pt": 8, "min_font_pt": 6},
                "panels": [panel]}
        output = self.base / f"{stem or kind}_figure"
        manifest = render_plots(spec, output, base_dir=self.base)
        self.assertEqual(hashlib.sha256(data_path.read_bytes()).hexdigest(), before)
        self.assertEqual(manifest["provenance"]["panels"][0]["source"]["sha256"], before)
        return output.with_suffix(".svg"), manifest

    def assert_native(self, path, manifest, *, additional_labels=()):
        report = audit_svg(path, width_mm=130, height_mm=90, min_font_pt=6,
                           expected_labels=manifest["expected_labels"] + list(additional_labels))
        self.assertTrue(report["passed"], report["errors"])
        self.assertEqual(report["metrics"]["image_count"], 0)
        self.assertGreater(report["metrics"]["text_count"], 0)
        self.assertGreater(report["metrics"]["path_count"], 0)
        self.assertEqual(manifest["journal_acceptance"], "not-certified")
        self.assertEqual(manifest["manual_review"]["status"], "required")
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), manifest["files"]["svg"]["sha256"])
        self.assertNotIn(b"<!DOCTYPE", path.read_bytes())
        self.assertTrue(json.dumps(clean_json(manifest), allow_nan=False))
        # The artifact itself contains native text nodes, rather than relying
        # exclusively on the auditor's summarized counts.
        root = ET.fromstring(path.read_bytes())
        self.assertTrue(any(element.tag.endswith("}text") for element in root.iter()))
        self.assertFalse(any(element.tag.endswith("}image") for element in root.iter()))

    def test_all_sixteen_chart_kinds_export_live_text_native_svg(self):
        distribution = "group,subject,value\nA,s1,1\nA,s2,2\nA,s3,4\nB,s4,2\nB,s5,3\nB,s6,5\n"
        classification = "truth,score\n1,0.9\n0,0.8\n1,0.7\n0,0.6\n"
        cases = {
            "line": ("time,value\n0,1\n1,2\n2,1.5\n3,2.5\n", {"x": "time", "y": "value"}, []),
            "bar": (distribution, {"x": "group", "y": "value", "unit": "subject",
                                    "estimator": "mean", "error": "ci95"}, ["A", "B"]),
            "scatter": ("x,y\n1,2\n2,1\n3,3\n4,4\n", {"x": "x", "y": "y", "fit": "ols"}, []),
            "box": (distribution, {"x": "group", "y": "value"}, ["A", "B"]),
            "violin": (distribution, {"x": "group", "y": "value"}, ["A", "B"]),
            "hist": (distribution, {"x": "value", "hue": "group", "bins": [0, 2, 4, 6]}, ["A", "B"]),
            "ecdf": (distribution, {"x": "value", "hue": "group"}, ["A", "B"]),
            "heatmap": ("row,column,value\nR1,C1,0.1\nR1,C2,0.3\nR2,C1,0.7\nR2,C2,0.9\n",
                        {"x": "column", "y": "row", "value": "value", "colorbar_label": "Signal (a.u.)"},
                        ["R1", "R2", "C1", "C2", "Signal (a.u.)"]),
            "confusion": ("truth,prediction\nCat,Cat\nCat,Cat\nCat,Dog\nDog,Cat\nDog,Dog\nDog,Dog\n",
                          {"truth": "truth", "prediction": "prediction", "normalize": "row",
                           "labels": ["Cat", "Dog"]}, ["Cat", "Dog"]),
            "roc": (classification, {"truth": "truth", "score": "score"}, ["ROC (AUC=0.750)"]),
            "pr": (classification, {"truth": "truth", "score": "score"}, ["Precision–recall (AP=0.833)"]),
            "forest": ("study,effect,low,high\nStudy A,0,-1,1\nStudy B,0.1,-0.5,0.7\n",
                       {"label": "study", "effect": "effect", "lower": "low", "upper": "high",
                        "reference": 0, "interval_definition": "95% confidence interval"}, ["Study A", "Study B"]),
            "pareto": ("cost,accuracy,model\n1,1,Model A\n2,2,Model B\n3,1,Model C\n4,4,Model D\n",
                       {"x": "cost", "y": "accuracy", "label": "model"}, ["Model A", "Model B", "Model C", "Model D"]),
            "stacked_bar": ("group,component,count\nA,Correct,3\nA,Incorrect,1\nB,Correct,2\nB,Incorrect,2\n",
                            {"x": "group", "y": "count", "hue": "component", "normalize": True},
                            ["A", "B", "Correct", "Incorrect"]),
            "volcano": ("effect,q\n0,0.9\n0.2,0.8\n-0.1,0.7\n",
                        {"x": "effect", "p": "q", "p_definition": "adjusted q value"}, ["Below thresholds"]),
            "correlation": ("x,y,z\n1,2,4\n2,4,3\n3,6,2\n4,8,1\n",
                            {"columns": ["x", "y", "z"]}, ["x", "y", "z"]),
        }
        self.assertEqual(set(cases), set(PLOT_KINDS))
        self.assertEqual(len(cases), 16)
        for kind, (csv, fields, labels) in cases.items():
            with self.subTest(kind=kind):
                path, manifest = self.render(kind, csv, fields)
                self.assert_native(path, manifest, additional_labels=labels)
                panel = manifest["provenance"]["panels"][0]
                if kind == "confusion":
                    self.assertEqual(panel["counts"], [[2, 1], [1, 2]])
                    np.testing.assert_allclose(panel["matrix"], [[2/3, 1/3], [1/3, 2/3]])
                elif kind == "correlation":
                    np.testing.assert_allclose(panel["matrix"], [[1, 1, -1], [1, 1, -1], [-1, -1, 1]])
                elif kind == "volcano":
                    self.assertEqual((panel["significant_points"], panel["total_points"]), (0, 3))
                elif kind == "pareto":
                    self.assertEqual(panel["frontier_indices"], [0, 1, 3])

    def test_heatmap_colorbar_is_vector_and_label_is_preserved(self):
        path, manifest = self.render("heatmap", "row,column,value\nR1,C1,0\nR1,C2,1\nR2,C1,2\nR2,C2,3\n",
                                    {"x": "column", "y": "row", "value": "value", "colorbar_label": "Intensity (mV)"})
        self.assert_native(path, manifest, additional_labels=["Intensity (mV)"])
        self.assertGreater(manifest["svg_audit"]["metrics"]["path_count"], 200)

    def test_null_and_inverted_experiments_still_produce_reviewable_figures(self):
        path, manifest = self.render("roc", "truth,score\n1,0.1\n1,0.2\n0,0.8\n0,0.9\n",
                                    {"truth": "truth", "score": "score"}, stem="inverted")
        self.assert_native(path, manifest, additional_labels=["ROC (AUC=0.000)"])
        self.assertEqual(manifest["provenance"]["panels"][0]["curves"][0]["auc"], 0)
        path, manifest = self.render("line", "time,value\n0,0\n1,0\n2,0\n",
                                    {"x": "time", "y": "value"}, stem="null_line")
        self.assert_native(path, manifest)


if __name__ == "__main__":
    unittest.main()
