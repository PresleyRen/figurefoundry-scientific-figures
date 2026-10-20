"""Real CLI regressions for default labels and the final minimum-font contract."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "skills" / "figurefoundry" / "scripts" / "figurefoundry.py"


class DiagramCLIContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)

    def run_cli(self, command, spec, name, minimum=None):
        specification = self.folder / f"{name}.json"
        specification.write_text(json.dumps(spec), encoding="utf-8")
        output = self.folder / f"{name}.svg"
        args = [sys.executable, str(CLI), command, "--spec", str(specification), "--out", str(output)]
        if minimum is not None:
            args.append(f"--min-font-pt={minimum}")
        result = subprocess.run(args, cwd=self.folder, capture_output=True, text=True, timeout=20)
        self.assertTrue(result.stdout.strip(), result.stderr)
        return result.returncode, json.loads(result.stdout), output

    def diagram(self, minimum=6):
        return {
            "width_mm": 90, "height_mm": 65, "font_pt": 8, "min_font_pt": minimum,
            "title": "Assay workflow",
            "groups": [{"id": "workflow", "label": "Workflow", "x": 3, "y": 18, "width": 83, "height": 35}],
            "nodes": [
                {"id": "sample", "x": 5, "y": 30, "width": 25, "height": 18},
                {"id": "assay", "x": 57, "y": 30, "width": 25, "height": 18},
            ],
            "edges": [{"source": "sample", "target": "assay", "label": "transfer"}],
        }

    def composition(self, minimum=8):
        source = self.folder / "source.svg"
        source.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="40mm" height="20mm" viewBox="0 0 40 20">'
            '<rect x="2" y="2" width="36" height="16" fill="#EEF3F7"/>'
            '<text x="4" y="11" font-size="2.4694444444" font-family="sans-serif">Seven point label</text>'
            '</svg>', encoding="utf-8"
        )
        return {"width_mm": 40, "height_mm": 20, "min_font_pt": minimum,
                "panels": [{"path": "source.svg", "x_mm": 0, "y_mm": 0, "width_mm": 40, "height_mm": 20}]}

    def test_omitted_node_label_uses_id_and_returns_success(self):
        code, result, output = self.run_cli("diagram", self.diagram(), "default-labels")
        self.assertEqual(code, 0, result)
        self.assertTrue(result["passed"])
        self.assertIn("sample", result["audit"]["metrics"]["labels"])
        self.assertIn("assay", result["audit"]["metrics"]["labels"])
        self.assertEqual(result["audit"]["metrics"]["expected_labels_checked"], 2)
        self.assertTrue(output.exists())

    def test_default_cli_honors_spec_minimum_for_diagram_and_composition(self):
        code, result, _ = self.run_cli("diagram", self.diagram(8), "eight-point-diagram")
        self.assertEqual(code, 0, result)
        self.assertGreaterEqual(result["audit"]["metrics"]["min_font_pt"], 8 - 1e-5)
        code, result, output = self.run_cli("compose", self.composition(8), "eight-point-composition")
        self.assertEqual(code, 2, result)
        self.assertFalse(result["passed"])
        self.assertTrue(any("minimum is 8" in error for error in result["audit"]["errors"]), result)
        self.assertTrue(output.exists(), "A failed final audit should leave an inspectable composition")

    def test_explicit_flag_overrides_spec_and_rejects_nonpositive_nonfinite_values(self):
        for command, spec in [("diagram", self.diagram(8)), ("compose", self.composition(8))]:
            with self.subTest(command=command, minimum=6):
                code, result, _ = self.run_cli(command, spec, f"{command}-override", minimum=6)
                self.assertEqual(code, 0, result)
                self.assertAlmostEqual(result["audit"]["metrics"]["min_font_pt"], 7, places=4)
            for index, minimum in enumerate([0, -1, "nan", "inf", "-inf"]):
                with self.subTest(command=command, minimum=minimum):
                    code, result, output = self.run_cli(command, spec, f"{command}-invalid-{index}", minimum=minimum)
                    self.assertEqual(code, 2, result)
                    self.assertFalse(result["passed"])
                    self.assertIn("finite positive", result["error"])
                    self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
