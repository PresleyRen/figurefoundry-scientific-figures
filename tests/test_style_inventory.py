import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "figurefoundry" / "scripts"))
from ff_inventory import inventory_sources
from ff_style import THEMES, resolve_plot_style


class StyleDefaultsTests(unittest.TestCase):
    def test_precedence_source_hash_and_input_immutability(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "defaults.json"
            path.write_text(json.dumps({"version": 1, "theme": "engineering", "figure": {"font_pt": 9},
                                        "panel_defaults": {"linewidth": 1.5},
                                        "palette": {"A": {"color": "#0072B2", "marker": "o", "linestyle": "-"}}}))
            spec = {"defaults": "defaults.json", "figure": {"font_pt": 10},
                    "panels": [{"kind": "line", "data": "a.csv", "linewidth": 2}]}
            original = copy.deepcopy(spec)
            result = resolve_plot_style(spec, base_dir=directory)
            self.assertEqual(result["figure"]["font_pt"], 10)
            self.assertEqual(result["figure"]["grid"], False)
            self.assertEqual(result["panels"][0]["linewidth"], 2)
            self.assertEqual(result["style_provenance"]["defaults"]["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(spec, original)

    def test_visual_defaults_do_not_override_statistics_or_data(self):
        for key in ("data", "unit", "estimator", "error", "fit"):
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, "scientific fields"):
                    resolve_plot_style({"panel_defaults": {key: "unexpected"}, "panels": []})

    def test_identity_stays_fixed_across_data_and_physical_layout_changes(self):
        a = {"theme": "compact", "palette": {"A": "#0072B2", "B": "#666666"},
             "figure": {"width_mm": 90}, "panels": [{"data": "first.csv"}]}
        b = copy.deepcopy(a)
        b["figure"]["width_mm"] = 180
        b["panels"][0]["data"] = "second.csv"
        self.assertEqual(resolve_plot_style(a)["style_provenance"]["style_sha256"],
                         resolve_plot_style(b)["style_provenance"]["style_sha256"])
        b["palette"]["A"] = "#D55E00"
        self.assertNotEqual(resolve_plot_style(a)["style_provenance"]["style_sha256"],
                            resolve_plot_style(b)["style_provenance"]["style_sha256"])

    def test_theme_choice_and_unknown_default_keys_are_explicit(self):
        for theme in THEMES:
            self.assertEqual(resolve_plot_style({"theme": theme, "panels": []})["style_provenance"]["theme"], theme)
        with self.assertRaisesRegex(ValueError, "theme"):
            resolve_plot_style({"theme": "mistyped"})
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "defaults.json").write_text('{"versoin":1}')
            with self.assertRaisesRegex(ValueError, "Unknown"):
                resolve_plot_style({"defaults": "defaults.json"}, base_dir=directory)


class SourceInventoryTests(unittest.TestCase):
    def test_python_and_notebook_locations_without_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            python = Path(directory, "plot.py")
            python.write_text("raise RuntimeError('must not execute')\nfig, ax = plt.subplots()\nax.set_xlabel('Dose')\nfig.savefig('draft.svg')\n")
            notebook = Path(directory, "analysis.ipynb")
            notebook.write_text(json.dumps({"cells": [{"cell_type": "markdown", "source": ["plt.savefig('ignore.png')"]},
                                                     {"cell_type": "code", "source": ["out = 'figure.svg'\n", "fig.savefig(out)\n"]}]}))
            before = python.read_bytes(), notebook.read_bytes()
            report = inventory_sources([directory])
            self.assertTrue(report["passed"])
            self.assertEqual(report["export_calls"], 2)
            calls = [e for f in report["files"] for e in f["entries"] if e["category"] == "export"]
            self.assertIn({"line": 4, "cell": None, "literal": "draft.svg"},
                          [{"line": e["line"], "cell": e["cell"], "literal": e["literal_output"]} for e in calls])
            dynamic = next(e for e in calls if e["cell"] == 1)
            self.assertIsNone(dynamic["literal_output"])
            self.assertEqual(dynamic["output_expression"], "out")
            self.assertEqual(before, (python.read_bytes(), notebook.read_bytes()))

    def test_parse_error_keeps_other_notebook_cells_locatable(self):
        with tempfile.TemporaryDirectory() as directory:
            notebook = Path(directory, "mixed.ipynb")
            notebook.write_text(json.dumps({"cells": [{"cell_type": "code", "source": "%matplotlib inline"},
                                                     {"cell_type": "code", "source": "fig.savefig('valid.svg')"}]}))
            report = inventory_sources([notebook])
            self.assertFalse(report["passed"])
            self.assertEqual(report["export_calls"], 1)
            self.assertEqual(report["files"][0]["parse_errors"][0]["cell"], 0)


if __name__ == "__main__":
    unittest.main()
