"""CLI, table input, journal-profile, and registry contracts.

Real files and subprocesses exercise the public interface. All fixture data and
outputs are temporary; HTTPS journal URLs below are illustrative inputs and are
never fetched or represented as verified journal requirements.
"""

from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "ff-cli-data-tests"))
REPOSITORY = Path(__file__).resolve().parents[1]
SKILL = REPOSITORY / "skills" / "figurefoundry"
SCRIPTS = SKILL / "scripts"
CLI = SCRIPTS / "figurefoundry.py"
sys.path.insert(0, str(SCRIPTS))

import numpy as np
import pandas as pd

from ff_data import numeric, read_table
from ff_journal import review_profile
from ff_plots import render_plots


class _TemporaryCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ff-cli-data-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def cli(self, *arguments, expected_code=0):
        process = subprocess.run([sys.executable, str(CLI), *map(str, arguments)],
                                 cwd=self.base, capture_output=True, text=True, timeout=30)
        self.assertEqual(process.returncode, expected_code,
                         f"Command: {arguments!r}\nstdout: {process.stdout}\nstderr: {process.stderr}")
        self.assertNotIn("Traceback", process.stderr)
        try:
            return json.loads(process.stdout)
        except json.JSONDecodeError as exc:
            self.fail(f"CLI did not return JSON: {exc}; stdout={process.stdout!r}")

    def write_json(self, name, value):
        path = self.base / name
        path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        return path


