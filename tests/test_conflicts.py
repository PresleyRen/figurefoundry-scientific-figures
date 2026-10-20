"""Executable decisions between conflicting scientific-export approaches.

CONFLICT_CASES supplies report metadata, not precomputed pass claims. A report
generator must attach actual unittest results. These tests write only to temporary
directories and never create a tracked conflict-results file.
"""

from __future__ import annotations

import io
import os
from pathlib import Path
import sys
import tempfile
import unittest

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "ff-conflict-tests"))
SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "figurefoundry" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

from ff_export import export_figure, normalize_generated_svg
from ff_svg import audit_svg


CONFLICT_CASES = [
    {"id": "live-text-vs-outline", "test": "test_live_text_export_overrides_path_font_defaults",
     "retained": "native SVG text with declared required labels",
     "rejected": "outlined default font export as the editable master"},
    {"id": "physical-size-vs-tight-bbox", "test": "test_exact_size_wins_over_global_tight_bounding_box",
     "retained": "explicit physical canvas and bbox_inches=None",
     "rejected": "tight bounding box that silently changes the canvas dimensions"},
    {"id": "native-mesh-vs-raster-colorbar", "test": "test_colorbar_must_be_vectorized_independently",
     "retained": "native mesh and native colorbar cells",
     "rejected": "native main mesh accompanied by a rasterized colorbar"},
    {"id": "native-cells-vs-imshow", "test": "test_raster_heatmap_is_rejected_and_native_cells_are_accepted",
     "retained": "native pcolormesh cells",
     "rejected": "imshow bitmap embedded inside an SVG container"},
    {"id": "live-text-vs-tex-artists", "test": "test_existing_usetex_artists_fail_before_export",
     "retained": "live text or explicitly prepared editable alternatives",
     "rejected": "assuming svg.fonttype alone converts pre-existing usetex artists"},
    {"id": "complete-labels-vs-text-presence", "test": "test_some_live_text_does_not_substitute_for_missing_required_labels",
     "retained": "required-label inventory validation",
     "rejected": "passing an export because at least one unrelated text node remains"},
    {"id": "physical-svg-vs-preview-dpi", "test": "test_preview_dpi_does_not_change_native_svg_geometry",
     "retained": "physical dimensions and point sizes for the native SVG",
     "rejected": "treating preview DPI as a remedy for SVG font or canvas sizing"},
    {"id": "svg-master-vs-raster-preview", "test": "test_raster_preview_is_additional_to_a_required_svg_master",
     "retained": "editable SVG master with optional PDF/PNG derivatives",
     "rejected": "a PNG-only delivery under the editable-master contract"},
]


class ExportConflictTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ff-conflicts-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.fig, self.ax = plt.subplots(figsize=(90 / 25.4, 60 / 25.4))
        self.addCleanup(plt.close, self.fig)

    def source_svg(self):
        buffer = io.StringIO()
        self.fig.savefig(buffer, format="svg")
        # Input here comes from this test's own live Matplotlib figure.
        return normalize_generated_svg(buffer.getvalue())

    def write_source(self, name="candidate.svg"):
        path = self.base / name
        path.write_text(self.source_svg(), encoding="utf-8")
        return path

    def export(self, name="retained", **kwargs):
        options = {"width_mm": 90, "height_mm": 60, "min_font_pt": 6,
                   "formats": ["svg"], **kwargs}
        return export_figure(self.fig, self.base / name, **options)

    def test_live_text_export_overrides_path_font_defaults(self):
        self.ax.plot([0, 1, 2], [0, 1, 0], marker="o")
        self.ax.set_xlabel("Dose (mg)")
        self.ax.set_ylabel("Response (mV)")
        with matplotlib.rc_context({"svg.fonttype": "path"}):
            candidate = self.write_source()
            rejected = audit_svg(candidate, expected_labels=["Dose (mg)", "Response (mV)"])
            self.assertFalse(rejected["passed"])
            self.assertEqual(rejected["metrics"]["text_count"], 0)
            retained = self.export(expected_labels=["Dose (mg)", "Response (mV)"])
            self.assertEqual(matplotlib.rcParams["svg.fonttype"], "path")
        self.assertTrue(retained["svg_audit"]["passed"])
        self.assertGreater(retained["svg_audit"]["metrics"]["text_count"], 0)

    def test_exact_size_wins_over_global_tight_bounding_box(self):
        self.ax.set_position([0.35, 0.35, 0.3, 0.3])
        self.ax.plot([0, 1], [0, 1])
        self.ax.set_xlabel("Time (s)")
        with matplotlib.rc_context({"savefig.bbox": "tight", "svg.fonttype": "none"}):
            cropped = self.write_source()
            changed = audit_svg(cropped, width_mm=90, height_mm=60)
            self.assertFalse(changed["passed"])
            self.assertGreater(abs(changed["metrics"]["width_mm"] - 90), 1)
            retained = self.export(expected_labels=["Time (s)"])
            self.assertEqual(matplotlib.rcParams["savefig.bbox"], "tight")
        self.assertTrue(retained["svg_audit"]["passed"])
        self.assertAlmostEqual(retained["svg_audit"]["metrics"]["width_mm"], 90, places=5)
        self.assertAlmostEqual(retained["svg_audit"]["metrics"]["height_mm"], 60, places=5)

    def test_colorbar_must_be_vectorized_independently(self):
        mesh = self.ax.pcolormesh([[0, 1], [2, 3]], rasterized=False)
        colorbar = self.fig.colorbar(mesh, ax=self.ax)
        colorbar.set_label("Signal (mV)")
        colorbar.solids.set_rasterized(True)
        with matplotlib.rc_context({"svg.fonttype": "none"}):
            candidate = self.write_source()
        rejected = audit_svg(candidate)
        self.assertFalse(rejected["passed"])
        self.assertGreater(rejected["metrics"]["image_count"], 0)
        with self.assertRaisesRegex(ValueError, "rasterized artist"):
            self.export(name="blocked")
        self.assertFalse((self.base / "blocked.svg").exists())
        colorbar.solids.set_rasterized(False)
        retained = self.export(expected_labels=["Signal (mV)"])
        self.assertTrue(retained["svg_audit"]["passed"])
        self.assertEqual(retained["svg_audit"]["metrics"]["image_count"], 0)
        self.assertGreater(retained["svg_audit"]["metrics"]["path_count"], 200)

    def test_raster_heatmap_is_rejected_and_native_cells_are_accepted(self):
        self.ax.imshow([[0, 1], [2, 3]])
        self.ax.set_xlabel("Column")
        with self.assertRaisesRegex(ValueError, "Forbidden <image>"):
            self.export(name="bitmap")
        self.assertFalse((self.base / "bitmap.svg").exists())
        self.ax.clear()
        self.ax.pcolormesh([[0, 1], [2, 3]], rasterized=False)
        self.ax.set_xlabel("Column")
        retained = self.export(expected_labels=["Column"])
        self.assertTrue(retained["svg_audit"]["passed"])
        self.assertEqual(retained["svg_audit"]["metrics"]["image_count"], 0)

    def test_existing_usetex_artists_fail_before_export(self):
        self.ax.set_xlabel("Dose", usetex=True)
        with self.assertRaisesRegex(ValueError, "usetex=True.*recreate"):
            self.export(name="tex")
        self.assertFalse((self.base / "tex.svg").exists())
        # This check intentionally requires no TeX subprocess or font download.

    def test_some_live_text_does_not_substitute_for_missing_required_labels(self):
        self.ax.plot([0, 1], [1, 2])
        self.ax.set_xlabel("Dose")
        with self.assertRaisesRegex(ValueError, "Required editable label is missing"):
            self.export(name="incomplete", expected_labels=["Dose", "Missing scientific condition"])
        self.assertFalse((self.base / "incomplete.svg").exists())
        self.assertFalse((self.base / "incomplete.manifest.json").exists())

    def test_preview_dpi_does_not_change_native_svg_geometry(self):
        self.ax.plot([0, 1, 2], [0, 1, 0], marker="o")
        self.ax.set_xlabel("Dose (mg)")
        low = self.export(name="dpi100", dpi=100, expected_labels=["Dose (mg)"])
        high = self.export(name="dpi600", dpi=600, expected_labels=["Dose (mg)"])
        for key in ("width_mm", "height_mm", "min_font_pt", "max_font_pt"):
            self.assertAlmostEqual(low["svg_audit"]["metrics"][key], high["svg_audit"]["metrics"][key])
        self.assertEqual(low["files"]["svg"]["sha256"], high["files"]["svg"]["sha256"])
        self.assertEqual((low["raster_preview_dpi"], high["raster_preview_dpi"]), (100, 600))

    def test_raster_preview_is_additional_to_a_required_svg_master(self):
        self.ax.plot([0, 1], [1, 2])
        self.ax.set_xlabel("Dose")
        with self.assertRaisesRegex(ValueError, "SVG is the mandatory master"):
            self.export(name="png_only", formats=["png"])
        manifest = self.export(formats=["svg", "pdf", "png"], dpi=120, expected_labels=["Dose"])
        self.assertEqual(set(manifest["files"]), {"svg", "pdf", "png"})
        self.assertTrue((self.base / "retained.pdf").read_bytes().startswith(b"%PDF"))
        with Image.open(self.base / "retained.png") as preview:
            self.assertLessEqual(abs(preview.width - 90 / 25.4 * 120), 1)
            self.assertLessEqual(abs(preview.height - 60 / 25.4 * 120), 1)
        self.assertTrue(manifest["svg_audit"]["passed"])
        self.assertEqual(manifest["svg_audit"]["metrics"]["image_count"], 0)


if __name__ == "__main__":
    unittest.main()
