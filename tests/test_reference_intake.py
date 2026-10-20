"""Evidence extraction fixtures, not retrieved papers or experimental results.

Constructed HTML exercises the actual local parser. DOI/URL strings below are
illustrative provenance values only. Network calls are never part of intake.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "skills" / "figurefoundry" / "scripts"))

from ff_reference import extract_figures, reference_review_template, validate_benchmark_record


ARXIV_FIXTURE = """<!doctype html>
<html><head><title>Fallback fixture title</title>
<meta name="citation_title" content="Constructed Agent figure fixture">
<meta name="citation_author" content="Fixture Author">
<meta name="citation_doi" content="10.1234/fixture">
<link rel="canonical" href="https://example.org/paper/fixture">
</head><body><article>
<h1>Method</h1>
<div class="ltx_para" id="p-before"><p id="evidence-before">
The memory is updated after each accepted episode; the encoder is frozen.</p></div>
<figure class="ltx_figure" id="S1.F1">
  <figure class="ltx_figure ltx_subfigure" id="S1.F1.sf1">
    <img class="ltx_graphics" src="x1.png" alt="Encoder and persistent memory">
    <figcaption class="ltx_caption">(a) Architecture.</figcaption>
  </figure>
  <figure class="ltx_figure ltx_subfigure" id="S1.F1.sf2">
    <img src="../assets/x2.svg" alt="Success rate across seeds">
    <figcaption class="ltx_caption">(b) Evaluation.</figcaption>
  </figure>
  <figcaption class="ltx_caption"><span class="ltx_tag ltx_tag_figure">Figure 1:</span>
    Architecture and evaluation on the same task.</figcaption>
