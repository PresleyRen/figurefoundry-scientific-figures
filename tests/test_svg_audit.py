"""Behavioral regression tests for the strict, offline SVG auditor."""

import io
import os
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "figurefoundry" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from ff_svg import audit_svg  # noqa: E402


def svg(body, *, width="90mm", height="60mm", viewbox="0 0 90 60", attributes=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{width}" height="{height}" viewBox="{viewbox}" {attributes}>'
            f'{body}</svg>')


TEXT = '<text x="5" y="20" font-size="3">Time (s)</text>'


class _AuditFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ff-svg-test-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "figure.svg"

    def check(self, content, **kwargs):
        if isinstance(content, bytes):
            self.path.write_bytes(content)
        else:
            self.path.write_text(content, encoding="utf-8")
        return audit_svg(self.path, **kwargs)

    def assertPasses(self, report):
        self.assertTrue(report["passed"], report["errors"])

    def assertFails(self, report, phrase):
        self.assertFalse(report["passed"])
        self.assertIn(phrase.lower(), "\n".join(report["errors"]).lower())


class SVGAuditTests(_AuditFixture):
    def test_native_shapes_and_editable_label(self):
        report = self.check(svg('<path d="M 2 40 L 20 30 C 30 25 40 20 50 10"/>'+TEXT),
                            width_mm=90, height_mm=60, expected_labels=["Time (s)"])
        self.assertPasses(report)
        self.assertEqual(report["metrics"]["text_count"], 1)
        self.assertEqual(report["metrics"]["path_count"], 1)
        self.assertEqual(report["metrics"]["image_count"], 0)
        self.assertAlmostEqual(report["metrics"]["min_font_pt"], 3*72/25.4)

    def test_viewbox_and_root_units_give_actual_points(self):
        document = svg('<text font-size="8px">Dose</text>', width="180pt", height="120pt",
                       viewbox="0 0 180 120")
        report = self.check(document, expected_labels=["Dose"], min_font_pt=8)
        self.assertPasses(report)
        self.assertAlmostEqual(report["metrics"]["min_font_pt"], 8)

    def test_svg_without_viewbox_uses_96dpi_css_pixels(self):
        report = self.check('<svg xmlns="http://www.w3.org/2000/svg" width="2in" height="1in">'
                            '<text font-size="8pt">Dose</text></svg>', min_font_pt=8)
        self.assertPasses(report)
        self.assertAlmostEqual(report["metrics"]["min_font_pt"], 8)
        self.assertAlmostEqual(report["metrics"]["width_mm"], 50.8)

    def test_inherited_transforms_expose_shrunken_font(self):
        document = svg('<g transform="translate(5 5) scale(0.5)" font-size="3">'
                       '<g transform="rotate(30)"><text>Small</text></g></g>')
        report = self.check(document, min_font_pt=5)
        self.assertFails(report, "smallest effective font")
        self.assertAlmostEqual(report["metrics"]["min_font_pt"], 1.5*72/25.4)

    def test_nonuniform_scale_uses_conservative_smallest_axis(self):
        report = self.check(svg('<text transform="scale(1 0.25)" font-size="4">Tiny</text>'))
        self.assertFails(report, "smallest effective font")
        self.assertAlmostEqual(report["metrics"]["min_font_pt"], 72/25.4)

    def test_font_shorthand_css_cascade_and_tspan_inheritance(self):
        document = svg('<style>text {font: 3px sans-serif}.main {font-size:4px}'
                       '#dose {font-size: 5px}</style>'
                       '<text id="dose" class="main" style="font-size:3px">Dose '
                       '<tspan font-size="80%">response</tspan></text>')
        report = self.check(document, expected_labels=["Dose response"])
        self.assertPasses(report)
        self.assertAlmostEqual(report["metrics"]["min_font_pt"], 2.4*72/25.4)

    def test_important_stylesheet_overrides_inline(self):
        report = self.check(svg('<style>text {font-size:1px !important}</style>'
                                '<text style="font-size:5px">Tiny</text>'))
        self.assertFails(report, "smallest effective font")

    def test_local_markers_and_clip_references_are_supported(self):
        document = svg('<defs><path id="marker" d="M 0 0 L 1 0 L 0 1 z"/>'
                       '<clipPath id="clip"><rect width="90" height="60"/></clipPath></defs>'
                       '<g clip-path="url(#clip)"><use xlink:href="#marker" x="5" y="5"/>'
                       +TEXT+'</g>')
        self.assertPasses(self.check(document, expected_labels=["Time (s)"]))

    def test_outlined_text_cannot_pass_live_text_requirement(self):
        document = svg('<defs><path id="glyph" d="M 0 0 L 1 2 L 2 0 Z"/></defs>'
                       '<use href="#glyph"/>')
        self.assertFails(self.check(document), "No visible native SVG text")
        self.assertPasses(self.check(document, require_text=False))

    def test_partial_outlining_is_caught_by_label_manifest(self):
        report = self.check(svg(TEXT+'<path d="M 0 0 L 1 1"/>'),
                            expected_labels=["Time (s)", "Concentration (mM)"])
        self.assertFails(report, "Required editable label is missing")

    def test_label_match_is_exact_not_substring(self):
        self.assertFails(self.check(svg(TEXT), expected_labels=["Time"]), "label is missing")

    def test_hidden_or_definition_only_text_does_not_satisfy_labels(self):
        for body in ('<text display="none">Time (s)</text>',
                     '<g opacity="0">'+TEXT+'</g>',
                     '<g visibility="hidden">'+TEXT+'</g>',
                     '<defs>'+TEXT+'</defs>',
                     '<text fill="none" stroke="none">Time (s)</text>',
                     '<text fill-opacity="0">Time (s)</text>'):
            with self.subTest(body=body):
                self.assertFails(self.check(svg(body), expected_labels=["Time (s)"]),
                                 "No visible native SVG text")

    def test_raster_and_embedded_svg_images_are_forbidden(self):
        for mime in ("image/png", "image/svg+xml"):
            report = self.check(svg(TEXT+f'<image href="data:{mime};base64,AAAA" '
                                    'width="10" height="10"/>'))
            self.assertFails(report, "Forbidden <image>")
            self.assertEqual(report["metrics"]["image_count"], 1)

    def test_active_content_external_resources_and_entities_fail(self):
        bodies = [
            '<script>alert(1)</script>', '<g onload="alert(1)"/>',
            '<foreignObject><div>Label</div></foreignObject>',
            '<use href="https://example.org/g.svg#plot"/>',
            '<path d="M 0 0 L 2 2" fill="url(https://example.org/fill.svg)"/>',
            '<style>text {fill:url(\'data:image/png;base64,AAAA\')}</style>',
            '<style>@import "https://example.org/style.css";</style>',
            '<style>text {fill: u\\72l(https://example.org/a)}</style>',
            '<path fill="u\\72l(https://example.org/a)" d="M 0 0 L 1 1"/>',
            '<animate attributeName="x" values="0;100" dur="1s"/>',
        ]
        for body in bodies:
            with self.subTest(body=body):
                self.assertFalse(self.check(svg(body+TEXT))["passed"])
        for declaration in ('<!DOCTYPE svg SYSTEM "https://example.org/svg.dtd">',
                            '<!DOCTYPE svg [<!ENTITY x "Time">]>'):
            self.assertFails(self.check(declaration+svg(TEXT)), "DTD and entity")
            self.assertFails(self.check((declaration+svg(TEXT)).encode("utf-16")), "DTD and entity")

    def test_duplicate_missing_and_cyclic_references_fail(self):
        fixtures = [
            ('<g id="same"/><path id="same" d="M 0 0 L 1 1"/>', "Duplicate"),
            ('<use href="#absent"/>', "Unresolved"),
            ('<g id="a"><use href="#b"/></g><g id="b"><use href="#a"/></g>', "Cyclic"),
            ('<g id="a"><g id="b"><use href="#a"/></g></g>', "Cyclic"),
            ('<g clip-path="url(#absent)"/>', "Unresolved"),
        ]
        for body, expected in fixtures:
            with self.subTest(body=body):
                self.assertFails(self.check(svg(body+TEXT)), expected)

    def test_invalid_geometry_is_rejected(self):
        bodies = [
            '<path d="M NaN 0 L 1 1"/>', '<path d="M 0 0 L 1e999 1"/>',
            '<path d="M 0 0 L 1"/>', '<path d="M 0 0 A 2 2 0 4 0 5 5"/>',
            '<rect x="inf" width="10" height="4"/>', '<circle r="-2"/>',
            '<polygon points="0 0 1"/>', '<g transform="scale(NaN)"/>',
            '<g transform="matrix(1 0 0 1 0)"/>',
            '<path d="M 0,,0 L 1 1"/>',
            '<defs><linearGradient id="bad" gradientTransform="scale(NaN)"/></defs>',
            '<filter><feGaussianBlur stdDeviation="NaN"/></filter>',
        ]
        for body in bodies:
            with self.subTest(body=body):
                self.assertFails(self.check(svg(body+TEXT)), "Invalid")

    def test_wrong_or_unresolvable_physical_size_fails(self):
        self.assertFails(self.check(svg(TEXT), width_mm=180), "Physical width")
        self.assertFails(self.check(svg(TEXT, width="100%")), "physical SVG geometry")
        self.assertFails(self.check(svg(TEXT, viewbox="0 0 0 60")), "viewBox")
        self.assertFails(self.check(svg(TEXT, viewbox="0 0 NaN 60")), "viewBox")

    def test_unsupported_font_mechanisms_fail_honestly(self):
        fixtures = [
            '<style>g text {font-size:3px}</style>'+TEXT,
            '<text style="transform:scale(0.1)" font-size="3">Tiny</text>',
            '<style>svg {width:180mm}</style>'+TEXT,
            '<text font-size="1ex">Unknown</text>',
            '<text textLength="2" font-size="3">Condensed</text>',
            '<svg width="5" height="5" viewBox="0 0 100 100">'+TEXT+'</svg>',
            '<defs><text id="label">Label</text></defs><use href="#label"/>',
        ]
        for body in fixtures:
            with self.subTest(body=body):
                self.assertFalse(self.check(svg(body))["passed"])

    def test_safe_metadata_and_literal_ai_research_labels_are_not_removed(self):
        document = svg('<metadata><creator>Matplotlib</creator></metadata>'
                       '<text font-size="3">AI model accuracy</text>')
        report = self.check(document, expected_labels=["AI model accuracy"])
        self.assertPasses(report)
        self.assertEqual(self.path.read_text(), document)

    def test_bad_input_returns_structured_failure(self):
        self.assertFalse(audit_svg(Path(self.temp.name)/"missing.svg")["passed"])
        self.assertFails(self.check("<svg"), "Malformed XML")
        self.assertFails(self.check("<html/>"), "root")
        self.assertFails(self.check(svg(TEXT), min_font_pt=float("nan")), "min_font_pt")

    def test_labels_normalize_unicode_and_whitespace(self):
        report = self.check(svg('<text font-size="3">Cafe\u0301\n dose</text>'),
                            expected_labels=["Café dose"])
        self.assertPasses(report)

    def test_whitespace_between_tspans_is_preserved(self):
        report = self.check(svg('<text font-size="3"><tspan>Dose</tspan> '
                                '<tspan>response</tspan></text>'),
                            expected_labels=["Dose response"])
        self.assertPasses(report)


