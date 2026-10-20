# Native diagram specification

```bash
python <skill-dir>/scripts/figurefoundry.py diagram --spec diagram.json --out diagram.svg
```

All coordinates and widths/heights are millimetres in the final page. Text size is
points. Layout is explicit; the tool never invents experimental or causal edges.
The skill may design coordinates from the supplied topology before rendering.

```json
{
  "width_mm": 130, "height_mm": 70,
  "title": "Sample preparation workflow",
  "font_pt": 8, "min_font_pt": 6,
  "nodes": [
    {"id": "sample", "label": "Sample", "x": 8, "y": 30, "width": 28, "height": 18, "role": "input"},
    {"id": "assay", "label": "Assay", "x": 50, "y": 30, "width": 28, "height": 18, "role": "process"},
    {"id": "readout", "label": "Readout", "x": 92, "y": 30, "width": 28, "height": 18, "role": "output"}
  ],
  "edges": [
    {"source": "sample", "target": "assay", "kind": "forward"},
    {"source": "assay", "target": "readout", "kind": "forward"}
  ]
}
```

## Field map

| Object | Fields and behavior |
|---|---|
| Page | `width_mm`, `height_mm`, optional `title`, `font_pt=8`, `min_font_pt=6` |
| Node | Unique nonempty `id`; `label` defaults to id; required `x`, `y`, `width`, `height` |
| Node geometry | `shape`: `roundrect` (default), `rect`, `ellipse`, `diamond`, `cylinder` |
| Semantic role | `role`: `input`, `process`, `evidence`, `output`, `control`, `neutral` |
| Node color | Optional `fill`: `#RGB`, `#RRGGBB` or a supported basic solid color |
| Edge | Valid node IDs in `source`, `target`; optional `label` |
| Edge kind | `forward`, `feedback`, `undirected`, `bidirectional` |
| Edge routing | Optional `points`: intermediate `[[x,y],...]`; anchors fit source/target boundaries |
| Group | Optional `groups` array: `id`, `label`, `x`, `y`, `width`, `height`, `fill` |

Forward edges are directed; feedback edges are dashed and labeled. Automatic
feedback routing needs an outer band; use explicit waypoints for complex layouts.
Bidirectional edges have arrowheads at both ends. Self-loops require an explicitly
positioned state node. Validate whether bidirectionality, feedback and grouping
actually match the experiment/system; visual convenience is not evidence.

Node labels wrap at Latin words/CJK characters and fit only as far as the declared
minimum. An impossible label fails rather than truncating or replacing scientific
terms. Logical text is preserved across tspans. Default font family includes common
Latin/CJK fallbacks; the rendering environment still needs suitable fonts. Reserve
space for title, group labels, arrows and edge labels before placing nodes.

The SVG includes named node/edge/group layers, native geometry, labels and local
arrow markers. It adds no platform logo or watermark. The CLI performs a final
text/geometry/font audit and returns the report as JSON. Automatic validation
cannot detect every overlap; render and inspect the final diagram.

To revise, edit JSON labels/coordinates/topology and rerun. Ordinary SVG editors
can edit its labels, shape geometry and colors. Keep JSON as the reproducible
master for scientific topology. See `svg-contract.md` for final composition and
editability validation.
