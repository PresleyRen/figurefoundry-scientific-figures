"""Coverage is navigable to real modules, with actionable failure diagnostics."""
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "figurefoundry"
sys.path.insert(0, str(ROOT / "tools"))
from check_package import check_indexes
from render_coverage import render


class CoverageNavigationTests(unittest.TestCase):
    def setUp(self):
        self.registry, self.coverage, self.atlas = [json.loads((SKILL / "assets" / name).read_text())
                                                  for name in ("capabilities.json", "source-coverage.json", "specialty-routes.json")]

    def cli(self, *args):
        result = subprocess.run([sys.executable, str(SKILL / "scripts" / "figurefoundry.py"), *args],
                                text=True, capture_output=True, check=True)
        return json.loads(result.stdout)

    def test_every_documented_source_feature_has_concrete_extension_and_valid_links(self):
        self.assertEqual(check_indexes(self.registry, self.coverage, self.atlas), [])
        self.assertEqual((ROOT / "docs" / "COVERAGE.md").read_text(), render())

    def test_missing_feature_pointer_names_the_feature_and_path(self):
        altered = copy.deepcopy(self.coverage)
        feature = altered["sources"][0]["features"][0]
        feature["extension"]["target"] = "scripts/absent_module.py"
        errors = check_indexes(self.registry, altered, self.atlas)
        self.assertTrue(any(feature["id"] in error and "absent_module.py" in error for error in errors))

    def test_undefined_capability_and_duplicate_ids_are_actionable(self):
        altered = copy.deepcopy(self.coverage)
        feature = altered["sources"][0]["features"][0]
        feature["capabilities"] = ["FF-MISSING-99"]
        altered["sources"][0]["features"].append(copy.deepcopy(feature))
        errors = check_indexes(self.registry, altered, self.atlas)
        self.assertTrue(any("capability mapping" in error and feature["id"] in error for error in errors))
        self.assertIn("Duplicate feature IDs in source coverage", errors)

    def test_feature_without_implementation_reference_or_test_reports_the_gap(self):
        for field in ("implementation", "references", "tests"):
            with self.subTest(field=field):
                altered = copy.deepcopy(self.coverage)
                feature = altered["sources"][0]["features"][0]
                feature[field] = []
                errors = check_indexes(self.registry, altered, self.atlas)
                self.assertTrue(any(feature["id"] in error and field in error for error in errors))

    def test_source_filter_and_specific_feature_search_find_actual_implementation(self):
        result = self.cli("coverage", "--source", "s08", "--query", "R²")
        self.assertTrue(result["matches"])
        self.assertTrue(all(entry["source_id"] == "S08" for entry in result["matches"]))
        self.assertTrue(all("scripts/ff_plots.py" in entry["implementation"] for entry in result["matches"]))

    def test_chinese_specialty_terms_find_specific_data_and_integration_routes(self):
        for term, route in (("富集图", "SP-ENRICHMENT"), ("雨云图", "SP-RAINCLOUD"),
                            ("基因组关联", "SP-GWAS"), ("相图", "SP-PHASE-POINCARE")):
            with self.subTest(term=term):
                found = self.cli("atlas", "--query", term)["matches"]
                selected = next(item for item in found if item["id"] == route)
                self.assertTrue(selected["data"])
                self.assertTrue(selected["integration"])


if __name__ == "__main__":
    unittest.main()