class MatplotlibIntegrationTests(_AuditFixture):
    """Exercise actual exporter behavior; no third-party dependency in ff_svg."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir())/"ff-mpl-tests"))
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            raise unittest.SkipTest("Matplotlib is unavailable; standard-library unit fixtures still run")
        cls.matplotlib, cls.plt = matplotlib, plt

    def export(self, *, outlined=False, raster=False):
        with self.matplotlib.rc_context({"svg.fonttype": "path" if outlined else "none"}):
            fig, ax = self.plt.subplots(figsize=(3.5, 2.5))
            if raster:
                ax.imshow([[0, 1], [2, 3]])
            else:
                ax.plot([0, 1, 2], [0, 2, 1], marker="o", label="Treatment")
                ax.legend()
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Response (a.u.)")
            buffer = io.StringIO()
            fig.savefig(buffer, format="svg")
            self.plt.close(fig)
            return buffer.getvalue()

    @staticmethod
    def standalone(document):
        # Only Matplotlib's known constant SVG 1.1 external declaration is
        # omitted. Arbitrary input DTDs are never repaired by the auditor.
        return document.replace('<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"\n'
                                '  "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n', "")

    def test_actual_matplotlib_live_text_and_markers_pass(self):
        report = self.check(self.standalone(self.export()),
                            width_mm=88.9, height_mm=63.5,
                            expected_labels=["Time (s)", "Response (a.u.)", "Treatment"])
        self.assertPasses(report)
        self.assertGreater(report["metrics"]["text_count"], 10)
        self.assertAlmostEqual(report["metrics"]["min_font_pt"], 10)

    def test_raw_matplotlib_doctype_is_explicitly_rejected(self):
        self.assertFails(self.check(self.export()), "DTD and entity")

    def test_actual_matplotlib_outlines_and_raster_fail(self):
        self.assertFails(self.check(self.standalone(self.export(outlined=True))),
                         "No visible native SVG text")
        self.assertFails(self.check(self.standalone(self.export(raster=True))), "Forbidden <image>")


if __name__ == "__main__":
    unittest.main()
