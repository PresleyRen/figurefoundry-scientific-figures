"""CF-06: matched 2D/3D quantitative displays, inspected as real SVG artifacts.

Normal test runs write only to temporary directories. To regenerate the checked
A/B evidence explicitly, run this file with --write-evidence <directory>; then
visually inspect both PNGs and complete the pending review.json.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "ff-spatial-choice-tests"))
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "figurefoundry" / "scripts"))

import numpy as np
from mpl_toolkits.mplot3d import proj3d

from ff_export import export_figure
from ff_plots import plt

GROUPS = ("Control", "Method A", "Method B")
VALUES = (12.0, 15.0, 14.0)
COLORS = ("#666A73", "#0072B2", "#D55E00")
WIDTH_MM, HEIGHT_MM = 120, 90
DATA_CSV = "group,response\nControl,12\nMethod A,15\nMethod B,14\n"
SCIENTIFIC_LABELS = [*GROUPS, "Group", "Response (a.u.)", "12", "15", "14",
                     "Synthetic quantitative comparison"]
STYLE = {"font.family": "DejaVu Sans", "font.size": 8, "axes.labelsize": 8,
         "xtick.labelsize": 7, "ytick.labelsize": 7, "text.usetex": False,
         "text.parse_math": False, "svg.fonttype": "none", "axes.linewidth": 0.7,
         "savefig.bbox": None}


def make_comparison(view):
    """Build matched science with a view-specific spatial encoding."""
    with plt.rc_context(STYLE):
        fig = plt.figure(figsize=(WIDTH_MM / 25.4, HEIGHT_MM / 25.4))
        fig.suptitle("Synthetic quantitative comparison", fontsize=9, fontweight="bold", y=0.96)
        if view == "2d":
            ax = fig.add_axes([0.16, 0.16, 0.78, 0.68])
            bars = list(ax.bar(range(3), VALUES, width=0.6, color=COLORS,
                               edgecolor="white", linewidth=0.5))
            ax.set_xticks(range(3), GROUPS)
            ax.set_xlim(-0.6, 2.6)
            ax.set_ylim(0, 18)
            ax.set_yticks([0, 5, 10, 15])
            ax.set_xlabel("Group", labelpad=5)
            ax.set_ylabel("Response (a.u.)", labelpad=5)
            ax.spines[["top", "right"]].set_visible(False)
            ax.set_axisbelow(True)
            ax.grid(axis="y", color="#E2E5E9", linewidth=0.5)
            for index, value in enumerate(VALUES):
                ax.text(index, value + 0.35, f"{value:g}", ha="center", va="bottom", fontsize=8)
        elif view == "3d":
            ax = fig.add_axes([0.04, 0.08, 0.84, 0.80], projection="3d")
            bars = [ax.bar3d(index - 0.3, 0, 0, 0.6, 0.5, value, color=color,
                             shade=True, edgecolor="white", linewidth=0.35)
                    for index, (value, color) in enumerate(zip(VALUES, COLORS))]
            ax.set_xlim(-0.6, 2.6)
            ax.set_ylim(-0.15, 0.85)
            ax.set_zlim(0, 18)
            ax.set_xticks(range(3), GROUPS)
            ax.set_yticks([])
            ax.set_zticks([0, 5, 10, 15])
            ax.set_xlabel("Group", labelpad=6)
            ax.zaxis.set_rotate_label(False)
            ax.set_zlabel("Response (a.u.)", rotation=90, labelpad=4)
            ax.tick_params(axis="z", labelsize=7, pad=2)
            ax.tick_params(axis="x", pad=1)
            ax.set_box_aspect((1.4, 0.5, 1))
            ax.view_init(elev=24, azim=-57)
            for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
                axis.pane.set_facecolor((0.97, 0.98, 0.99, 1))
                axis.pane.set_edgecolor("#D7DCE2")
            for index, value in enumerate(VALUES):
                ax.text(index, 0.25, value + 0.65, f"{value:g}", ha="center", va="bottom", fontsize=8)
        else:
            plt.close(fig)
            raise ValueError("view must be 2d or 3d")
        fig.canvas.draw()
    return fig, ax, bars


def projected_height_metrics(view, ax):
    """Measure displayed baseline-to-top segment length per response unit."""
    ratios = []
    for index, value in enumerate(VALUES):
        if view == "2d":
            endpoints = ax.transData.transform([[index, 0], [index, value]])
        else:
            projected = [proj3d.proj_transform(index, 0, z, ax.get_proj())[:2] for z in (0, value)]
            endpoints = ax.transData.transform(projected)
        ratios.append(float(np.linalg.norm(endpoints[1] - endpoints[0]) / value))
    return {"pixels_per_response_unit": ratios,
            "relative_span": float(np.ptp(ratios) / np.mean(ratios)),
            "measurement": "2D centerline or 3D projected front-face centerline, from baseline to bar top"}


def export_comparison(fig, directory, view, *, overwrite=False):
    return export_figure(
        fig, Path(directory) / f"quantitative-{view}", width_mm=WIDTH_MM, height_mm=HEIGHT_MM,
        min_font_pt=6, formats=["svg", "png"], dpi=240, expected_labels=SCIENTIFIC_LABELS,
        provenance={"conflict_id": "CF-06", "data_status": "synthetic", "source": "data.csv",
                    "source_sha256": hashlib.sha256(DATA_CSV.encode("utf-8")).hexdigest(),
                    "groups": list(GROUPS), "values": list(VALUES), "view": view,
                    "quantity_axes": 1,
                    "extrusion_depth": 0.5 if view == "3d" else None,
                    "extrusion_meaning": "layout only; no second quantitative variable" if view == "3d" else None},
        overwrite=overwrite,
    )


def write_evidence(directory):
    """Explicit evidence regeneration; visual review is deliberately left pending."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "data.csv").write_text(DATA_CSV, encoding="utf-8")
    report = {"schema_version": 1, "conflict_id": "CF-06",
              "comparison": "One quantitative response across three categorical groups",
              "data_status": "synthetic", "source": "data.csv",
              "source_sha256": hashlib.sha256(DATA_CSV.encode("utf-8")).hexdigest(),
              "groups": list(GROUPS), "values": list(VALUES),
              "canvas_mm": [WIDTH_MM, HEIGHT_MM], "candidates": {},
              "visual_review": {"status": "pending"}, "decision": None}
    for view in ("2d", "3d"):
        fig, ax, _ = make_comparison(view)
        try:
            geometry = projected_height_metrics(view, ax)
            manifest = export_comparison(fig, directory, view, overwrite=True)
            metrics = manifest["svg_audit"]["metrics"]
            report["candidates"][view] = {
                "svg": f"quantitative-{view}.svg", "preview": f"quantitative-{view}.png",
                "manifest": f"quantitative-{view}.manifest.json",
                "svg_audit_passed": manifest["svg_audit"]["passed"],
                "text_count": metrics["text_count"], "image_count": metrics["image_count"],
                "width_mm": metrics["width_mm"], "height_mm": metrics["height_mm"],
                "height_encoding": geometry,
            }
        finally:
            plt.close(fig)
    (directory / "review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


class SpatialChoiceTests(unittest.TestCase):
    def test_matched_2d_and_3d_preserve_values_labels_and_editable_svg(self):
        with tempfile.TemporaryDirectory(prefix="ff-spatial-choice-") as temporary:
            Path(temporary, "data.csv").write_text(DATA_CSV, encoding="utf-8")
            for view in ("2d", "3d"):
                with self.subTest(view=view):
                    fig, ax, bars = make_comparison(view)
                    self.addCleanup(plt.close, fig)
                    if view == "2d":
                        self.assertEqual([bar.get_height() for bar in bars], list(VALUES))
                    else:
                        # Check the actually rendered projected polygons against
                        # the eight world-space corners of each independently
                        # specified bar. No private Matplotlib vertex attributes.
                        for index, (value, bar) in enumerate(zip(VALUES, bars)):
                            actual = np.unique(np.round(np.vstack([path.vertices for path in bar.get_paths()]), 9), axis=0)
                            corners = itertools.product([index - 0.3, index + 0.3], [0, 0.5], [0, value])
                            expected = np.unique(np.round([proj3d.proj_transform(x, y, z, ax.get_proj())[:2]
                                                          for x, y, z in corners], 9), axis=0)
                            np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-9)
                    manifest = export_comparison(fig, temporary, view)
                    self.assertTrue(manifest["svg_audit"]["passed"])
                    self.assertEqual(manifest["svg_audit"]["metrics"]["image_count"], 0)
                    self.assertAlmostEqual(manifest["svg_audit"]["metrics"]["width_mm"], WIDTH_MM, places=5)
                    self.assertAlmostEqual(manifest["svg_audit"]["metrics"]["height_mm"], HEIGHT_MM, places=5)
                    root = ET.fromstring(Path(temporary, f"quantitative-{view}.svg").read_bytes())
                    texts = ["".join(node.itertext()) for node in root.iter() if node.tag.endswith("}text")]
                    for label in SCIENTIFIC_LABELS:
                        self.assertIn(label, texts)

    def test_decorative_perspective_varies_height_scale_while_2d_keeps_common_scale(self):
        measured = {}
        for view in ("2d", "3d"):
            fig, ax, _ = make_comparison(view)
            self.addCleanup(plt.close, fig)
            measured[view] = projected_height_metrics(view, ax)
        self.assertLess(measured["2d"]["relative_span"], 1e-12)
        # This specific perspective introduces >1% unequal screen height per
        # response unit. Both formats remain valid SVG; this is a comparison
        # readability choice, not a rejection of real scientific 3D geometry.
        self.assertGreater(measured["3d"]["relative_span"], 0.01)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--write-evidence":
        report = write_evidence(sys.argv[2])
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        unittest.main()

