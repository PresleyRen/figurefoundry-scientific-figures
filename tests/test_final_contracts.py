"""Regressions for final integration findings, with independent input expectations."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "figurefoundry" / "scripts"))
from ff_plots import render_plots


class FinalIntegrationContracts(unittest.TestCase):
    def test_nonpositive_log_limits_cannot_be_silently_clamped(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / "values.csv").write_text("x,y\n1,2\n2,3\n3,4\n")
            for axis in ("x", "y"):
                with self.subTest(axis=axis):
                    spec = {"panels": [{"kind": "scatter", "data": "values.csv", "x": "x", "y": "y",
                                         axis + "scale": "log", axis + "lim": [0, 10]}], "formats": ["svg"]}
                    with self.assertRaisesRegex(ValueError, "strictly positive"):
                        render_plots(spec, base / axis, base_dir=base)
                    self.assertFalse((base / (axis + ".svg")).exists())

    def test_multiline_and_in_cell_labels_are_in_final_inventory(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / "matrix.csv").write_text("x,y,value\nA,C,1\nB,C,2\nA,D,3\nB,D,4\n")
            spec = {"figure": {"width_mm": 100, "height_mm": 75}, "formats": ["svg"],
                    "panels": [{"kind": "heatmap", "data": "matrix.csv", "x": "x", "y": "y", "value": "value",
                                "title": "Measured\nresponses", "colorbar_label": "Signal", "show_panel_id": True}]}
            report = render_plots(spec, base / "matrix", base_dir=base)
            for text in ("Measured", "responses", "Signal", "a", "1.00", "4.00"):
                self.assertIn(text, report["expected_labels"])
                self.assertIn(text, report["svg_audit"]["metrics"]["labels"])
            self.assertTrue(report["svg_audit"]["passed"])


if __name__ == "__main__":
    unittest.main()
