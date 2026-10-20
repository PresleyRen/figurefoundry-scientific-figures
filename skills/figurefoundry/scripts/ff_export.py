"""Exact-size, live-text SVG export and reproducibility manifest."""
from __future__ import annotations

import hashlib
import io
import json
import platform
from pathlib import Path

import matplotlib as mpl

from ff_data import clean_json
from ff_svg import audit_svg

VERSION = "1.0.0"
MPL_SVG_DTD = ('<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"\n'
               '  "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">')


def normalize_generated_svg(svg: str) -> str:
    """Only remove the known DOCTYPE in our own Matplotlib-generated output.

    This is not an input sanitizer. Incoming third-party XML must pass audit
    without calling this function. Creator metadata and scientific labels remain.
    """
    return svg.replace(MPL_SVG_DTD, "", 1)


def export_figure(fig, output, *, width_mm, height_mm, min_font_pt=6,
                  formats=("svg", "pdf", "png"), dpi=300,
                  expected_labels=None, provenance=None, overwrite=False):
    output = Path(output)
    if output.suffix.lower() in {".svg", ".pdf", ".png"}:
        output = output.with_suffix("")
    formats = list(dict.fromkeys(formats))
    if "svg" not in formats:
        raise ValueError("Editable SVG is the mandatory master format.")
    if any(f not in {"svg", "pdf", "png"} for f in formats):
        raise ValueError("Supported outputs: svg, pdf, png")
    if not (0 < float(width_mm) <= 2000 and 0 < float(height_mm) <= 2000):
        raise ValueError("Physical figure dimensions must be positive and <= 2000 mm.")
    targets = [output.with_suffix("." + f) for f in formats]
    manifest_path = output.with_suffix(".manifest.json")
    if not overwrite:
        existing = [str(p) for p in targets + [manifest_path] if p.exists()]
        if existing:
            raise FileExistsError("Refusing to overwrite: " + ", ".join(existing))
    fig.set_size_inches(float(width_mm) / 25.4, float(height_mm) / 25.4)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Applying these at export also protects a custom Matplotlib figure.
    # Text created with usetex=True cannot be retroactively converted to live text.
    for text in fig.findobj(mpl.text.Text):
        if text.get_usetex():
            raise ValueError("A text artist uses usetex=True; recreate it with live SVG text.")
    for artist in fig.findobj():
        if getattr(artist, "get_rasterized", lambda: False)():
            raise ValueError("A rasterized artist is incompatible with the editable SVG master.")
    rc = {"svg.fonttype": "none", "text.usetex": False,
          "svg.hashsalt": "figurefoundry-v1", "savefig.bbox": None,
          "pdf.fonttype": 42, "ps.fonttype": 42}
    generated = {}
    with mpl.rc_context(rc):
        for fmt in formats:
            buffer = io.BytesIO()
            metadata = {"Creator": f"FigureFoundry {VERSION}; Matplotlib {mpl.__version__}"}
            if fmt == "svg":
                metadata["Date"] = None
            elif fmt == "pdf":
                metadata.update(CreationDate=None, ModDate=None)
            else:
                metadata = {"Software": f"FigureFoundry {VERSION}; Matplotlib {mpl.__version__}"}
            fig.savefig(buffer, format=fmt, dpi=int(dpi), bbox_inches=None,
                        facecolor="white", metadata=metadata)
            data = buffer.getvalue()
            if fmt == "svg":
                data = normalize_generated_svg(data.decode("utf-8")).encode("utf-8")
            generated[fmt] = data
    # Validate a temporary local master before replacing any final output.
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".svg", dir=output.parent, delete=False) as f:
        staging = Path(f.name)
        f.write(generated["svg"])
    try:
        audit = audit_svg(staging, min_font_pt=float(min_font_pt),
                          width_mm=float(width_mm), height_mm=float(height_mm),
                          require_text=True, expected_labels=expected_labels)
        if not audit["passed"]:
            raise ValueError("SVG master failed audit: " + "; ".join(audit["errors"]))
    finally:
        staging.unlink(missing_ok=True)
    for fmt, data in generated.items():
        target = output.with_suffix("." + fmt)
        # Exclusive creation avoids an accidental overwrite, including a late race.
        with target.open("wb" if overwrite else "xb") as f:
            f.write(data)
    manifest = clean_json({
        "schema_version": 1, "generator": "FigureFoundry", "version": VERSION,
        "environment": {"python": platform.python_version(), "matplotlib": mpl.__version__},
        "master": output.with_suffix(".svg").name,
        "width_mm": float(width_mm), "height_mm": float(height_mm),
        "minimum_font_pt": float(min_font_pt), "text_mode": "live-svg-text",
        "raster_preview_dpi": int(dpi), "expected_labels": expected_labels or [],
        "files": {fmt: {"name": output.with_suffix("." + fmt).name,
                         "sha256": hashlib.sha256(data).hexdigest()}
                  for fmt, data in generated.items()},
        "svg_audit": audit, "provenance": provenance or {},
        "manual_review": {"status": "required",
                          "items": ["scientific meaning", "label collisions", "font availability",
                                    "grayscale readability", "current journal and submission stage"]},
        "journal_acceptance": "not-certified",
    })
    with manifest_path.open("w" if overwrite else "x", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")
    return manifest
