#!/usr/bin/env python3
"""Four executable Seaborn recipes with editable, exact-size SVG export.

Use --data to read an inspected experimental table, or --synthetic-demo for a labelled demonstration.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "figurefoundry-mpl"))
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from ff_export import export_figure
from ff_plots import visible_text_labels

KINDS = ("facet", "pair", "joint", "cluster")
PALETTE = {"Baseline": "#666A73", "Proposed": "#0072B2"}
RC = {"text.usetex": False, "text.parse_math": False, "svg.fonttype": "none",
      "font.family": "DejaVu Sans", "font.size": 8, "axes.labelsize": 8,
      "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
      "axes.spines.top": False, "axes.spines.right": False}


def weighted_summary(values, weights, *, weight_definition):
    """Explicit nonnegative-weight mean; uncertainty belongs to the analysis model."""
    values, weights = np.asarray(values, dtype=float), np.asarray(weights, dtype=float)
    if values.ndim != 1 or weights.shape != values.shape or not len(values):
        raise ValueError("Values and weights must be matching nonempty one-dimensional arrays")
    if not np.isfinite(values).all() or not np.isfinite(weights).all() or (weights < 0).any():
        raise ValueError("Measurements must be finite and weights finite and nonnegative")
    if not isinstance(weight_definition, str) or not weight_definition.strip():
        raise ValueError("State the scientific definition of the weights")
    total = float(weights.sum())
    if not np.isfinite(total) or total <= 0:
        raise ValueError("Total weight must be finite and positive")
    mean = float(np.dot(values, weights / total))
    if not np.isfinite(mean):
        raise ValueError("Weighted mean exceeded finite numeric range")
    return {"mean": mean, "weight_sum": total, "rows": len(values),
            "positive_weight_rows": int(np.count_nonzero(weights)),
            "weight_definition": weight_definition, "uncertainty": None}


def synthetic_data():
    rng = np.random.default_rng(2718)
    rows = []
    for condition in ("Early", "Late"):
        for method in PALETTE:
            for unit, dose in enumerate(np.linspace(0.5, 8, 12), 1):
                response = 0.75 * dose + 0.7 * (method == "Proposed") + 0.4 * (condition == "Late")
                rows.append({"unit": f"{condition}-{method}-{unit}", "condition": condition,
                             "method": method, "dose": dose,
                             "response": response + rng.normal(0, 0.18),
                             "signal": 2 + 0.3 * dose + rng.normal(0, 0.15)})
    return pd.DataFrame(rows)


def build_recipe(kind, frame, *, data_status="user-supplied"):
    """Return Figure, dimensions and declared analysis for one inspected table."""
    if kind not in KINDS:
        raise ValueError(f"Unknown Seaborn recipe: {kind}")
    required = {"dose", "response", "signal", "unit", "method", "condition"}
    if not required <= set(frame.columns):
        raise ValueError("Seaborn recipe input needs " + ", ".join(sorted(required)))
    if frame[list(required)].isna().any().any():
        raise ValueError("Resolve missing values explicitly before using this recipe")
    if not np.isfinite(frame[["dose", "response", "signal"]].to_numpy(dtype=float)).all():
        raise ValueError("Recipe measurements must be finite")
    if not set(frame["method"]) <= set(PALETTE):
        raise ValueError("Declare all method roles in PALETTE before plotting")
    metadata = {"recipe": kind, "rows": len(frame), "estimator": "none; individual observations",
                "seaborn": sns.__version__, "method_order": list(PALETTE)}
    bins = {column: np.histogram_bin_edges(frame[column].to_numpy(), bins="auto")
            for column in ("dose", "response", "signal")}
    with mpl.rc_context(RC):
        if kind == "facet":
            conditions = list(pd.unique(frame["condition"]))
            grid = sns.FacetGrid(frame, col="condition", col_order=conditions,
                                 hue="method", hue_order=list(PALETTE), palette=PALETTE,
                                 hue_kws={"marker": ["o", "s"]}, legend_out=False,
                                 height=2.4, aspect=1.15)
            grid.map_dataframe(sns.scatterplot, x="dose", y="response", s=15, linewidth=0.3)
            grid.set_axis_labels("Dose (a.u.)", "Response (a.u.)")
            grid.set_titles("{col_name}")
            grid.add_legend(title="Method", loc="upper left", frameon=False)
            fig, width, height = grid.figure, 180, 78
            fig.subplots_adjust(top=0.80, bottom=0.19, left=0.10, right=0.98, wspace=0.16)
        elif kind == "pair":
            grid = sns.PairGrid(frame, vars=["dose", "response", "signal"], hue="method",
                                hue_order=list(PALETTE), palette=PALETTE, height=1.6,
                                hue_kws={"marker": ["o", "s"]}, corner=True,
                                diag_sharey=False)
            grid.map_lower(plt.scatter, s=12, linewidth=0)
            # For each variable, every method consumes the same full-data bin edges.
            def histogram(values, color=None, label=None, **kwargs):
                plt.hist(values, bins=bins[values.name], density=True,
                         histtype="step", color=color, label=label, linewidth=1)
            grid.map_diag(histogram)
            for variable, ax in zip(("dose", "response", "signal"), grid.diag_axes):
                ax.set_gid(f"ff-pair-density-{variable}")
            grid.add_legend(title="Method", bbox_to_anchor=(0.97, 0.92), loc="upper right", frameon=False)
            fig, width, height = grid.figure, 160, 150
            fig.subplots_adjust(top=0.925, bottom=0.10, left=0.10, right=0.97, hspace=0.18, wspace=0.18)
            metadata["histogram_bins"] = {key: value.tolist() for key, value in bins.items()}
            # Probability density has inverse-variable units: autoscale each
            # variable separately, while both methods still share its y scale.
            metadata["histogram_density_scales"] = "independent per variable; shared between methods"
        elif kind == "joint":
            grid = sns.JointGrid(data=frame, x="dose", y="response", height=4, ratio=4, space=0.15)
            sns.scatterplot(data=frame, x="dose", y="response", hue="method", style="method",
                            hue_order=list(PALETTE), style_order=list(PALETTE), palette=PALETTE,
                            markers={"Baseline": "o", "Proposed": "s"}, s=18, ax=grid.ax_joint)
            sns.histplot(data=frame, x="dose", bins=bins["dose"], color="#666A73",
                         element="step", fill=False, stat="count", ax=grid.ax_marg_x)
            sns.histplot(data=frame, y="response", bins=bins["response"], color="#666A73",
                         element="step", fill=False, stat="count", ax=grid.ax_marg_y)
            grid.set_axis_labels("Dose (a.u.)", "Response (a.u.)")
            fig, width, height = grid.figure, 120, 120
            fig.subplots_adjust(top=0.86, bottom=0.13, left=0.14, right=0.97)
        else:
            matrix = frame.set_index("unit")[["dose", "response", "signal"]]
            if not matrix.index.is_unique or len(matrix) < 2:
                raise ValueError("Cluster recipe needs unique independent-unit IDs and at least two rows")
            if (matrix.std(ddof=1) == 0).any():
                raise ValueError("Column z-score requires nonconstant measured variables")
            width, height = 165, max(120, 35 + 3.5 * len(matrix))
            grid = sns.clustermap(matrix, z_score=1, method="average", metric="euclidean",
                                  cmap="coolwarm", center=0, vmin=-2, vmax=2,
                                  dendrogram_ratio=0.12, yticklabels=True,
                                  cbar_pos=(0.02, 1 - 28 / height, 0.028, 21 / height),
                                  cbar_kws={"label": "Column z-score", "ticks": [-2, 0, 2]},
                                  figsize=(width / 25.4, height / 25.4))
            # Reserve physical space for the header and labels before export.
            # The colorbar occupies the upper-left header, above the row tree
            # and left of the column tree, so neither tree is covered.
            heatmap_bottom, heatmap_height = 13 / height, (height - 44) / height
            grid.ax_heatmap.set_position((0.14, heatmap_bottom, 0.64, heatmap_height))
            grid.ax_row_dendrogram.set_position((0.02, heatmap_bottom, 0.116, heatmap_height))
            grid.ax_col_dendrogram.set_position((0.14, 1 - 30 / height, 0.64, 14 / height))
            grid.cax.set_position((0.02, 1 - 28 / height, 0.028, 21 / height))
            grid.cax.set_ylabel("Column z-score", labelpad=3)
            for ax, role in ((grid.ax_heatmap, "heatmap"),
                             (grid.ax_row_dendrogram, "row-dendrogram"),
                             (grid.ax_col_dendrogram, "column-dendrogram"),
                             (grid.cax, "colorbar")):
                ax.set_gid(f"ff-cluster-{role}")
            grid.ax_heatmap.set_xlabel("Measured variable")
            grid.ax_heatmap.set_ylabel("Independent unit")
            fig = grid.figure
            metadata.update(rows=len(matrix), transform="column z-score (Seaborn z_score=1)",
                            linkage="average", distance="euclidean",
                            row_order=[str(matrix.index[i]) for i in grid.dendrogram_row.reordered_ind])
        prefix = "Synthetic demonstration" if data_status == "synthetic" else "Experimental relationships"
        fig.suptitle(f"{prefix} · {kind}", y=0.98, fontsize=9, fontweight="bold")
        for artist in fig.findobj():
            if isinstance(artist, mpl.text.Text):
                artist.set_usetex(False)
                artist.set_parse_math(False)
                if artist.get_fontsize() < 7:
                    artist.set_fontsize(7)
            # Seaborn/Matplotlib may automatically rasterize a dense colorbar.
            # These recipes create only native collections; keep every one vector.
            if hasattr(artist, "set_rasterized") and artist.get_rasterized():
                artist.set_rasterized(False)
        return fig, width, height, metadata


def export_recipe(kind, frame, output, *, overwrite=False, formats=("svg", "png"),
                  data_status="user-supplied", source=None):
    fig, width, height, metadata = build_recipe(kind, frame, data_status=data_status)
    try:
        fig.set_size_inches(width / 25.4, height / 25.4)
        fig.canvas.draw()
        return export_figure(fig, output, width_mm=width, height_mm=height, min_font_pt=6,
                             formats=formats, expected_labels=visible_text_labels(fig),
                             provenance={"data_status": data_status, "source": source, "analysis": metadata},
                             overwrite=overwrite)
    finally:
        plt.close(fig)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    inputs = p.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--data", type=Path)
    inputs.add_argument("--synthetic-demo", action="store_true")
    p.add_argument("--kind", action="append", choices=KINDS)
    p.add_argument("--out", type=Path, default=Path("figures/seaborn"))
    p.add_argument("--overwrite", action="store_true")
    args = p.parse_args(argv)
    if args.synthetic_demo:
        frame, source, status = synthetic_data(), {"seed": 2718}, "synthetic"
    else:
        from ff_data import read_table
        frame, source = read_table(args.data)
        status = "user-supplied"
    for kind in args.kind or KINDS:
        result = export_recipe(kind, frame, args.out / kind, overwrite=args.overwrite,
                               data_status=status, source=source)
        print(f"{kind}: passed={result['svg_audit']['passed']}")


if __name__ == "__main__":
    main()
