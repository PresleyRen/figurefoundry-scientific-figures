"""Meaningful integration checks for native diagrams and vector composition."""
import copy
import json
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "skills" / "figurefoundry" / "scripts"))
from ff_compose import compose_svgs
from ff_diagram import render_diagram

SVG = "{http://www.w3.org/2000/svg}"


def simple_spec():
    return {
        "width_mm": 120, "height_mm": 75, "title": "Experimental workflow",
        "nodes": [
            {"id": "input", "label": "Samples", "x": 5, "y": 30, "width": 30, "height": 20, "role": "input"},
            {"id": "analysis", "label": "Analysis", "x": 45, "y": 30, "width": 30, "height": 20, "shape": "ellipse"},
            {"id": "result", "label": "Results", "x": 85, "y": 30, "width": 30, "height": 20, "role": "output"},
        ],
        "edges": [
            {"source": "input", "target": "analysis"},
            {"source": "analysis", "target": "result"},
            {"source": "result", "target": "input", "kind": "feedback", "label": "review"},
        ],
    }


class DiagramTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)

    def test_explicit_nodes_and_feedback_remain_native_editable(self):
        out = self.folder / "workflow.svg"
        report = render_diagram(simple_spec(), out)
        root = ET.parse(out).getroot()
        self.assertEqual(report["node_count"], 3)
        self.assertEqual(report["edge_count"], 3)
        self.assertEqual(root.get("width"), "120mm")
        self.assertEqual(root.get("height"), "75mm")
        self.assertTrue(root.findall(f".//{SVG}text"))
        self.assertTrue(root.findall(f".//{SVG}tspan"))
        self.assertFalse(root.findall(f".//{SVG}image"))
        self.assertFalse(root.findall(f".//{SVG}foreignObject"))
        nodes = root.find(f"{SVG}g[@id='diagram-nodes']")
        self.assertEqual([node.get("data-node-id") for node in nodes], ["input", "analysis", "result"])
        feedback = root.find(f".//{SVG}g[@data-kind='feedback']")
        self.assertIsNotNone(feedback)
        self.assertEqual(feedback.find(f"{SVG}path").get("marker-end"), "url(#edge-arrow)")
        self.assertTrue(feedback.find(f"{SVG}path").get("stroke-dasharray"))
        self.assertTrue(all(label["font_pt"] == 8 for label in report["labels"]))

    def test_chinese_and_xml_sensitive_labels_round_trip(self):
        spec = simple_spec()
        spec["nodes"][0]["label"] = "样品 <A> & B\n实验数据"
        spec["title"] = "分析流程：误差与重复"
        out = self.folder / "chinese.svg"
        render_diagram(spec, out)
        root = ET.parse(out).getroot()
        texts = root.findall(f".//{SVG}text")
        self.assertIn("样品 <A> & B\n实验数据", [element.get("aria-label") for element in texts])
        visible = "".join("".join(element.itertext()) for element in texts)
        self.assertIn("实验数据", visible)
        self.assertIn("&amp;", out.read_text())
        self.assertIn("&lt;A&gt;", out.read_text())

    def test_label_wraps_without_path_outlining_or_truncation(self):
        spec = simple_spec()
        spec["nodes"][0]["label"] = "Repeated measurements"
        out = self.folder / "wrapped.svg"
        report = render_diagram(spec, out)
        self.assertGreater(len(report["labels"][0]["lines"]), 1)
        reconstructed = "".join(report["labels"][0]["lines"]).replace(" ", "")
        self.assertEqual(reconstructed, "Repeatedmeasurements")
        self.assertGreaterEqual(report["labels"][0]["font_pt"], 6)

    def test_wrapping_preserves_logical_chinese_and_long_token_text(self):
        from ff_svg import audit_svg
        for label in ["完整保留中文实验数据标签", "CounterintuitivelyLongToken"]:
            with self.subTest(label=label):
                spec = simple_spec()
                spec["nodes"][0]["label"] = label
                out = self.folder / "logical-text.svg"
                render_diagram(spec, out)
                audit = audit_svg(out, min_font_pt=6, expected_labels=[label])
                self.assertTrue(audit["passed"], audit["errors"])

    def test_all_supported_shapes_and_explicit_waypoints(self):
        shapes = ["rect", "roundrect", "ellipse", "diamond", "cylinder"]
        spec = {"width_mm": 200, "height_mm": 70, "nodes": [
            {"id": str(i), "label": "A", "x": 5 + i * 39, "y": 25, "width": 33, "height": 30, "shape": shape}
            for i, shape in enumerate(shapes)
        ], "edges": [{"source": "0", "target": "4", "kind": "feedback", "points": [[21, 10], [177, 10]]}]}
        out = self.folder / "shapes.svg"
        report = render_diagram(spec, out)
        self.assertEqual(report["node_count"], 5)
        self.assertEqual(len(ET.parse(out).findall(f".//{SVG}polygon")), 1)

    def test_invalid_requests_do_not_write_a_partial_svg(self):
        cases = []
        for key, value in [("x", float("nan")), ("width", -1), ("height", 0), ("y", 99)]:
            spec = simple_spec()
            spec["nodes"][0][key] = value
            cases.append(spec)
        duplicate = simple_spec()
        duplicate["nodes"][1]["id"] = "input"
        cases.append(duplicate)
        missing = simple_spec()
        missing["edges"][0]["target"] = "absent"
        cases.append(missing)
        long = simple_spec()
        long["nodes"][0]["label"] = "A" * 1000
        cases.append(long)
        controls = simple_spec()
        controls["nodes"][0]["label"] = "Invalid\x00label"
        cases.append(controls)
        for index, spec in enumerate(cases):
            with self.subTest(case=index):
                out = self.folder / f"invalid-{index}.svg"
                with self.assertRaises(ValueError):
                    render_diagram(spec, out)
                self.assertFalse(out.exists())

    def test_shipped_agent_example_renders_with_requested_font_size(self):
        spec = json.loads((PROJECT / "examples" / "diagram.json").read_text())
        report = render_diagram(spec, self.folder / "example.svg")
        self.assertEqual(report["warnings"], [])
        self.assertEqual(report["node_count"], 6)
        self.assertTrue(all(label["font_pt"] == 8 for label in report["labels"]))


class CompositionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)

    def source(self, name="source.svg", extra=""):
        path = self.folder / name
        path.write_text('''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" id="source" width="100mm" height="60mm" viewBox="0 0 100 60" aria-labelledby="title">
<title id="title">Source panel</title>
<defs>
 <linearGradient id="ink"><stop offset="0" stop-color="#445566"/><stop offset="1" stop-color="#778899"/></linearGradient>
 <clipPath id="clip"><rect x="0" y="0" width="100" height="60"/></clipPath>
 <circle id="dot" cx="10" cy="10" r="2"/>
 <style>#dot { fill: #336699; } .curve { stroke: url(#ink); fill: none; }</style>
</defs>
<g id="plot" clip-path="url(#clip)"><path class="curve" d="M 10 40 L 80 15"/><use xlink:href="#dot" x="5" y="5"/></g>
<text id="heading" x="10" y="53" font-family="sans-serif" font-size="2.82222222">Experimental data</text>
''' + extra + "</svg>")
        return path

    def panel(self, source, x=0, y=0, width=90, height=54, label=""):
        return {"path": str(source), "x_mm": x, "y_mm": y, "width_mm": width, "height_mm": height, "label": label}

    def test_two_panels_preserve_text_paths_refs_and_unique_ids(self):
        source = self.source()
        out = self.folder / "composed.svg"
        report = compose_svgs([self.panel(source, label="a", height=59), self.panel(source, x=90, label="b", height=59)], out, width_mm=180, height_mm=60, min_font_pt=6)
        root = ET.parse(out).getroot()
        ids = [element.get("id") for element in root.iter() if element.get("id")]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(root.findall(f".//{SVG}use")), 2)
        self.assertGreaterEqual(len(root.findall(f".//{SVG}path")), 2)
        self.assertEqual(len(root.findall(f".//{SVG}text")), 4)
        self.assertFalse(root.findall(f".//{SVG}image"))
        self.assertFalse(root.findall(f".//{SVG}foreignObject"))
        for element in root.iter():
            for key, value in element.attrib.items():
                if key.endswith("href"):
                    self.assertIn(value[1:], ids)
                for reference in re.findall(r"url\(#([^)]*)\)", value):
                    self.assertIn(reference, ids)
        self.assertIn("#panel-001-src-dot.panel-001-scope", out.read_text())
        self.assertIn("url(#panel-002-src-ink)", out.read_text())
        self.assertEqual([panel["uniform_scale"] for panel in report["panels"]], [0.9, 0.9])
        self.assertTrue(report["passed"], report["audit"])

    def test_nonuniform_requested_box_uses_uniform_scale_and_whitespace(self):
        out = self.folder / "letterbox.svg"
        report = compose_svgs([self.panel(self.source(), width=100, height=100)], out, width_mm=100, height_mm=100)
        panel = report["panels"][0]
        self.assertEqual(panel["uniform_scale"], 1)
        self.assertEqual(panel["content_bounds_mm"], {"x": 0, "y": 20, "width": 100, "height": 60})
        self.assertTrue(any("aspect ratio" in warning for warning in report["warnings"]))

    def test_final_physical_font_size_is_audited_when_available(self):
        try:
            from ff_svg import audit_svg
        except ImportError:
            self.skipTest("SVG audit module is not yet available")
        source = self.source(extra='<text x="20" y="30" font-size="1">Tiny</text>')
        report = compose_svgs([self.panel(source)], self.folder / "tiny.svg", width_mm=90, height_mm=54, min_font_pt=5)
        self.assertFalse(report["passed"])
        self.assertTrue(any("font" in message.lower() for message in report["audit"]["errors"]))

    def test_rejects_raster_foreignobject_external_urls_and_dtd(self):
        cases = [
            '<image href="data:image/png;base64,AAAA"/>',
            '<foreignObject width="10" height="10"><p xmlns="http://www.w3.org/1999/xhtml">Raster wrapper</p></foreignObject>',
            '<script>alert(1)</script>',
            '<path onclick="alert(1)" d="M0 0 L1 1"/>',
            '<use href="https://example.org/drawing.svg#id"/>',
            '<path fill="url(https://example.org/fill)" d="M0 0 L1 1"/>',
            '<path id="dot" d="M0 0 L1 1"/>',
            '<use href="#missing"/>',
        ]
        for index, extra in enumerate(cases):
            with self.subTest(case=index):
                source = self.source(f"bad-{index}.svg", extra)
                out = self.folder / f"rejected-{index}.svg"
                with self.assertRaises(ValueError):
                    compose_svgs([self.panel(source)], out, width_mm=90, height_mm=54)
                self.assertFalse(out.exists())
        source = self.source("dtd.svg")
        source.write_text('<!DOCTYPE svg SYSTEM "https://example.org/evil.dtd">' + source.read_text())
        with self.assertRaises(ValueError):
            compose_svgs([self.panel(source)], self.folder / "rejected-dtd.svg", width_mm=90, height_mm=54)

    def test_rejects_invalid_placement_and_source_overwrite(self):
        source = self.source()
        cases = [self.panel(source, x=-1), self.panel(source, width=0), self.panel(source, y=float("inf")), self.panel(source, x=100)]
        for index, panel in enumerate(cases):
            with self.subTest(case=index):
                with self.assertRaises(ValueError):
                    compose_svgs([panel], self.folder / f"bad-place-{index}.svg", width_mm=90, height_mm=54)
        with self.assertRaises(ValueError):
            compose_svgs([self.panel(source)], source, width_mm=90, height_mm=54)


if __name__ == "__main__":
    unittest.main()
