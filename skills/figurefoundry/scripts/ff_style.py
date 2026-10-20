"""Versioned project defaults and named styles for a shared scientific figure set."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

THEMES = {
    "minimal": {"figure": {"font_family": "DejaVu Sans", "font_pt": 8, "grid": "y"},
                "panel_defaults": {}},
    "engineering": {"figure": {"font_family": "DejaVu Sans", "font_pt": 8, "grid": False,
                               "axis_font_pt": 8, "tick_font_pt": 7, "legend_font_pt": 7},
                    "panel_defaults": {"spines": "all", "linewidth": 1.2, "markersize": 3}},
    "classic": {"figure": {"font_family": "DejaVu Serif", "font_pt": 8, "grid": False},
                "panel_defaults": {"spines": "all", "linewidth": 1.1, "markersize": 3}},
    "warm": {"figure": {"font_family": "DejaVu Sans", "font_pt": 8, "grid": False},
             "panel_defaults": {"linewidth": 1.3, "markersize": 3.5}},
    "compact": {"figure": {"font_family": "DejaVu Sans", "font_pt": 8, "axis_font_pt": 8,
                           "tick_font_pt": 7, "legend_font_pt": 8, "panel_font_pt": 9,
                           "panel_label_position": "center", "grid": False},
                "panel_defaults": {"linewidth": 1.1, "markersize": 3}},
}


def _object(value, name):
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a JSON object")
    return value


def _read_json(path):
    def reject(value):
        raise ValueError(f"Non-finite JSON number {value} is not allowed")
    return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=reject)


def resolve_plot_style(spec, *, base_dir="."):
    """Merge theme < project defaults < figure specification without mutating input.

    defaults is an explicit local JSON path resolved relative to this spec.
    Panel-specific keys override panel_defaults; source/data selection never
    comes from a theme or a project-wide panel default.
    """
    _object(spec, "Plot specification")
    result = deepcopy(spec)
    defaults, source = {}, None
    if result.get("defaults") is not None:
        if not isinstance(result["defaults"], str) or not result["defaults"].strip():
            raise ValueError("defaults must be a nonempty project JSON path")
        path = (Path(base_dir) / result["defaults"]).resolve()
        defaults = _object(_read_json(path), "Project defaults")
        unknown = set(defaults) - {"version", "theme", "figure", "palette", "panel_defaults"}
        if unknown:
            raise ValueError("Unknown project defaults fields: " + ", ".join(sorted(unknown)))
        if defaults.get("version", 1) != 1:
            raise ValueError("Project defaults must use version 1")
        source = {"path": result["defaults"], "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    theme = result.get("theme", defaults.get("theme", "minimal"))
    if not isinstance(theme, str) or theme not in THEMES:
        raise ValueError("theme must be one of: " + ", ".join(THEMES))
    preset = deepcopy(THEMES[theme])
    figure = {**preset["figure"], **_object(defaults.get("figure", {}), "defaults.figure"),
              **_object(result.get("figure", {}), "figure")}
    panel_defaults = {**preset["panel_defaults"],
                      **_object(defaults.get("panel_defaults", {}), "defaults.panel_defaults"),
                      **_object(result.pop("panel_defaults", {}), "panel_defaults")}
    forbidden = {"data", "x", "y", "kind", "unit", "hue", "truth", "score", "value", "grid",
                 "estimator", "error", "within_unit", "fit", "y_columns"} & set(panel_defaults)
    if forbidden:
        raise ValueError("Project panel defaults are visual settings; define scientific fields per panel: " +
                         ", ".join(sorted(forbidden)))
    panels = result.get("panels", [])
    if not isinstance(panels, list) or any(not isinstance(p, dict) for p in panels):
        raise ValueError("panels must be an array of objects")
    palette = {**_object(defaults.get("palette", {}), "defaults.palette"),
               **_object(result.get("palette", {}), "palette")}
    result.update(figure=figure, panels=[{**deepcopy(panel_defaults), **p} for p in panels])
    if palette:
        result["palette"] = palette
    style_fields = {k: v for k, v in figure.items()
                    if k not in {"width_mm", "height_mm", "rows", "cols", "width_ratios", "height_ratios",
                                 "sharex", "sharey", "preview_dpi"}}
    identity = {"theme": theme, "figure": style_fields, "panel_defaults": panel_defaults,
                "palette": list(palette.items())}
    digest = hashlib.sha256(json.dumps(identity, ensure_ascii=False, sort_keys=True,
                                       allow_nan=False).encode("utf-8")).hexdigest()
    result["style_provenance"] = {"theme": theme, "defaults": source,
                                  "precedence": ["theme", "project defaults", "figure specification"],
                                  "style_sha256": digest, "resolved": identity}
    return result


def load_plot_spec(path):
    path = Path(path)
    return resolve_plot_style(_read_json(path), base_dir=path.resolve().parent)
