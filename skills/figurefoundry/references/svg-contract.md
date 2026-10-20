# SVG master, composition and audit contract

The final SVG must preserve editable geometry and text. A path is normal for a
curve or scientific shape; converting labels into hundreds of paths destroys text
editing. A `.svg` extension alone does not establish either kind of editability.

## Commands

```bash
python <skill-dir>/scripts/figurefoundry.py audit figure.svg --min-font-pt 6 \
  --width-mm 180 --height-mm 120 --labels expected-labels.json
python <skill-dir>/scripts/figurefoundry.py compose --spec composition.json --out composite.svg
```

`expected-labels.json` is a JSON array of all expected visible logical strings.
Matching normalizes Unicode NFC and whitespace and includes text in tspans; it
does not treat glyph paths as editable labels. Common hidden text and definitions
cannot satisfy visible label requirements. An incomplete label list cannot prove
that every letter remains editable.

`audit` returns JSON with `passed`, `errors`, `warnings` and `metrics`, exits 0 on
pass or 2 on failure, and never changes the input. Structural pass means only the
declared mechanical checks passed. Scientific validity and venue approval are
outside the program's scope.

## Structural checks

- Native SVG XML, finite geometry, physical dimensions, viewBox mapping, valid
  path arguments and affine transforms.
- No image elements (even SVG embedded through image), DTD/entities, scripts,
  event handlers, foreignObject, animation or external-resource references.
- Unique IDs, resolved local references and no cyclic reference expansion.
- Real visible text inventory, expected labels and effective physical font size.
- Simple styles/inheritance and affine transforms; conservative minimum singular
  scale for nonuniform transformations. Unsupported CSS, nested viewports,
  textPath/stretch or text instances through use fail explicitly.

Dimension tolerance is max(0.1 mm, 0.1%). Font availability, actual clipping,
overlap, full painted bounds, aesthetics and journal acceptance need separate
review. Paths cannot generally be classified as outlined letters from XML alone.

The exporter removes only Matplotlib's known generator-created SVG 1.1 external
DOCTYPE from its own newly generated string. It does not sanitize incoming XML,
strip attribution, remove metadata, or alter visible scientific labels. Input
files containing a DTD fail audit and should be re-exported from trusted source.

## Native composition

```json
{
  "width_mm": 190, "height_mm": 90,
  "panels": [
    {"path": "a.svg", "x_mm": 5, "y_mm": 0, "width_mm": 90, "height_mm": 85, "label": "a"},
    {"path": "b.svg", "x_mm": 100, "y_mm": 0, "width_mm": 85, "height_mm": 85, "label": "b"}
  ]
}
```

Paths resolve relative to the composition spec. Slot coordinates and size are mm.
A label reserves a 5 mm header. Native subtrees are copied under uniformly scaled
groups; aspect ratio is preserved. IDs, classes, local links, clip references and
ARIA references are renamed/scoped per panel. Simple source CSS is isolated;
complex selectors require an inline-style export. Sources remain unchanged.

Composition validates inputs before writing. Final font failure returns
`passed=false` and preserves the composite for inspection; do not deliver it as a
passing master. Enlarge the panel or regenerate its fonts at final size, then rerun
the audit. Repeated panels may not share IDs or bleed styles into one another.

## Visual and editability review

With Inkscape installed:

```bash
inkscape figure.svg --export-type=png --export-filename=figure-preview.png --export-dpi=180
```

Inspect the complete page, then the smallest labels and dense regions. Confirm
scientific arrows/topology, axis ranges/units, legends, sample sizes, negative
results, panel letters, missing data, colors and line/marker distinctions. A high
resolution preview does not excuse text that is too small at the final size.

Test editing in a disposable copy: change a known text node's string and a shape's
fill/stroke, render the copy, and verify both changes. Keep the original master and
hashes. Structural edit tests plus a real renderer demonstrate this tested path,
not universal compatibility with every SVG editor. If vector curves themselves
need scientific changes, edit the data/source and regenerate them.