</figure>
<p id="evidence-after">The dashed edge denotes a conditional memory update.</p>
</article></body></html>
"""


class LocalReferenceIntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ff-reference-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def extract(self, html, **kwargs):
        self.html = self.base / "paper.html"
        self.html.write_text(html, encoding="utf-8")
        before = self.html.read_bytes()
        with patch("socket.socket", side_effect=AssertionError("Intake must not use the network")):
            result = extract_figures(self.html, "https://arxiv.org/html/2601.01234v1/paper.html", **kwargs)
        self.assertEqual(self.html.read_bytes(), before)
        self.assertEqual(result["source"]["sha256"], hashlib.sha256(before).hexdigest())
        json.dumps(result, ensure_ascii=False, allow_nan=False)
        return result

    def test_grouped_arxiv_figures_preserve_subcaptions_assets_and_evidence(self):
        result = self.extract(ARXIV_FIXTURE, context_blocks=1)
        self.assertEqual(result["source"]["metadata"]["title"], "Constructed Agent figure fixture")
        self.assertEqual(result["source"]["metadata"]["authors"], ["Fixture Author"])
        self.assertEqual(result["summary"]["figure_count"], 1)
        self.assertEqual(result["summary"]["image_count"], 2)
        figure = result["figures"][0]
        self.assertEqual(figure["caption"], "Figure 1: Architecture and evaluation on the same task.")
        self.assertEqual(figure["label"], "Figure 1:")
        self.assertEqual(figure["source_url"], "https://arxiv.org/html/2601.01234v1/paper.html#S1.F1")
        self.assertEqual([item["caption"] for item in figure["subfigures"]],
                         ["(a) Architecture.", "(b) Evaluation."])
        self.assertEqual([item["source_url"] for item in figure["images"]],
                         ["https://arxiv.org/html/2601.01234v1/x1.png",
                          "https://arxiv.org/html/assets/x2.svg"])
        self.assertEqual(figure["images"][1]["subfigure_id"], "fig-0001-s02")
        self.assertEqual(figure["subfigures"][1]["image_ids"], ["fig-0001-image-02"])
        self.assertEqual(figure["context"]["before"][0]["dom_id"], "evidence-before")
        self.assertIn("encoder is frozen", figure["context"]["before"][0]["text"])
        self.assertIn("conditional memory update", figure["context"]["after"][0]["text"])
        self.assertNotIn("Architecture.", json.dumps(figure["context"]))

    def test_ar5iv_style_div_caption_and_lazy_image_are_supported(self):
        result = self.extract('<p>Observation before.</p><div class="ltx_figure" id="F2">'
                              '<img data-src="//cdn.example.org/fig2.svg">'
                              '<div class="ltx_caption"><b>Fig. 2.</b> Observations.</div>'
                              '</div><p>Observation after.</p>')
        figure = result["figures"][0]
        self.assertEqual(figure["caption"], "Fig. 2. Observations.")
        image = figure["images"][0]
        self.assertEqual(image["source_attribute"], "data-src")
        self.assertEqual(image["source_url"], "https://cdn.example.org/fig2.svg")
        self.assertIsNone(image["alt"])
        self.assertEqual(image["alt_status"], "missing")
        self.assertEqual(result["summary"]["missing_alt_count"], 1)

    def test_scripts_templates_hidden_and_navigation_are_not_figure_evidence(self):
        html = """<script>const fake = '<figure><img src="evil.png"></figure>';
        fetch('https://example.org/should-never-be-called');</script>
        <style>.figure { content: "fabricated claim"; }</style>
        <template><figure><img src="template.png"><figcaption>Template</figcaption></figure></template>
        <nav><figure><img src="logo.png"></figure><p>Navigation claim</p></nav>
        <figure hidden><img src="hidden.png"></figure>
        <p>Evidence <script>secret()</script>only.</p>
        <figure><img src="valid.svg" alt="True fixture">
        <figcaption>Visible <style>bad-css</style>caption.</figcaption></figure>"""
        result = self.extract(html)
        self.assertEqual(result["summary"]["figure_count"], 1)
        self.assertEqual(result["summary"]["image_count"], 1)
        self.assertEqual(result["figures"][0]["caption"], "Visible caption.")
        self.assertEqual(result["figures"][0]["context"]["before"][0]["text"], "Evidence only.")
        self.assertNotIn("secret()", json.dumps(result))

    def test_missing_empty_and_unicode_alt_are_distinct_without_fabrication(self):
        result = self.extract('<figure><img src="a.svg"><img src="b.svg" alt="">'
                              '<img src="c.svg" alt="细胞 &amp; DNA，n=8">'
                              '<figcaption>真实标签 &amp; 单位</figcaption></figure>')
        images = result["figures"][0]["images"]
        self.assertEqual([image["alt_status"] for image in images], ["missing", "empty", "present"])
        self.assertEqual([image["alt"] for image in images], [None, "", "细胞 & DNA，n=8"])
        self.assertEqual(result["summary"]["empty_alt_count"], 1)
        self.assertEqual(result["figures"][0]["caption"], "真实标签 & 单位")

    def test_base_srcset_and_picture_urls_resolve_without_resource_downloads(self):
        result = self.extract('<head><base href="../assets/"></head><figure>'
                              '<picture><source srcset="plot.svg 1x, plot@2.svg 2x">'
                              '<img alt="Density plot"></picture>'
                              '<img src="fallback.png" srcset="small.png 400w, large.png 800w" alt="Zoom">'
                              '<figcaption>Figure with responsive assets.</figcaption></figure>')
        images = result["figures"][0]["images"]
        self.assertEqual(result["source"]["asset_base_url"], "https://arxiv.org/html/assets/")
        self.assertEqual(images[0]["source_attribute"], "srcset")
        self.assertEqual(images[0]["source_url"], "https://arxiv.org/html/assets/plot.svg")
        self.assertEqual([entry["descriptor"] for entry in images[0]["srcset"]], ["1x", "2x"])
        self.assertEqual(images[1]["srcset"][1]["source_url"], "https://arxiv.org/html/assets/large.png")
        self.assertEqual(images[1]["source_url"], "https://arxiv.org/html/assets/fallback.png")
        self.assertEqual(sorted(path.name for path in self.base.iterdir()), ["paper.html"])

    def test_unsupported_and_malformed_asset_urls_are_recorded_as_unresolved(self):
        for bad in ("javascript:alert(1)", "file:///tmp/private.png", "data:image/png;base64,AA==", "https://[bad"):
            with self.subTest(source=bad):
                result = self.extract(f'<head><base href="javascript:bad"></head>'
                                      f'<figure><img src="{bad}" alt="Fixture"><figcaption>Fixture</figcaption></figure>')
                self.assertIsNone(result["figures"][0]["images"][0]["source_url"])
                self.assertEqual(result["summary"]["unresolved_image_count"], 1)
                self.assertTrue(result["warnings"])

    def test_ungrouped_images_require_explicit_intake_option(self):
        html = '<p>Inline evidence before.</p><img id="loose" src="panel.svg" alt="Panel"><p>After.</p>'
        default = self.extract(html)
        self.assertEqual(default["figures"], [])
        self.assertEqual(default["summary"]["ungrouped_image_count"], 1)
        explicit = self.extract(html, include_ungrouped=True, context_blocks=1)
        figure = explicit["figures"][0]
        self.assertEqual(figure["kind"], "ungrouped-image")
        self.assertEqual(figure["caption"], "")
        self.assertEqual(figure["context"]["before"][0]["text"], "Inline evidence before.")
        self.assertEqual(explicit["summary"]["figure_count"], 0)
        self.assertEqual(explicit["summary"]["record_count"], 1)

    def test_no_image_or_caption_is_reported_and_inline_svg_is_identified(self):
        result = self.extract('<figure id="vector"><svg><text>Native example</text></svg></figure>')
        figure = result["figures"][0]
        self.assertTrue(figure["inline_svg_present"])
        self.assertEqual(figure["caption"], "")
        self.assertEqual(figure["images"], [])
        self.assertEqual(len(figure["issues"]), 2)

    def test_context_limit_omitted_paragraph_end_tags_and_determinism(self):
        html = '<p>First paragraph<p>Closest paragraph<figure><img src="a.svg" alt="a">' \
               '<figcaption>Fixture.</figcaption></figure><p>After</p>'
        result = self.extract(html, context_blocks=1)
        self.assertEqual(result["figures"][0]["context"]["before"][0]["text"], "Closest paragraph")
        self.assertEqual(result, extract_figures(self.html, result["source"]["url"], context_blocks=1))
        empty_context = self.extract(html, context_blocks=0)
        self.assertEqual(empty_context["figures"][0]["context"], {"before": [], "after": []})

    def test_review_questions_remain_pending_and_are_independent(self):
        result = self.extract(ARXIV_FIXTURE)
        review = result["figures"][0]["review"]
        self.assertEqual(review["status"], "pending")
        self.assertEqual(review["observations"], [])
        self.assertEqual(review["inferences"], [])
        self.assertTrue(all(check["status"] == "pending" for check in review["checks"]))
        by_id = {check["id"]: check for check in review["checks"]}
        self.assertIn("frozen invariants", by_id["agent-update"]["question"])
        self.assertIn("causation or comparison", by_id["relations"]["question"])
        self.assertIn("markers and line styles", by_id["semantic-style"]["question"])
        review["checks"][0]["evidence"].append("manually-reviewed evidence")
        self.assertEqual(reference_review_template()["checks"][0]["evidence"], [])

    def test_invalid_source_url_or_context_parameters_fail_clearly(self):
        path = self.base / "fixture.html"
        path.write_text("<figure></figure>", encoding="utf-8")
        for url in (None, "", "example.org/paper", "file:///paper.html", "https://[bad"):
            with self.subTest(url=url):
                with self.assertRaisesRegex(ValueError, "source_url"):
                    extract_figures(path, url)
        for count in (-1, 1.5, True, "2"):
            with self.subTest(context=count):
                with self.assertRaisesRegex(ValueError, "context_blocks"):
                    extract_figures(path, "https://example.org/paper", context_blocks=count)
        with self.assertRaisesRegex(ValueError, "include_ungrouped"):
            extract_figures(path, "https://example.org/paper", include_ungrouped=1)


class BenchmarkProvenanceTests(unittest.TestCase):
    def record(self):
        return {
            "id": "fixture-literature-curve",
            "origin": "digitized-literature",
            "source": {"doi": "10.1234/fixture", "figure": "Figure 3b"},
            "units": {"time": "s", "response": "mV"},
            "digitization": {"method": "Manual axis calibration and curve point selection",
                             "tool": "Fixture digitizer", "tool_version": "1.0"},
            "transformations": [],
            "uncertainty": {"status": "unknown", "description": "Reading uncertainty was not estimated."},
        }

    def test_complete_record_retains_unknown_uncertainty_and_original_fields(self):
        record = self.record()
        original = deepcopy(record)
        report = validate_benchmark_record(record)
        self.assertTrue(report["passed"], report)
        self.assertEqual(record, original)
        self.assertTrue(report["warnings"])
        self.assertNotIn("value", report["record"]["uncertainty"])
        self.assertEqual(report["normalized_source"]["url"], "https://doi.org/10.1234/fixture")
        report["record"]["source"]["figure"] = "Mutated report only"
        self.assertEqual(record, original)

    def test_each_required_provenance_field_is_actually_checked(self):
        for key in ("id", "origin", "source", "units", "digitization", "transformations", "uncertainty"):
            with self.subTest(field=key):
                record = self.record()
                del record[key]
                report = validate_benchmark_record(record)
                self.assertFalse(report["passed"], report)
                self.assertTrue(any(key in error for error in report["errors"]), report)
        for key in ("doi", "figure"):
            with self.subTest(source=key):
                record = self.record()
                del record["source"][key]
                self.assertFalse(validate_benchmark_record(record)["passed"])

    def test_invalid_schema_types_and_url_schemes_return_reports_without_crashing(self):
        for origin in ([], {}, 7, None):
            record = self.record()
            record["origin"] = origin
            self.assertFalse(validate_benchmark_record(record)["passed"])
        for status in ([], {}, 7, None):
            record = self.record()
            record["uncertainty"]["status"] = status
            self.assertFalse(validate_benchmark_record(record)["passed"])
        for source in ({"url": "javascript:alert(1)", "figure": "1"},
                       {"doi": "not-a-doi", "figure": "1"},
                       {"url": "https://[bad", "figure": "1"},
                       {"url": "https://example.org/paper", "figure": 1},
                       {"doi": "10.1234/fixture", "table": ""}):
            record = self.record()
            record["source"] = source
            self.assertFalse(validate_benchmark_record(record)["passed"])
        for record in (None, [], "text", {"not-finite": float("nan")}):
            self.assertFalse(validate_benchmark_record(record)["passed"])

    def test_reported_table_data_use_explicit_origin_without_fictitious_digitization(self):
        record = self.record()
        record["origin"] = "reported-literature"
        record["source"] = {"url": "https://example.org/paper", "table": "Table 2, row B"}
        del record["digitization"]
        record["uncertainty"] = {"status": "reported", "description": "SD is supplied in the cited table."}
        report = validate_benchmark_record(record)
        self.assertTrue(report["passed"], report)
        self.assertIsNone(report["normalized_source"]["doi"])
        self.assertNotIn("digitization", report["record"])

    def test_transformations_and_local_data_provenance_are_explicit(self):
        record = self.record()
        record["source"]["doi"] = "https://doi.org/10.1234/fixture"
        record["transformations"] = [
            {"operation": "unit_conversion", "details": "Multiply source seconds by 1000 to report ms."},
            "No smoothing or interpolation was used.",
        ]
        record["units"]["time"] = "ms"
        record["data"] = {"file": "digitized-fixture.csv", "sha256": "a" * 64}
        report = validate_benchmark_record(record)
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["normalized_source"]["doi"], "10.1234/fixture")
        self.assertEqual(report["record"]["transformations"], record["transformations"])
        for mutation in ({"transformations": [{"operation": "smooth"}]},
                         {"transformations": None},
                         {"data": {"file": "digitized.csv", "sha256": "bad"}}):
            self.assertFalse(validate_benchmark_record({**record, **mutation})["passed"])

    def test_uncertainty_values_require_nonnegative_numbers_and_units(self):
        record = self.record()
        record["uncertainty"] = {"status": "estimated", "description": "Estimated from fixture pixel calibration.",
                                 "value": 0, "unit": "mV"}
        self.assertTrue(validate_benchmark_record(record)["passed"])
        for value in (-1, True, "1", float("inf"), float("nan")):
            bad = deepcopy(record)
            bad["uncertainty"]["value"] = value
            self.assertFalse(validate_benchmark_record(bad)["passed"])
        bad = deepcopy(record)
        del bad["uncertainty"]["unit"]
        self.assertFalse(validate_benchmark_record(bad)["passed"])
        bad = deepcopy(record)
        bad["uncertainty"]["status"] = "unknown"
        self.assertFalse(validate_benchmark_record(bad)["passed"])


if __name__ == "__main__":
    unittest.main()

