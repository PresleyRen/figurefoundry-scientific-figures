"""Behavioral coverage of the useful S01/S06/S08 plotting features.

The fixtures are synthetic with independently calculable answers. Tests inspect
scientific values and rendered geometry, and verify real editable SVG output.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "ff-feature-tests"))
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "figurefoundry" / "scripts"))

import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection, PathCollection

from ff_data import wide_to_long
from ff_export import export_figure
from ff_plots import (Palette, _distribution, _line_bar, _matrix, _scatter,
                      plt, render_plots, visible_text_labels)
from ff_style import resolve_plot_style


class WideTableTests(unittest.TestCase):
    def test_explicit_curve_columns_preserve_units_missingness_and_order(self):
        frame = pd.DataFrame({"time": [0, 1, 2], "subject": ["s1"] * 3,
                              "temperature": [20, 21, 22], "alpha": [1, np.nan, 3],
                              "beta": [4, 5, 6]})
        original = frame.copy(deep=True)
        result, report = wide_to_long(frame, x="time", y_columns=["beta", "alpha"])
        self.assertEqual(result["series"].tolist(), ["beta"] * 3 + ["alpha"] * 3)
        self.assertEqual(result["time"].tolist(), [0, 1, 2] * 2)
        self.assertEqual(result["subject"].tolist(), ["s1"] * 6)
        # A numerical metadata field must stay an identifier, not become a curve.
        self.assertEqual(result["temperature"].tolist(), [20, 21, 22] * 2)
        np.testing.assert_allclose(result["value"], [4, 5, 6, 1, np.nan, 3], equal_nan=True)
        self.assertEqual(report["missing_values_retained"], 1)
        self.assertEqual(report["output_rows"], 6)
        pd.testing.assert_frame_equal(frame, original)

    def test_ambiguous_wide_columns_or_output_names_fail(self):
        frame = pd.DataFrame({"time": [0, 1], "a": [1, 2], "b": [3, 4]})
        options = [
            {"y_columns": ["a", "a"]},
            {"y_columns": ["a", "time"]},
            {"y_columns": ["missing"]},
            {"y_columns": ["a"], "value_name": "b"},
            {"y_columns": ["a"], "value_name": "v", "series_name": "v"},
        ]
        for extra in options:
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                wide_to_long(frame, x="time", **extra)


class ArtistFeatureTests(unittest.TestCase):
    def setUp(self):
        self.fig, self.ax = plt.subplots()
        self.addCleanup(plt.close, self.fig)

    def test_bar_overlay_uses_independent_unit_values_and_matching_sem(self):
        frame = pd.DataFrame({"condition": ["A"] * 7,
                              "subject": ["s1", "s1", "s1", "s2", "s3", "s4", "s4"],
                              "response": [0, 4, 8, 10, 16, np.nan, np.nan]})
        panel = {"kind": "bar", "x": "condition", "y": "response", "unit": "subject",
                 "within_unit": "mean", "estimator": "mean", "error": "sem",
                 "raw_points": True, "raw_point_jitter": 0}
        report = {"warnings": []}
        _line_bar(self.ax, frame, panel, Palette(), report)
        # Subject means are 4, 10, 16. Missing s4 contributes no point or n.
        points = [item for item in self.ax.collections if isinstance(item, PathCollection)]
        self.assertEqual(len(points), 1)
        np.testing.assert_array_equal(points[0].get_offsets(), [[0, 4], [0, 10], [0, 16]])
        self.assertEqual(self.ax.patches[0].get_height(), 10)
        self.assertEqual(report["raw_points"]["point_count"], 3)
        row = report["statistics"]["groups"][0]
        self.assertEqual((row["n"], row["observations"], row["missing"]), (3, 7, 2))
        # Sample SD=6, so SEM=6/sqrt(3); verify actual interval geometry.
        interval = next(item for item in self.ax.collections if isinstance(item, LineCollection))
        np.testing.assert_allclose(interval.get_segments()[0],
                                   [[0, 10 - 6 / math.sqrt(3)], [0, 10 + 6 / math.sqrt(3)]])

    def test_bar_overlay_requires_units_and_explicit_repeated_unit_reduction(self):
        frame = pd.DataFrame({"group": ["A"] * 3, "subject": ["s1", "s1", "s2"], "value": [0, 4, 8]})
        base = {"kind": "bar", "x": "group", "y": "value", "estimator": "mean", "raw_points": True}
        with self.assertRaisesRegex(ValueError, "independent unit"):
            _line_bar(self.ax, frame, base, Palette(), {"warnings": []})
        with self.assertRaisesRegex(ValueError, "Repeated unit.*within_unit"):
            _line_bar(self.ax, frame, {**base, "unit": "subject"}, Palette(), {"warnings": []})

    def test_same_subject_in_two_conditions_is_drawn_once_in_each_condition(self):
        frame = pd.DataFrame({"group": ["A", "A", "B", "B"], "subject": ["s1", "s2"] * 2,
                              "value": [1, 3, 2, 4]})
        report = {"warnings": []}
        _line_bar(self.ax, frame, {"kind": "bar", "x": "group", "y": "value", "unit": "subject",
                                   "estimator": "mean", "raw_points": True, "raw_point_jitter": 0},
                  Palette(), report)
        points = next(item for item in self.ax.collections if isinstance(item, PathCollection))
        np.testing.assert_array_equal(points.get_offsets(), [[0, 1], [0, 3], [1, 2], [1, 4]])
        self.assertEqual(report["raw_points"]["point_count"], 4)

    def test_ols_annotation_matches_hand_calculated_equation_and_r_squared(self):
        frame = pd.DataFrame({"x": [0, 1, 2, 3], "y": [1, 2, 2, 5]})
        report = {"warnings": []}
        _scatter(self.ax, frame, {"kind": "scatter", "x": "x", "y": "y",
                                 "fit": "ols", "fit_annotation": True}, Palette(), report)
        fit = report["fits"][0]
        # Sxx=5, Sxy=6, ymean=2.5; b=1.2, a=.7, SSE=1.8, SST=9.
        for key, expected in {"slope": 1.2, "intercept": 0.7, "sse": 1.8, "sst": 9,
                              "r_squared": 0.8}.items():
            self.assertAlmostEqual(fit[key], expected)
        self.assertEqual(self.ax.texts[0].get_text(), "y = 1.2 x + 0.7; R² = 0.8")
        np.testing.assert_allclose(self.ax.lines[0].get_ydata(), [0.7, 4.3])
        self.assertEqual(fit["fit_space"], "original data coordinates")

    def test_constant_response_reports_undefined_r_squared(self):
        report = {"warnings": []}
        _scatter(self.ax, pd.DataFrame({"x": [0, 1, 2], "y": [3, 3, 3]}),
                 {"kind": "scatter", "x": "x", "y": "y", "fit": "ols", "fit_annotation": True},
                 Palette(), report)
        self.assertIsNone(report["fits"][0]["r_squared"])
        self.assertIn("R² = undefined", self.ax.texts[0].get_text())

    def test_fit_annotation_is_opt_in_and_cannot_appear_without_model(self):
        frame = pd.DataFrame({"x": [0, 1, 2], "y": [1, 3, 5]})
        _scatter(self.ax, frame, {"kind": "scatter", "x": "x", "y": "y", "fit": "ols"},
                 Palette(), {"warnings": []})
        self.assertEqual(len(self.ax.texts), 0)
        with self.assertRaisesRegex(ValueError, "requires explicit fit"):
            _scatter(self.ax, frame, {"kind": "scatter", "x": "x", "y": "y", "fit_annotation": True},
                     Palette(), {"warnings": []})

    def test_normal_fit_is_mle_and_overlays_a_probability_density(self):
        report = {"warnings": []}
        _distribution(self.ax, pd.DataFrame({"x": [-1, 0, 1]}),
                      {"kind": "hist", "x": "x", "bins": [-1.5, -0.5, 0.5, 1.5],
                       "fit": "normal", "density": True}, Palette(), report)
        fit = report["fits"][0]
        sigma = math.sqrt(2 / 3)  # MLE uses population denominator n, not n-1.
        self.assertEqual(fit["parameters"]["loc"], 0)
        self.assertAlmostEqual(fit["parameters"]["scale"], sigma)
        xx, yy = self.ax.lines[0].get_data()
        expected = np.exp(-0.5 * (xx / sigma) ** 2) / (sigma * math.sqrt(2 * math.pi))
        np.testing.assert_allclose(yy, expected, rtol=1e-12)
        self.assertAlmostEqual(float(np.trapezoid(yy, xx)), 1, places=3)
        # Three equally populated bins of width 1 each have height 1/3.
        self.assertAlmostEqual(self.ax.patches[0].get_xy()[:, 1].max(), 1 / 3)
        self.assertEqual(report["histogram_scale"], "probability density")

    def test_lognormal_fit_uses_log_mle_without_a_location_shift(self):
        report = {"warnings": []}
        _distribution(self.ax, pd.DataFrame({"x": [math.exp(-1), 1, math.exp(1)]}),
                      {"kind": "hist", "x": "x", "bins": [0, 0.8, 1.2, 3],
                       "fit": "lognormal", "density": True}, Palette(), report)
        fit = report["fits"][0]
        sigma = math.sqrt(2 / 3)
        self.assertEqual(fit["parameters"]["loc"], 0)
        self.assertAlmostEqual(fit["parameters"]["scale"], 1)
        self.assertAlmostEqual(fit["parameters"]["s"], sigma)
        self.assertAlmostEqual(fit["parameters"]["log_mean"], 0)
        xx, yy = self.ax.lines[0].get_data()
        expected = np.exp(-0.5 * (np.log(xx) / sigma) ** 2) / (xx * sigma * math.sqrt(2 * math.pi))
        self.assertTrue(np.all(xx > 0))
        np.testing.assert_allclose(yy, expected, rtol=1e-12)
        self.assertAlmostEqual(float(np.trapezoid(yy, xx)), 1, places=3)

    def test_histogram_fits_reject_count_units_nonpositive_lognormal_and_truncated_bins(self):
        cases = [
            ([-1, 0, 1], {"fit": "normal"}, "density=true"),
            ([0, 1, 2], {"fit": "lognormal", "density": True}, "strictly positive"),
            ([2, 2, 2], {"fit": "normal", "density": True}, "nonconstant"),
            ([-1, 0, 1], {"fit": "normal", "density": True, "bins": [-0.5, 0.5]}, "cover all"),
        ]
        for values, options, message in cases:
            with self.subTest(options=options), self.assertRaisesRegex(ValueError, message):
                _distribution(self.ax, pd.DataFrame({"x": values}),
                              {"kind": "hist", "x": "x", **options}, Palette(), {"warnings": []})

    def test_grouped_histogram_fits_each_observed_group_separately(self):
        report = {"warnings": []}
        _distribution(self.ax, pd.DataFrame({"x": [-1, 0, 1, 3, 4, 5], "group": ["A"] * 3 + ["B"] * 3}),
                      {"kind": "hist", "x": "x", "hue": "group", "fit": "normal", "density": True},
                      Palette(), report)
        self.assertEqual([fit["group"] for fit in report["fits"]], ["A", "B"])
        self.assertEqual([fit["n"] for fit in report["fits"]], [3, 3])
        self.assertEqual([fit["parameters"]["loc"] for fit in report["fits"]], [0, 4])
        self.assertEqual(len(self.ax.lines), 2)


class SemanticPaletteTests(unittest.TestCase):
    def test_explicit_category_styles_match_between_lines_and_ungrouped_bars(self):
        mapping = {"Control": {"color": "#555555", "marker": "o"},
                   "Method": {"color": "#0072B2", "marker": "s"}}
        fig, ax = plt.subplots()
        self.addCleanup(plt.close, fig)
        frame = pd.DataFrame({"group": ["Method", "Method", "Control", "Control"],
                              "unit": [1, 2, 1, 2], "value": [2, 4, 1, 3]})
        _line_bar(ax, frame, {"kind": "bar", "x": "group", "y": "value", "unit": "unit",
                              "estimator": "mean", "raw_points": True}, Palette(mapping), {"warnings": []})
        np.testing.assert_allclose(ax.patches[0].get_facecolor(), [0, 114 / 255, 178 / 255, 1])
        np.testing.assert_allclose(ax.patches[1].get_facecolor(), [85 / 255] * 3 + [1])
        points = [item for item in ax.collections if isinstance(item, PathCollection)]
        self.assertEqual(len(points[0].get_paths()[0].vertices), 5)  # Method square
        self.assertGreater(len(points[1].get_paths()[0].vertices), 5)  # Control circle

    def test_numeric_zero_series_uses_its_declared_style(self):
        fig, ax = plt.subplots()
        self.addCleanup(plt.close, fig)
        frame = pd.DataFrame({"x": [0, 1, 0, 1], "y": [1, 2, 3, 4], "group": [0, 0, 1, 1]})
        _line_bar(ax, frame, {"kind": "line", "x": "x", "y": "y", "hue": "group"},
                  Palette({"0": "#D55E00", "1": "#0072B2"}), {"warnings": []})
        self.assertEqual([(line.get_label(), line.get_color()) for line in ax.lines],
                         [("0", "#D55E00"), ("1", "#0072B2")])

    def test_legacy_colors_keep_marker_and_line_codes_across_reordered_figures(self):
        mapping = {"Control": "#555555", "Method": "#0072B2", "Validation": "#D55E00"}
        frames = [
            pd.DataFrame({"x": [0, 1, 0, 1], "y": [1, 2, 2, 4], "group": ["Control"] * 2 + ["Method"] * 2}),
            pd.DataFrame({"x": [0, 1, 0, 1], "y": [2, 4, 1, 2], "group": ["Method"] * 2 + ["Control"] * 2}),
        ]
        actual = []
        for frame in frames:
            fig, ax = plt.subplots()
            self.addCleanup(plt.close, fig)
            _line_bar(ax, frame, {"kind": "line", "x": "x", "y": "y", "hue": "group"}, Palette(mapping), {"warnings": []})
            actual.append({line.get_label(): (line.get_color(), line.get_marker(), line.get_linestyle())
                           for line in ax.lines})
        self.assertEqual(actual[0], actual[1])
        self.assertEqual(actual[0]["Method"], ("#0072B2", "s", "--"))
        # A standalone subset must retain its role even when earlier roles are absent.
        self.assertEqual(Palette(mapping).style("Method")["marker"], "s")

    def test_structured_styles_preserve_explicit_semantics_and_leave_input_unchanged(self):
        mapping = {"Control": "#555555", "Method": {"color": "#0072B2", "marker": "^", "linestyle": ":"}}
        original = copy.deepcopy(mapping)
        first, second = Palette(mapping), Palette(mapping)
        first.style("Control")
        self.assertEqual(first.style("Method"), second.style("Method"))
        self.assertEqual(second.style("Method"), {"color": "#0072B2", "marker": "^", "linestyle": ":"})
        self.assertEqual(mapping, original)


class MatrixNormalizationTests(unittest.TestCase):
    def test_native_mesh_maps_known_values_under_all_five_norms(self):
        cases = [
            ([0, 5, 10], {"norm": "linear", "vmin": 0, "vmax": 10}, [0, 0.5, 1]),
            ([1, 10, 100], {"norm": "log", "vmin": 1, "vmax": 100}, [0, 0.5, 1]),
            ([-1, 0, 3], {"norm": "two-slope", "vmin": -1, "vcenter": 0, "vmax": 3}, [0, 0.5, 1]),
            ([-100, -1, 0, 1, 100], {"norm": "symlog", "vmin": -100, "vmax": 100, "linthresh": 1},
             [0, 9 / 28, 0.5, 19 / 28, 1]),
            ([0.5, 1.5, 2.5], {"norm": "boundary", "boundaries": [0, 1, 2, 3]}, [0, 127, 255]),
        ]
        for values, options, expected in cases:
            with self.subTest(norm=options["norm"]):
                fig, ax = plt.subplots()
                self.addCleanup(plt.close, fig)
                frame = pd.DataFrame({"column": list(map(str, range(len(values)))), "row": ["r"] * len(values),
                                      "value": values})
                report = {"warnings": []}
                _matrix(ax, frame, {"kind": "heatmap", "x": "column", "y": "row", "value": "value", **options},
                        Palette(), report)
                mesh = ax.collections[0]
                fig.canvas.draw()
                np.testing.assert_allclose(mesh.norm(values), expected)
                np.testing.assert_allclose(mesh.get_facecolors(), mesh.cmap(np.asarray(expected)))
                self.assertEqual(report["color_normalization"]["kind"], options["norm"])

    def test_invalid_norm_parameters_fail_instead_of_masking_scientific_values(self):
        cases = [
            ([0, 1, 2], {"norm": "log"}, "strictly positive"),
            ([-1, 0, 1], {"norm": "two-slope", "vcenter": 2}, "vcenter"),
            ([-1, 0, 1], {"norm": "symlog"}, "linthresh"),
            ([0, 1, 2], {"norm": "boundary", "boundaries": [0, 2, 1]}, "increasing"),
            ([0, 1, 2], {"norm": "boundary", "boundaries": [0, 1, 3], "vmin": 0}, "instead of vmin"),
        ]
        for values, options, message in cases:
            with self.subTest(options=options):
                fig, ax = plt.subplots()
                self.addCleanup(plt.close, fig)
                frame = pd.DataFrame({"x": ["a", "b", "c"], "y": ["r"] * 3, "value": values})
                with self.assertRaisesRegex(ValueError, message):
                    _matrix(ax, frame, {"kind": "heatmap", "x": "x", "y": "y", "value": "value", **options},
                            Palette(), {"warnings": []})

    def test_shared_explicit_scale_maps_same_value_to_same_color(self):
        observed = []
        for values in ([1, 10, 100], [10, 100, 1000]):
            fig, ax = plt.subplots()
            self.addCleanup(plt.close, fig)
            frame = pd.DataFrame({"x": ["a", "b", "c"], "y": ["r"] * 3, "value": values})
            _matrix(ax, frame, {"kind": "heatmap", "x": "x", "y": "y", "value": "value",
                                "norm": "log", "vmin": 1, "vmax": 1000}, Palette(), {"warnings": []})
            mesh = ax.collections[0]
            fig.canvas.draw()
            observed.append(mesh.get_facecolors()[list(values).index(10)])
        np.testing.assert_array_equal(observed[0], observed[1])


class VisibilityInventoryTests(unittest.TestCase):
    def test_hidden_axis_ticks_labels_and_offset_text_do_not_enter_visible_inventory(self):
        fig, axes = plt.subplots(1, 2)
        self.addCleanup(plt.close, fig)
        axes[0].plot([0, 1, 2], [1, 3, 5])
        axes[0].set_xticks([0.137], ["hidden-tick-137"])
        axes[0].set_xlabel("Hidden x label")
        axes[0].xaxis.set_visible(False)
        axes[1].set_xlabel("Hidden off-axis label")
        axes[1].set_xticks([0.271], ["hidden-tick-271"])
        axes[1].set_axis_off()
        axes[1].set_title("Visible title")
        axes[1].text(0.5, 0.5, "Visible annotation")
        fig.canvas.draw()
        axes[0].xaxis.get_offset_text().set_text("Hidden offset")
        labels = visible_text_labels(fig)
        for hidden in ("hidden-tick-137", "hidden-tick-271", "Hidden x label", "Hidden off-axis label", "Hidden offset"):
            self.assertNotIn(hidden, labels)
        self.assertIn("Visible title", labels)
        self.assertIn("Visible annotation", labels)


class FeatureExportAndLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ff-feature-export-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def write(self, name, content):
        (self.base / name).write_text(content, encoding="utf-8")
        return name

    def spec(self, panels):
        return {"version": 1, "title": "Synthetic feature validation", "data_status": "synthetic",
                "formats": ["svg"], "figure": {"width_mm": 180, "height_mm": 120, "font_pt": 8, "min_font_pt": 6},
                "panels": panels}

    def test_wide_curve_and_fit_annotation_survive_real_native_svg_export(self):
        wide = self.write("wide.csv", "time,Control,Method\n0,1,2\n1,,4\n2,3,6\n")
        scatter = self.write("scatter.csv", "x,y\n0,1\n1,2\n2,2\n3,5\n")
        before = hashlib.sha256((self.base / wide).read_bytes()).hexdigest()
        spec = self.spec([
            {"kind": "line", "data": wide, "x": "time", "y_columns": ["Control", "Method"],
             "xlabel": "Time (s)", "ylabel": "Response (mV)", "title": "Curves"},
            {"kind": "scatter", "data": scatter, "x": "x", "y": "y",
             "fit": "ols", "fit_annotation": True, "title": "Regression"},
        ])
        result = render_plots(spec, self.base / "feature", base_dir=self.base)
        self.assertTrue(result["svg_audit"]["passed"])
        self.assertEqual(result["svg_audit"]["metrics"]["image_count"], 0)
        xml = ET.fromstring((self.base / "feature.svg").read_bytes())
        texts = ["".join(node.itertext()) for node in xml.iter() if node.tag.endswith("}text")]
        for label in ["Control", "Method", "y = 1.2 x + 0.7; R² = 0.8"]:
            self.assertIn(label, texts)
        self.assertEqual(result["provenance"]["panels"][0]["transformations"][0]["missing_values_retained"], 1)
        self.assertEqual(hashlib.sha256((self.base / wide).read_bytes()).hexdigest(), before)

    def test_line_controls_role_fonts_and_integrated_center_labels_reach_artists(self):
        source = self.write("styles.csv", "x,y,group\n0,1,A\n1,2,A\n2,3,A\n0,2,B\n1,3,B\n2,4,B\n")
        spec = self.spec([{"kind": "line", "data": source, "x": "x", "y": "y", "hue": "group",
                           "xlabel": "Time", "ylabel": "Response", "title": "Calibration",
                           "linewidth": 2.2, "markersize": 5, "markevery": 2, "show_panel_id": True}])
        spec["figure"].update(grid="x", axis_font_pt=9, tick_font_pt=7, legend_font_pt=8,
                              panel_font_pt=10, panel_label_style="integrated", panel_label_position="center")
        observed = {}
        def capture(fig, *args, **kwargs):
            ax = fig.axes[0]
            observed.update(title=ax.get_title(), title_font=ax.title.get_fontsize(),
                            axis_font=ax.xaxis.label.get_fontsize(), tick_font=ax.get_xticklabels()[0].get_fontsize(),
                            legend_font=ax.get_legend().get_texts()[0].get_fontsize(),
                            linewidth=ax.lines[0].get_linewidth(), markersize=ax.lines[0].get_markersize(),
                            markevery=ax.lines[0].get_markevery(), xdata=ax.lines[0].get_xdata(),
                            xgrid=any(line.get_visible() for line in ax.get_xgridlines()),
                            ygrid=any(line.get_visible() for line in ax.get_ygridlines()))
            return {}
        with patch("ff_plots.export_figure", side_effect=capture):
            render_plots(spec, self.base / "style", base_dir=self.base)
        self.assertEqual(observed["title"], "(a) Calibration")
        for role, expected in {"title_font": 10, "axis_font": 9, "tick_font": 7, "legend_font": 8,
                               "linewidth": 2.2, "markersize": 5, "markevery": 2}.items():
            self.assertEqual(observed[role], expected)
        np.testing.assert_array_equal(observed["xdata"], [0, 1, 2])
        self.assertTrue(observed["xgrid"])
        self.assertFalse(observed["ygrid"])

    def test_grid_choices_change_only_the_requested_grid_axes(self):
        source = self.write("grid.csv", "x,y\n0,1\n1,2\n2,3\n")
        for setting, expected in [(False, (False, False)), (True, (True, True)),
                                  ("x", (True, False)), ("y", (False, True)), ("both", (True, True))]:
            with self.subTest(setting=setting):
                spec = self.spec([{"kind": "line", "data": source, "x": "x", "y": "y"}])
                spec["figure"]["grid"] = setting
                observed = []
                def capture(fig, *args, **kwargs):
                    ax = fig.axes[0]
                    observed.extend([any(line.get_visible() for line in ax.get_xgridlines()),
                                     any(line.get_visible() for line in ax.get_ygridlines())])
                    return {}
                with patch("ff_plots.export_figure", side_effect=capture):
                    render_plots(spec, self.base / "grid", base_dir=self.base)
                self.assertEqual(tuple(observed), expected)

    def test_centered_separate_identifier_keeps_title_in_its_own_row(self):
        source = self.write("label.csv", "x,y\n0,1\n1,2\n2,3\n")
        spec = self.spec([{"kind": "line", "data": source, "x": "x", "y": "y", "title": "Observation",
                           "show_panel_id": True}])
        spec["figure"].update(panel_label_style="separate", panel_label_position="center")
        observed = {}
        def capture(fig, *args, **kwargs):
            ax = fig.axes[0]
            renderer = fig.canvas.get_renderer()
            observed.update(title=ax.get_title(), identifier=ax.texts[-1].get_text(),
                            label_bottom=ax.texts[-1].get_window_extent(renderer).y0,
                            title_top=ax.title.get_window_extent(renderer).y1)
            return {}
        with patch("ff_plots.export_figure", side_effect=capture):
            render_plots(spec, self.base / "label", base_dir=self.base)
        self.assertEqual((observed["title"], observed["identifier"]), ("Observation", "a"))
        self.assertGreater(observed["label_bottom"], observed["title_top"])

    def test_log_colorbar_uses_editable_literal_ticks_in_real_svg(self):
        source = self.write("log-matrix.csv", "x,y,value\na,r,1\nb,r,10\nc,r,100\n")
        spec = self.spec([{"kind": "heatmap", "data": source, "x": "x", "y": "y", "value": "value",
                           "norm": "log", "vmin": 1, "vmax": 100, "colorbar_label": "Signal (a.u.)"}])
        result = render_plots(spec, self.base / "log-matrix", base_dir=self.base)
        self.assertTrue(result["svg_audit"]["passed"])
        self.assertEqual(result["svg_audit"]["metrics"]["image_count"], 0)
        xml = ET.fromstring((self.base / "log-matrix.svg").read_bytes())
        texts = ["".join(node.itertext()) for node in xml.iter() if node.tag.endswith("}text")]
        for label in ["1", "10", "100", "Signal (a.u.)"]:
            self.assertIn(label, texts)

    def test_histogram_fits_export_native_curves_and_editable_model_labels(self):
        for model, csv in [("normal", "value\n-1\n0\n1\n"),
                           ("lognormal", "value\n0.36787944117144233\n1\n2.718281828459045\n")]:
            with self.subTest(model=model):
                source = self.write(f"{model}.csv", csv)
                spec = self.spec([{"kind": "hist", "data": source, "x": "value", "fit": model,
                                   "density": True, "xlabel": "Measured quantity (a.u.)"}])
                result = render_plots(spec, self.base / f"{model}-fit", base_dir=self.base)
                self.assertTrue(result["svg_audit"]["passed"])
                self.assertEqual(result["svg_audit"]["metrics"]["image_count"], 0)
                xml = ET.fromstring((self.base / f"{model}-fit.svg").read_bytes())
                texts = ["".join(node.itertext()) for node in xml.iter() if node.tag.endswith("}text")]
                self.assertIn(f"{model} fit", texts)
                self.assertIn("Probability density", texts)

    def test_five_resolved_themes_change_real_artists_without_changing_statistics_or_svg_contract(self):
        source = self.write("theme-data.csv", "time,subject,group,value\n0,s1,A,1\n0,s2,A,3\n0,s3,A,5\n"
                            "1,s1,A,3\n1,s2,A,5\n1,s3,A,7\n")
        # Independent expectations, including two visibly different typography/
        # frame conventions. These do not read expected values back from THEMES.
        expected = {
            "minimal": ("DejaVu Sans", True, False, 1.3, 3.8, 8, 7.5),
            "engineering": ("DejaVu Sans", False, True, 1.2, 3, 7, 7),
            "classic": ("DejaVu Serif", False, True, 1.1, 3, 8, 7.5),
            "warm": ("DejaVu Sans", False, False, 1.3, 3.5, 8, 7.5),
            "compact": ("DejaVu Sans", False, False, 1.1, 3, 7, 8),
        }
        reports = []
        with plt.rc_context({"svg.fonttype": "path", "text.usetex": True, "savefig.bbox": "tight",
                             "axes.grid": True, "axes.spines.top": True, "font.size": 19}):
            for theme, wanted in expected.items():
                with self.subTest(theme=theme):
                    spec = self.spec([{"kind": "line", "data": source, "x": "time", "y": "value", "hue": "group",
                                       "unit": "subject", "estimator": "mean", "error": "ci95",
                                       "xlabel": "Time (s)", "ylabel": "Signal (mV)", "title": "Repeated samples",
                                       "show_panel_id": True}])
                    spec["theme"] = theme
                    spec["figure"].update(width_mm=95, height_mm=80)
                    resolved = resolve_plot_style(spec)
                    observed = {}
                    def capture_and_export(fig, *args, **kwargs):
                        ax = fig.axes[0]
                        observed["style"] = (ax.xaxis.label.get_fontfamily()[0],
                                             any(line.get_visible() for line in ax.get_ygridlines()),
                                             ax.spines["top"].get_visible(), ax.lines[0].get_linewidth(),
                                             ax.lines[0].get_markersize(), ax.get_xticklabels()[0].get_fontsize(),
                                             ax.get_legend().get_texts()[0].get_fontsize())
                        observed["values"] = ax.lines[0].get_ydata()
                        self.assertFalse(any(line.get_visible() for line in ax.get_xgridlines()))
                        self.assertFalse(ax.xaxis.label.get_usetex())
                        return export_figure(fig, *args, **kwargs)
                    with patch("ff_plots.export_figure", side_effect=capture_and_export):
                        result = render_plots(resolved, self.base / f"theme-{theme}", base_dir=self.base)
                    self.assertEqual(observed["style"], wanted)
                    np.testing.assert_array_equal(observed["values"], [3, 5])
                    statistics = result["provenance"]["panels"][0]["statistics"]
                    reports.append(statistics)
                    self.assertEqual([row["n"] for row in statistics["groups"]], [3, 3])
                    self.assertAlmostEqual(statistics["groups"][0]["upper"],
                                           3 + 4.302652729696142 * 2 / math.sqrt(3), places=9)
                    self.assertTrue(result["svg_audit"]["passed"])
                    self.assertEqual(result["svg_audit"]["metrics"]["image_count"], 0)
                    self.assertGreater(result["svg_audit"]["metrics"]["text_count"], 0)
                    self.assertAlmostEqual(result["svg_audit"]["metrics"]["width_mm"], 95, places=5)
                    self.assertAlmostEqual(result["svg_audit"]["metrics"]["height_mm"], 80, places=5)
                    # Scoped rendering must restore even deliberately dirty globals.
                    self.assertEqual(plt.rcParams["svg.fonttype"], "path")
                    self.assertTrue(plt.rcParams["text.usetex"])
                    self.assertEqual(plt.rcParams["savefig.bbox"], "tight")
        self.assertTrue(all(report == reports[0] for report in reports[1:]))

    def layout_spec(self, *, automatic=False):
        source = self.write("panel.csv", "x,y\n0,1\n1,2\n2,3\n")
        panels = [{"kind": "line", "data": source, "x": "x", "y": "y", "title": title}
                  for title in ["Discovery", "Validation", "Robustness"]]
        panels[0]["grid"] = [0, 0, 2, 1]
        if not automatic:
            panels[1]["grid"], panels[2]["grid"] = [0, 1, 1, 1], [1, 1, 1, 1]
        spec = self.spec(panels)
        spec["figure"].update(rows=2, cols=2, width_ratios=[1.8, 1], height_ratios=[1, 1])
        return spec

    def test_asymmetric_hero_has_three_visible_axes_with_real_geometric_hierarchy(self):
        for automatic in (False, True):
            with self.subTest(automatic=automatic):
                spec = self.layout_spec(automatic=automatic)
                captured = {}
                def capture(fig, *args, **kwargs):
                    captured["positions"] = [ax.get_position().frozen() for ax in fig.axes]
                    captured["visible"] = [ax.get_visible() for ax in fig.axes]
                    captured["titles"] = [ax.get_title() for ax in fig.axes]
                    return {"provenance": kwargs["provenance"]}
                with patch("ff_plots.export_figure", side_effect=capture):
                    result = render_plots(spec, self.base / "geometry", base_dir=self.base)
                hero, top, bottom = captured["positions"]
                self.assertEqual(captured["visible"], [True, True, True])
                self.assertEqual(captured["titles"], ["Discovery", "Validation", "Robustness"])
                self.assertGreater(hero.width, 1.5 * top.width)
                self.assertGreater(hero.height, 1.7 * top.height)
                self.assertLess(hero.x1, top.x0)
                self.assertLess(bottom.y1, top.y0)
                self.assertAlmostEqual(hero.y0, bottom.y0, places=5)
                self.assertAlmostEqual(hero.y1, top.y1, places=5)
                self.assertEqual(result["provenance"]["layout"]["panel_grid"],
                                 [[0, 0, 2, 1], [0, 1, 1, 1], [1, 1, 1, 1]])

    def test_layout_overlap_outside_and_invalid_ratio_are_rejected_before_export(self):
        variants = []
        overlap = self.layout_spec()
        overlap["panels"][1]["grid"] = [1, 0, 1, 1]
        variants.append((overlap, "overlaps"))
        outside = self.layout_spec()
        outside["panels"][2]["grid"] = [2, 1, 1, 1]
        variants.append((outside, "outside"))
        bad_ratio = self.layout_spec()
        bad_ratio["figure"]["width_ratios"] = [1, 0]
        variants.append((bad_ratio, "positive finite"))
        fractional = self.layout_spec()
        fractional["panels"][0]["grid"] = [0, 0, 1.5, 1]
        variants.append((fractional, "integer"))
        for spec, message in variants:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                render_plots(spec, self.base / "invalid", base_dir=self.base)
        self.assertFalse((self.base / "invalid.svg").exists())

    def test_asymmetric_example_exports_editable_panels(self):
        path = ROOT / "examples" / "asymmetric.json"
        spec = json.loads(path.read_text(encoding="utf-8"))
        spec["formats"] = ["svg"]
        result = render_plots(spec, self.base / "asymmetric", base_dir=path.parent)
        self.assertTrue(result["svg_audit"]["passed"])
        self.assertEqual(result["svg_audit"]["metrics"]["image_count"], 0)
        self.assertEqual(len(result["provenance"]["panels"]), 3)
        self.assertEqual(result["provenance"]["layout"]["panel_grid"],
                         [[0, 0, 2, 1], [0, 1, 1, 1], [1, 1, 1, 1]])
        xml = ET.fromstring((self.base / "asymmetric.svg").read_bytes())
        texts = ["".join(node.itertext()) for node in xml.iter() if node.tag.endswith("}text")]
        for panel in spec["panels"]:
            self.assertIn(panel["title"], texts)


if __name__ == "__main__":
    unittest.main()