class DataInputContractTests(_TemporaryCase):
    ROWS = [
        {"subject": "s1", "condition": "Control", "response_mg": 1.25, "replicate": 1},
        {"subject": "s2", "condition": "处理", "response_mg": None, "replicate": 2},
        {"subject": "s3", "condition": "Control", "response_mg": 3.5, "replicate": 3},
    ]

    def roundtrip(self, path, *, sheet=0):
        expected = pd.DataFrame(self.ROWS)
        original_bytes = path.read_bytes()
        actual, provenance = read_table(path, sheet=sheet)
        pd.testing.assert_frame_equal(actual, expected)
        self.assertEqual(path.read_bytes(), original_bytes)
        self.assertEqual(provenance["sha256"], hashlib.sha256(original_bytes).hexdigest())
        self.assertEqual(provenance["file"], path.name)
        self.assertEqual(provenance["rows"], 3)
        self.assertEqual(provenance["columns"], list(expected.columns))
        self.assertEqual(provenance["missing_by_column"],
                         {"subject": 0, "condition": 0, "response_mg": 1, "replicate": 0})
        return provenance

    def test_csv_roundtrip_records_exact_source_hash(self):
        path = self.base / "observations.csv"
        pd.DataFrame(self.ROWS).to_csv(path, index=False)
        self.roundtrip(path)

    def test_tsv_roundtrip_records_exact_source_hash(self):
        path = self.base / "observations.tsv"
        pd.DataFrame(self.ROWS).to_csv(path, sep="\t", index=False)
        self.roundtrip(path)

    def test_json_row_array_roundtrip_records_exact_source_hash(self):
        self.roundtrip(self.write_json("observations.json", self.ROWS))

    def test_jsonl_roundtrip_records_exact_source_hash(self):
        path = self.base / "observations.jsonl"
        path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in self.ROWS) + "\n",
                        encoding="utf-8")
        self.roundtrip(path)

    def test_xlsx_roundtrip_respects_sheet_name_and_index(self):
        path = self.base / "observations.xlsx"
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            pd.DataFrame({"unrelated": [99]}).to_excel(writer, sheet_name="Cover", index=False)
            pd.DataFrame(self.ROWS).to_excel(writer, sheet_name="Experiment", index=False)
        named = self.roundtrip(path, sheet="Experiment")
        indexed = self.roundtrip(path, sheet=1)
        self.assertEqual(named["sheet"], "Experiment")
        self.assertEqual(indexed["sheet"], 1)
        self.assertEqual(named["sha256"], indexed["sha256"])

    def test_numeric_conversion_rejects_nonnumeric_and_infinite_observations(self):
        with self.assertRaisesRegex(ValueError, "non-numeric"):
            numeric(pd.DataFrame({"value": [1, "instrument failed", 3]}), "value")
        for bad in (float("inf"), float("-inf"), "inf", "-Infinity"):
            with self.subTest(value=bad):
                with self.assertRaisesRegex(ValueError, "infinite"):
                    numeric(pd.DataFrame({"value": [1, bad, 3]}), "value")

    def test_missing_numeric_values_are_explicitly_allowed_or_rejected(self):
        frame = pd.DataFrame({"value": [1.0, np.nan, 3.0]})
        before = frame.copy(deep=True)
        result = numeric(frame, "value")
        np.testing.assert_allclose(result.to_numpy(), [1, np.nan, 3], equal_nan=True)
        with self.assertRaisesRegex(ValueError, "missing observations"):
            numeric(frame, "value", allow_missing=False)
        pd.testing.assert_frame_equal(frame, before)

    def test_duplicate_source_headers_are_rejected_before_pandas_mangling(self):
        for extension, separator in (("csv", ","), ("tsv", "\t")):
            with self.subTest(extension=extension):
                path = self.base / f"ambiguous.{extension}"
                path.write_text(f"value{separator}value\n1{separator}2\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "(?i)(duplicate|unique)"):
                    read_table(path)

    def test_empty_and_malformed_table_contracts_fail_explicitly(self):
        empty = self.base / "empty.csv"
        empty.write_text("value,subject\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "No observations"):
            read_table(empty)
        for value in ({"value": [1, 2]}, [1, 2], [None]):
            with self.subTest(value=value):
                invalid = self.write_json("invalid.json", value)
                with self.assertRaisesRegex(ValueError, "array of row objects"):
                    read_table(invalid)
        unknown = self.base / "data.bin"
        unknown.write_bytes(b"value\n1\n")
        with self.assertRaisesRegex(ValueError, "Unsupported data extension"):
            read_table(unknown)


class CLIContractTests(_TemporaryCase):
    def line_spec(self):
        data = self.base / "data.csv"
        data.write_text("time,response\n0,1\n1,2\n2,3\n", encoding="utf-8")
        return {"version": 1, "formats": ["svg"],
                "figure": {"width_mm": 90, "height_mm": 60},
                "panels": [{"kind": "line", "data": data.name, "x": "time", "y": "response",
                            "xlabel": "Time (s)", "ylabel": "Response (mV)"}]}

    def test_doctor_has_machine_readable_availability_without_certification(self):
        result = self.cli("doctor")
        self.assertEqual(result["version"], json.loads((SKILL / "assets" / "capabilities.json").read_text())["version"])
        self.assertTrue(result["native_data_plotting_available"])
        self.assertTrue(result["native_svg_diagrams_and_audit"])
        self.assertEqual(set(result["python_packages"]), {"matplotlib", "numpy", "pandas", "scipy", "openpyxl"})
        self.assertTrue(all(isinstance(value, bool) for value in result["optional_executables"].values()))
        self.assertIn("not an integration test", result["note"])

    def test_capabilities_queries_are_case_insensitive_and_specific(self):
        svg = self.cli("capabilities", "--query", "ff-svg-01")
        self.assertEqual([item["id"] for item in svg["matches"]], ["FF-SVG-01"])
        data = self.cli("capabilities", "--query", "XlSx")
        self.assertIn("FF-DATA-01", [item["id"] for item in data["matches"]])
        absent = self.cli("capabilities", "--query", "definitely-no-such-capability-314159")
        self.assertEqual(absent["matches"], [])

    def test_inspect_reports_real_shape_missingness_and_hash(self):
        path = self.base / "source.csv"
        path.write_text("subject,value\ns1,1.5\ns2,\ns3,3.5\n", encoding="utf-8")
        result = self.cli("inspect", path)
        self.assertEqual(result["source"]["rows"], 3)
        self.assertEqual(result["source"]["missing_by_column"]["value"], 1)
        self.assertEqual(result["source"]["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(set(result["dtypes"]), {"subject", "value"})

    def test_invalid_json_and_schema_shapes_return_structured_exit_two(self):
        valid = self.line_spec()
        cases = [
            "{broken JSON", '{"version":NaN}', "[]", "null", '"not a spec"',
            json.dumps({"version": 99, "panels": []}),
            json.dumps({"panels": [42]}),
            json.dumps({"panels": {"kind": "line"}}),
            json.dumps({**valid, "figure": []}),
            json.dumps({"panels": [{"kind": "unsupported"}]}),
        ]
        for index, content in enumerate(cases):
            with self.subTest(content=content):
                path = self.base / f"invalid_{index}.json"
                path.write_text(content, encoding="utf-8")
                result = self.cli("plot", "--spec", path, "--out", self.base / f"bad_{index}", expected_code=2)
                self.assertFalse(result["passed"])
                self.assertIsInstance(result["error"], str)
                self.assertFalse((self.base / f"bad_{index}.svg").exists())

    def test_existing_output_is_protected_with_exit_two_and_unchanged_bytes(self):
        occupied = self.base / "occupied.svg"
        sentinel = b"KEEP THE EXISTING USER ARTIFACT\n"
        occupied.write_bytes(sentinel)
        plot_spec = self.write_json("plot.json", self.line_spec())
        diagram_spec = self.write_json("diagram.json", {"nodes": [{"id": "a", "label": "Sample"}]})
        for command, spec in (("plot", plot_spec), ("diagram", diagram_spec)):
            with self.subTest(command=command):
                result = self.cli(command, "--spec", spec, "--out", occupied, expected_code=2)
                self.assertFalse(result["passed"])
                self.assertEqual(result["error_type"], "FileExistsError")
                self.assertIn("overwrite", result["error"].lower())
                self.assertEqual(occupied.read_bytes(), sentinel)

    def test_audit_labels_file_must_be_an_array_of_strings(self):
        document = self.base / "native.svg"
        document.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="90mm" height="60mm" '
                            'viewBox="0 0 90 60"><text font-size="3">Dose</text></svg>', encoding="utf-8")
        labels = self.write_json("labels.json", {"label": "Dose"})
        rejected = self.cli("audit", document, "--labels", labels, expected_code=2)
        self.assertIn("array of strings", rejected["error"])
        labels = self.write_json("labels.json", ["Dose"])
        accepted = self.cli("audit", document, "--labels", labels)
        self.assertTrue(accepted["passed"])

    def test_capability_registry_pointers_resolve_before_packaging(self):
        registry = json.loads((SKILL / "assets" / "capabilities.json").read_text(encoding="utf-8"))
        identifiers = [entry["id"] for entry in registry["capabilities"]]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        self.assertIn("FF-DATA-01", identifiers)
        self.assertIn("FF-JOURNAL-01", identifiers)
        for entry in registry["capabilities"]:
            for field, base in (("module", SKILL), ("reference", SKILL), ("tests", REPOSITORY)):
                relative = entry.get(field)
                if relative is None:
                    continue
                with self.subTest(capability=entry["id"], field=field):
                    target = (base / relative).resolve()
                    self.assertTrue(target.is_relative_to(base.resolve()), relative)
                    self.assertTrue(target.is_file(), f"Broken {entry['id']} {field}: {target}")
        for identifier in ("FF-DATA-01", "FF-JOURNAL-01"):
            entry = next(item for item in registry["capabilities"] if item["id"] == identifier)
            self.assertEqual(entry["tests"], "tests/test_cli_and_data.py")


class JournalProfileContractTests(_TemporaryCase):
    TODAY = date(2026, 10, 20)

    def profile(self):
        return {"journal": "Illustrative Journal", "article_type": "Research Article", "stage": "final artwork",
                "source_urls": ["https://example.org/journal/artwork-instructions"],
                "checked_on": self.TODAY.isoformat(), "width_mm": 90, "height_mm": 60,
                "min_font_pt": 6, "submission_formats": ["svg", "pdf"], "status": "source-checked"}

    def test_planning_profile_warns_without_claiming_or_blocking_certification(self):
        result = review_profile({"journal": "Illustrative Journal", "article_type": "Article", "stage": "initial"},
                                today=self.TODAY)
        self.assertTrue(result["passed"])
        warnings = " ".join(result["warnings"])
        self.assertIn("planning", warnings)
        self.assertIn("no verification date", warnings)
        self.assertIn("No width_mm", warnings)
        self.assertEqual(result["journal_acceptance"], "not-certified")
        self.assertIn("sources were not fetched", result["scope"])

    def test_current_dated_complete_profile_passes_only_field_validation(self):
        profile = self.profile()
        result = review_profile(profile, today=self.TODAY)
        self.assertTrue(result["passed"], result["errors"])
        self.assertEqual(result["warnings"], [])
        self.assertEqual(result["journal_acceptance"], "not-certified")
        self.assertIn("field validation only", result["scope"])
        self.assertEqual(result["profile"], profile)

    def test_future_verification_date_fails_and_stale_record_warns(self):
        profile = self.profile()
        profile["checked_on"] = (self.TODAY + timedelta(days=1)).isoformat()
        future = review_profile(profile, today=self.TODAY)
        self.assertFalse(future["passed"])
        self.assertTrue(any("future" in error for error in future["errors"]))
        profile["checked_on"] = (self.TODAY - timedelta(days=91)).isoformat()
        stale = review_profile(profile, today=self.TODAY)
        self.assertTrue(stale["passed"])
        self.assertTrue(any("recheck" in warning for warning in stale["warnings"]))

    def test_conflicting_sources_require_a_recorded_stage_specific_resolution(self):
        profile = self.profile()
        profile["conflicting_sources"] = ["Initial submission instruction", "Final artwork instruction"]
        unresolved = review_profile(profile, today=self.TODAY)
        self.assertFalse(unresolved["passed"])
        self.assertTrue(any("resolution" in error for error in unresolved["errors"]))
        profile["resolution"] = "Use the final-artwork width for this final-artwork submission stage."
        self.assertTrue(review_profile(profile, today=self.TODAY)["passed"])

    def test_invalid_source_and_numeric_types_have_controlled_validation_errors(self):
        for urls in ([42], ["http://example.org/instructions"]):
            with self.subTest(urls=urls):
                profile = self.profile()
                profile["source_urls"] = urls
                result = review_profile(profile, today=self.TODAY)
                self.assertFalse(result["passed"])
                self.assertTrue(result["errors"])
        for value in (True, 0, -1, float("nan"), float("inf")):
            with self.subTest(width=value):
                profile = self.profile()
                profile["width_mm"] = value
                self.assertFalse(review_profile(profile, today=self.TODAY)["passed"])

    def test_journal_cli_exits_two_for_future_date_and_zero_for_current_profile(self):
        profile = self.profile()
        profile["checked_on"] = (date.today() + timedelta(days=1)).isoformat()
        path = self.write_json("profile.json", profile)
        self.assertFalse(self.cli("journal", "--profile", path, expected_code=2)["passed"])
        profile["checked_on"] = date.today().isoformat()
        path = self.write_json("profile.json", profile)
        self.assertTrue(self.cli("journal", "--profile", path)["passed"])


class LogAxisInputContractTests(_TemporaryCase):
    def spec(self, **panel_fields):
        return {"version": 1, "formats": ["svg"],
                "figure": {"width_mm": 90, "height_mm": 70, "font_pt": 8, "min_font_pt": 6},
                "panels": [{"kind": "scatter", "data": "data.csv", "x": "x", "y": "y",
                            "xlabel": "Concentration (mM)", "ylabel": "Response (mV)", **panel_fields}]}

    def test_nonpositive_raw_observations_are_rejected_on_each_log_axis(self):
        for axis in ("x", "y"):
            for bad in (0, -1):
                with self.subTest(axis=axis, value=bad):
                    rows = [{"x": 1, "y": 1}, {"x": 10, "y": 10}]
                    rows[0][axis] = bad
                    pd.DataFrame(rows).to_csv(self.base / "data.csv", index=False)
                    output = self.base / f"blocked_{axis}_{bad}"
                    with self.assertRaisesRegex(ValueError, "Log .*nonpositive"):
                        render_plots(self.spec(**{axis + "scale": "log"}), output, base_dir=self.base)
                    self.assertFalse(output.with_suffix(".svg").exists())

    def test_positive_log_data_exports_literal_editable_ticks(self):
        (self.base / "data.csv").write_text("x,y\n1,1\n10,10\n100,100\n", encoding="utf-8")
        result = render_plots(self.spec(xscale="log", yscale="log"), self.base / "positive", base_dir=self.base)
        self.assertTrue(result["svg_audit"]["passed"])
        self.assertEqual(result["svg_audit"]["metrics"]["image_count"], 0)
        self.assertTrue({"1", "10", "100"}.issubset(result["expected_labels"]))
        self.assertIn("Concentration (mM)", result["expected_labels"])


if __name__ == "__main__":
    unittest.main()
