"""Data-driven native-vector scientific plotting, controlled by a JSON spec."""
from __future__ import annotations

import json
import math
import os
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "figurefoundry-mpl"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
from matplotlib.text import Text
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd
from scipy import stats

from ff_data import clean_json, complete_cases, numeric, read_table, require_columns, summarize
from ff_export import export_figure

PLOT_KINDS = ("line", "bar", "scatter", "box", "violin", "hist", "ecdf", "heatmap",
              "confusion", "roc", "pr", "forest", "pareto", "stacked_bar", "volcano", "correlation")
COLORS = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#555555")
MARKERS = ("o", "s", "^", "D", "v", "P", "X")
LINESTYLES = ("-", "--", "-.", ":")


def ordered(values, explicit=None):
    present = list(pd.unique(pd.Series(values).dropna()))
    if explicit is None:
        return present
    if len(explicit) != len(set(map(str, explicit))):
        raise ValueError("Category order contains duplicates.")
    missing = set(map(str, present)) - set(map(str, explicit))
    if missing:
        raise ValueError(f"Explicit order omits observed categories: {sorted(missing)}")
    return list(explicit)


def _category_equal(series, value):
    # JSON categorical labels must retain the same type as the table where possible.
    return series.astype(str) == str(value)


def _groups(df, hue, order=None):
    if not hue:
        return [(None, df)]
    return [(v, df.loc[_category_equal(df[hue], v)]) for v in ordered(df[hue], order)]


class Palette:
    def __init__(self, mapping=None):
        self.colors = {str(k): v for k, v in (mapping or {}).items()}
        for color in self.colors.values():
            to_rgba(color)  # Fail early on invalid color contracts.
        self.indices = {}

    def style(self, key):
        key = "data" if key is None else str(key)
        if key not in self.indices:
            self.indices[key] = len(self.indices)
        idx = self.indices[key]
        return dict(color=self.colors.get(key, COLORS[idx % len(COLORS)]),
                    marker=MARKERS[idx % len(MARKERS)], linestyle=LINESTYLES[idx % len(LINESTYLES)])


def _values(df, names):
    df = df.copy()
    for name in names:
        df[name] = numeric(df, name)
    return df


def _summary(df, panel, group_cols):
    return summarize(df, group_cols, panel["y"], unit=panel.get("unit"),
                     estimator=panel.get("estimator", "mean"), error=panel.get("error", "none"),
                     within_unit=panel.get("within_unit"), seed=panel.get("seed", 1729),
                     bootstrap_draws=panel.get("bootstrap_draws", 2000))


def _intervals(ax, x, center, lower, upper, *, color, horizontal=False):
    """Draw bounds directly: a bootstrap interval need not bracket the estimate."""
    valid = np.isfinite(lower) & np.isfinite(upper) & np.isfinite(center)
    if horizontal:
        ax.hlines(x[valid], lower[valid], upper[valid], color=color, linewidth=1)
    else:
        ax.vlines(x[valid], lower[valid], upper[valid], color=color, linewidth=1)
        for bound in (lower, upper):
            ax.plot(x[valid], bound[valid], linestyle="none", marker="_", color=color, markersize=4)


def _line_bar(ax, df, panel, palette, report):
    x, y, hue = panel["x"], panel["y"], panel.get("hue")
    kind = panel["kind"]
    require_columns(df, [x, y, hue])
    df = _values(df, [y])
    if df[[c for c in (x, hue) if c]].isna().any().any():
        raise ValueError("Line/bar group identifiers cannot be missing.")
    groups = [x] + ([hue] if hue and hue != x else [])
    aggregate = panel.get("estimator") is not None
    if kind == "bar" and not aggregate:
        raise ValueError("Bar panels require an explicit estimator (mean or median).")
    if panel.get("error", "none") != "none" and not aggregate:
        raise ValueError("Set an explicit estimator before requesting uncertainty.")
    if aggregate:
        data, report["statistics"] = _summary(df, panel, groups)
        report["warnings"].extend(report["statistics"]["warnings"])
    else:
        if df.duplicated(groups).any():
            raise ValueError("Repeated line coordinates require an explicit estimator and independent-unit semantics.")
        data = df.rename(columns={y: "estimate"}).copy()
        data["lower"] = data["upper"] = np.nan
        report["warnings"].append(f"Raw line: {int(data['estimate'].isna().sum())} missing y values remain gaps.")
    categories = ordered(df[x], panel.get("order"))
    categorical = kind == "bar" or panel.get("x_type") == "categorical" or not pd.api.types.is_numeric_dtype(df[x])
    if not categorical:
        categories = sorted(categories) if panel.get("order") is None else categories
        positions = np.asarray(categories, float)
    else:
        positions = np.arange(len(categories), dtype=float)
        ax.set_xticks(positions, [str(c) for c in categories])
    hue_groups = _groups(data, hue, panel.get("hue_order"))
    for j, (name, group) in enumerate(hue_groups):
        # iterrows can coerce integer keys to floats when a row contains NaN,
        # turning category "0" into "0.0" and silently losing line points.
        row_map = {str(row[x]): row for row in group.to_dict("records")}
        center = np.array([row_map.get(str(c), {}).get("estimate", np.nan) for c in categories], float)
        lower = np.array([row_map.get(str(c), {}).get("lower", np.nan) for c in categories], float)
        upper = np.array([row_map.get(str(c), {}).get("upper", np.nan) for c in categories], float)
        style = palette.style(name or panel.get("series", "data"))
        label = str(name) if name is not None else None
        if kind == "bar":
            width = 0.75 / len(hue_groups)
            xpos = positions + (j - (len(hue_groups) - 1) / 2) * width
            ax.bar(xpos, center, width=width * 0.9, color=style["color"], label=label,
                   edgecolor="white", linewidth=0.4,
                   hatch=("", "//", "..", "xx")[j % 4] if len(hue_groups) > 1 else None)
            _intervals(ax, xpos, center, lower, upper, color="#333333")
            ax.axhline(0, color="#555555", linewidth=0.6)
        else:
            ax.plot(positions, center, label=label, markersize=3.8, linewidth=1.3, **style)
            if panel.get("error", "none") != "none":
                ax.fill_between(positions, lower, upper, color=style["color"], alpha=0.13)
                _intervals(ax, positions, center, lower, upper, color=style["color"])
    if kind == "bar" and panel.get("ylim") and not (panel["ylim"][0] <= 0 <= panel["ylim"][1]):
        raise ValueError("Bar-chart numeric axis must include zero; choose points/forest for magnified intervals.")


def _scatter(ax, df, panel, palette, report):
    x, y, hue = panel["x"], panel["y"], panel.get("hue")
    df = complete_cases(_values(df, [x, y]), [x, y, hue], warnings=report["warnings"])
    for name, group in _groups(df, hue, panel.get("hue_order")):
        style = palette.style(name or panel.get("series", "data"))
        ax.scatter(group[x], group[y], s=panel.get("point_size", 17), alpha=0.8,
                   color=style["color"], marker=style["marker"],
                   edgecolors="white", linewidths=0.35, label=str(name) if name is not None else None,
                   rasterized=False)
        if panel.get("fit"):
            if panel["fit"] != "ols":
                raise ValueError("Only explicit fit='ols' is implemented; custom models need a source script.")
            if len(group) < 3 or group[x].nunique() < 2:
                raise ValueError("OLS needs >=3 complete observations and nonconstant x.")
            fit = stats.linregress(group[x], group[y])
            xx = np.array([group[x].min(), group[x].max()])
            ax.plot(xx, fit.intercept + fit.slope * xx, color=style["color"], linestyle="--", linewidth=1)
            report.setdefault("fits", []).append({"group": name, "model": "ordinary least squares",
                                                   "n": len(group), "slope": fit.slope,
                                                   "intercept": fit.intercept, "r": fit.rvalue})


def _distribution(ax, df, panel, palette, report):
    x, y, hue, kind = panel.get("x"), panel.get("y"), panel.get("hue"), panel["kind"]
    value = y if kind in {"box", "violin"} else x
    columns = [value, hue] + ([x] if kind in {"box", "violin"} else [])
    df = complete_cases(_values(df, [value]), columns, warnings=report["warnings"])
    if kind in {"hist", "ecdf"}:
        bins = np.histogram_bin_edges(df[value], bins=panel.get("bins", "auto")) if kind == "hist" else None
        if bins is not None:
            report["bins"] = bins.tolist()
        for name, group in _groups(df, hue, panel.get("hue_order")):
            style = palette.style(name or panel.get("series", "data"))
            vals = np.sort(group[value].to_numpy(float))
            if kind == "ecdf":
                unique, counts = np.unique(vals, return_counts=True)
                ax.step(unique, np.cumsum(counts) / len(vals), where="post", color=style["color"],
                        linestyle=style["linestyle"], label=str(name) if name is not None else None)
                ax.set_ylim(0, 1.02)
                report.setdefault("ecdf", []).append({"group": name, "n": len(vals)})
            else:
                ax.hist(vals, bins=bins, density=bool(panel.get("density", False)), histtype="step",
                        linewidth=1.4, color=style["color"], linestyle=style["linestyle"],
                        label=str(name) if name is not None else None)
        return
    if hue:
        raise ValueError("Native box/violin use x groups. For nested groups, use separate panels or a custom script.")
    cats = ordered(df[x], panel.get("order"))
    rng = np.random.default_rng(int(panel.get("seed", 1729)))
    for pos, cat in enumerate(cats):
        vals = df.loc[_category_equal(df[x], cat), y].to_numpy(float)
        color = palette.style(cat)["color"]
        if not len(vals):
            continue
        if kind == "box":
            box = ax.boxplot([vals], positions=[pos], widths=0.5, patch_artist=True,
                             showfliers=not panel.get("raw_points", True), manage_ticks=False,
                             medianprops={"color": "#222222", "linewidth": 1.1},
                             whiskerprops={"linewidth": 0.7}, capprops={"linewidth": 0.7})
            box["boxes"][0].set(facecolor=color, alpha=0.35, linewidth=0.8)
        elif len(vals) >= 2 and np.ptp(vals) > 0:
            violin = ax.violinplot([vals], positions=[pos], widths=0.7, showmedians=True,
                                   showextrema=False, bw_method=panel.get("bandwidth", "scott"))
            for body in violin["bodies"]:
                body.set(facecolor=color, edgecolor=color, alpha=0.3)
            violin["cmedians"].set(color="#333333", linewidth=1)
        else:
            ax.plot([pos - 0.15, pos + 0.15], [vals[0]] * 2, color=color)
            report["warnings"].append(f"Group {cat}: constant/singleton sample; violin density replaced by a value line.")
        if panel.get("raw_points", True):
            jitter = rng.uniform(-0.16, 0.16, len(vals))
            ax.scatter(pos + jitter, vals, s=9, color=color, alpha=0.65, edgecolors="none", rasterized=False)
        report.setdefault("sample_sizes", {})[str(cat)] = len(vals)
    ax.set_xticks(range(len(cats)), [str(c) for c in cats])


def _matrix(ax, df, panel, palette, report):
    kind = panel["kind"]
    if kind == "correlation":
        columns = panel.get("columns")
        if not columns or len(columns) < 2:
            raise ValueError("Correlation requires an explicit list of >=2 numeric columns.")
        df = _values(df, columns)
        df = complete_cases(df, columns, warnings=report["warnings"])
        if len(df) < 3 or any(df[c].nunique() < 2 for c in columns):
            raise ValueError("Correlation requires >=3 complete observations and nonconstant columns.")
        method = panel.get("method", "pearson")
        if method not in {"pearson", "spearman"}:
            raise ValueError("Correlation method must be pearson or spearman.")
        matrix = df[columns].corr(method=method).to_numpy()
        xlabels = ylabels = columns
        report.update(correlation_method=method, complete_case_n=len(df), missing_policy="listwise complete cases")
        vmin, vmax, cmap = -1, 1, panel.get("cmap", "RdBu_r")
    elif kind == "confusion":
        truth, pred = panel["truth"], panel["prediction"]
        df = complete_cases(df, [truth, pred], warnings=report["warnings"])
        labels = ordered(pd.concat([df[truth], df[pred]]), panel.get("labels"))
        index = {str(v): i for i, v in enumerate(labels)}
        matrix = np.zeros((len(labels), len(labels)), float)
        for actual, predicted in zip(df[truth], df[pred]):
            matrix[index[str(actual)], index[str(predicted)]] += 1
        report["counts"] = matrix.astype(int).tolist()
        normalize = panel.get("normalize", "none")
        if normalize not in {"none", "row"}:
            raise ValueError("Confusion normalize must be none or row.")
        if normalize == "row":
            sums = matrix.sum(axis=1, keepdims=True)
            matrix = np.divide(matrix, sums, out=np.full_like(matrix, np.nan), where=sums != 0)
        xlabels = ylabels = labels
        vmin, vmax, cmap = 0, (1 if normalize == "row" else None), panel.get("cmap", "Blues")
        report["normalization"] = normalize
    else:
        x, y, value = panel["x"], panel["y"], panel["value"]
        require_columns(df, [x, y, value])
        df = _values(df, [value])
        if df[[x, y]].isna().any().any():
            raise ValueError("Heatmap cell identifiers cannot be missing.")
        if df.duplicated([x, y]).any():
            if panel.get("aggregate") not in {"mean", "median"}:
                raise ValueError("Duplicate heatmap cells require explicit aggregate=mean or median.")
            df = df.groupby([x, y], sort=False, as_index=False, observed=True)[value].agg(panel["aggregate"])
            report["aggregation"] = panel["aggregate"]
        xlabels, ylabels = ordered(df[x], panel.get("x_order")), ordered(df[y], panel.get("y_order"))
        grid = df.pivot(index=y, columns=x, values=value)
        matrix = grid.reindex(index=ylabels, columns=xlabels).to_numpy(float)
        vmin, vmax, cmap = panel.get("vmin"), panel.get("vmax"), panel.get("cmap", "viridis")
    if matrix.size > 40000:
        raise ValueError("Native editable heatmap exceeds 40,000 cells; choose an explicit aggregation or custom source strategy.")
    mesh = ax.pcolormesh(np.ma.masked_invalid(matrix), cmap=cmap, vmin=vmin, vmax=vmax,
                         edgecolors="white" if matrix.size <= 400 else "none",
                         linewidth=0.5, rasterized=False, shading="flat")
    ax.set_xticks(np.arange(len(xlabels)) + 0.5, [str(v) for v in xlabels])
    ax.set_yticks(np.arange(len(ylabels)) + 0.5, [str(v) for v in ylabels])
    ax.invert_yaxis()
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    colorbar = ax.figure.colorbar(mesh, ax=ax, fraction=0.045, pad=0.035)
    colorbar.solids.set_rasterized(False)
    colorbar.solids.set_edgecolor("face")  # Prevent SVG viewer seams between vector colorbar cells.
    if panel.get("colorbar_label"):
        colorbar.set_label(panel["colorbar_label"])
    annotate = panel.get("annotate", matrix.size <= 64)
    if annotate:
        for (i, j), value in np.ndenumerate(matrix):
            if not np.isfinite(value):
                continue
            rgba = mesh.cmap(mesh.norm(value))
            luminance = sum(c * w for c, w in zip(rgba, (0.2126, 0.7152, 0.0722)))
            fmt = panel.get("number_format", ".2f" if kind != "confusion" or panel.get("normalize") == "row" else ".0f")
            ax.text(j + 0.5, i + 0.5, format(value, fmt), ha="center", va="center",
                    color="white" if luminance < 0.5 else "#222222", fontsize=panel.get("annotation_font_pt", 7))
    report["matrix"] = clean_json(matrix.tolist())
    missing_cells = int(np.isnan(matrix).sum())
    if missing_cells:
        report["warnings"].append(f"{missing_cells} missing matrix cells are blank; no imputation.")


def binary_curve(truth, scores, positive=1):
    """Threshold-exact binary ROC/PR points; ties are grouped, no smoothing."""
    scores = np.asarray(scores, float)
    truth = np.asarray(truth)
    if len(truth) != len(scores) or len(truth) == 0 or not np.isfinite(scores).all():
        raise ValueError("Binary curves need equal-length, finite, nonempty data.")
    labels = np.unique(truth)
    if len(labels) != 2 or not np.any(labels == positive):
        raise ValueError("Binary curves require exactly two observed classes and an explicit valid positive label.")
    positive_mask = truth == positive
    order = np.argsort(-scores, kind="stable")
    sorted_scores, hits = scores[order], positive_mask[order]
    ends = np.r_[np.flatnonzero(np.diff(sorted_scores)), len(scores) - 1]
    tp = np.cumsum(hits)[ends].astype(float)
    fp = (ends + 1 - tp).astype(float)
    tpr, fpr = np.r_[0, tp / hits.sum()], np.r_[0, fp / (~hits).sum()]
    recall, precision = tp / hits.sum(), tp / (tp + fp)
    auc = float(np.trapezoid(tpr, fpr))
    ap = float(np.sum(np.diff(np.r_[0, recall]) * precision))
    return {"fpr": fpr, "tpr": tpr, "recall": np.r_[0, recall],
            "precision": np.r_[1, precision], "auc": auc, "average_precision": ap,
            "positive_n": int(hits.sum()), "negative_n": int((~hits).sum())}


def _classification(ax, df, panel, palette, report):
    truth, score, hue = panel["truth"], panel["score"], panel.get("hue")
    df = complete_cases(_values(df, [score]), [truth, score, hue], warnings=report["warnings"])
    report["curves"] = []
    for name, group in _groups(df, hue, panel.get("hue_order")):
        curve = binary_curve(group[truth], group[score], panel.get("positive_label", 1))
        style = palette.style(name or "data")
        label = str(name) if name is not None else ("ROC" if panel["kind"] == "roc" else "Precision–recall")
        metric = "auc" if panel["kind"] == "roc" else "average_precision"
        if panel.get("show_metric", True):
            label += f" ({'AUC' if metric == 'auc' else 'AP'}={curve[metric]:.3f})"
        if panel["kind"] == "roc":
            ax.plot(curve["fpr"], curve["tpr"], label=label, color=style["color"], linestyle=style["linestyle"])
        else:
            ax.step(curve["recall"], curve["precision"], where="pre", label=label,
                    color=style["color"], linestyle=style["linestyle"])
        report["curves"].append({"group": name, "auc": curve["auc"], "average_precision": curve["average_precision"],
                                  "positive_n": curve["positive_n"], "negative_n": curve["negative_n"]})
    if panel["kind"] == "roc":
        ax.plot([0, 1], [0, 1], color="#888888", linestyle=":", linewidth=0.7)
    ax.set(xlim=(0, 1), ylim=(0, 1.02))


def _forest(ax, df, panel, palette, report):
    label, effect, lower, upper = panel["label"], panel["effect"], panel["lower"], panel["upper"]
    df = complete_cases(_values(df, [effect, lower, upper]), [label, effect, lower, upper], warnings=report["warnings"])
    if (df[lower] > df[upper]).any():
        raise ValueError("Forest lower interval bounds must not exceed upper bounds.")
    if df[label].duplicated().any():
        raise ValueError("Forest row labels must be unique.")
    pos = np.arange(len(df), dtype=float)
    _intervals(ax, pos, df[effect].to_numpy(), df[lower].to_numpy(), df[upper].to_numpy(), color=COLORS[0], horizontal=True)
    ax.scatter(df[effect], pos, marker="s", s=20, color=COLORS[0], zorder=3)
    ax.set_yticks(pos, df[label].astype(str))
    ax.invert_yaxis()
    if "reference" in panel:
        ax.axvline(float(panel["reference"]), color="#777777", linestyle=":", linewidth=0.8)
    report["intervals"] = {"source": "provided", "definition": panel.get("interval_definition", "unspecified"), "rows": len(df)}
    if not panel.get("interval_definition"):
        report["warnings"].append("Provided interval definition is unspecified; complete the caption before submission.")


def pareto_mask(x, y, *, minimize_x=True, minimize_y=False):
    values = np.column_stack((x, y)).astype(float)
    if not np.isfinite(values).all():
        raise ValueError("Pareto points must be finite.")
    costs = values * np.array([1 if minimize_x else -1, 1 if minimize_y else -1])
    return np.array([not np.any(np.all(costs <= row, axis=1) & np.any(costs < row, axis=1)) for row in costs])


def _pareto(ax, df, panel, palette, report):
    x, y = panel["x"], panel["y"]
    df = complete_cases(_values(df, [x, y]), [x, y, panel.get("label")], warnings=report["warnings"])
    front = pareto_mask(df[x], df[y], minimize_x=panel.get("minimize_x", True), minimize_y=panel.get("minimize_y", False))
    ax.scatter(df.loc[~front, x], df.loc[~front, y], color="#888888", marker="o", s=21, label="Dominated")
    ax.scatter(df.loc[front, x], df.loc[front, y], color=COLORS[0], marker="D", s=27, label="Pareto frontier")
    if panel.get("connect_frontier", False):
        boundary = df.loc[front].sort_values(x)
        ax.plot(boundary[x], boundary[y], color=COLORS[0], linewidth=0.8, linestyle="--")
        report["warnings"].append("Frontier connections are a visual guide, not unobserved operating points.")
    if panel.get("label"):
        for _, row in df.iterrows():
            ax.annotate(str(row[panel["label"]]), (row[x], row[y]), xytext=(3, 3), textcoords="offset points", fontsize=7)
    report["frontier_indices"] = df.index[front].tolist()


def _stacked(ax, df, panel, palette, report):
    x, category, value = panel["x"], panel["hue"], panel["y"]
    df = complete_cases(_values(df, [value]), [x, category, value], warnings=report["warnings"])
    if (df[value] < 0).any() or df.duplicated([x, category]).any():
        raise ValueError("Stacked bars require nonnegative values and one row per x/category; aggregate explicitly upstream.")
    cats, xs = ordered(df[category], panel.get("hue_order")), ordered(df[x], panel.get("order"))
    pivot = df.pivot(index=x, columns=category, values=value).reindex(index=xs, columns=cats)
    if pivot.isna().any().any():
        raise ValueError("Stacked components cannot be missing; supply explicit zero when it is scientifically correct.")
    matrix = pivot.to_numpy(float)
    if panel.get("normalize", False):
        totals = matrix.sum(axis=1)
        if (totals == 0).any():
            raise ValueError("Cannot normalize a zero-total stacked bar.")
        matrix = matrix / totals[:, None]
    bottom = np.zeros(len(xs))
    for j, cat in enumerate(cats):
        ax.bar(np.arange(len(xs)), matrix[:, j], bottom=bottom, color=palette.style(cat)["color"],
               label=str(cat), edgecolor="white", linewidth=0.4, hatch=("", "//", "..", "xx")[j % 4])
        bottom += matrix[:, j]
    ax.set_xticks(range(len(xs)), [str(v) for v in xs])
    if panel.get("ylim") and not (panel["ylim"][0] <= 0 <= panel["ylim"][1]):
        raise ValueError("Stacked bar axis must include zero.")
    report["normalization"] = "row fraction" if panel.get("normalize") else "none"


def _volcano(ax, df, panel, palette, report):
    effect, p = panel["x"], panel["p"]
    df = complete_cases(_values(df, [effect, p]), [effect, p], warnings=report["warnings"])
    if ((df[p] <= 0) | (df[p] > 1)).any():
        raise ValueError("Volcano p/q values must be in (0,1]; zero needs a documented upstream detection limit.")
    # No automatic significance gate or hypothesis test: plot supplied results.
    threshold = float(panel.get("p_threshold", 0.05))
    effect_threshold = float(panel.get("effect_threshold", 1))
    if not 0 < threshold <= 1 or effect_threshold < 0:
        raise ValueError("Invalid volcano thresholds.")
    sig = (df[p] < threshold) & (df[effect].abs() >= effect_threshold)
    for name, mask, color, marker in (("Below thresholds", ~sig, "#888888", "o"),
                                       ("Above thresholds", sig, COLORS[1], "^")):
        if mask.any():
            ax.scatter(df.loc[mask, effect], -np.log10(df.loc[mask, p]), color=color,
                       marker=marker, s=14, alpha=0.7, label=name, rasterized=False)
    ax.axhline(-math.log10(threshold), color="#777777", linestyle=":", linewidth=0.7)
    for boundary in (-effect_threshold, effect_threshold):
        ax.axvline(boundary, color="#777777", linestyle=":", linewidth=0.7)
    report.update(significant_points=int(sig.sum()), total_points=len(df), p_column=p,
                  p_definition=panel.get("p_definition", "unspecified"), p_threshold=threshold,
                  effect_threshold=effect_threshold)
    if not panel.get("p_definition"):
        report["warnings"].append("Specify whether the supplied values are raw p or multiplicity-adjusted q values.")


HANDLERS = {"line": _line_bar, "bar": _line_bar, "scatter": _scatter,
            **{k: _distribution for k in ("box", "violin", "hist", "ecdf")},
            **{k: _matrix for k in ("heatmap", "confusion", "correlation")},
            "roc": _classification, "pr": _classification, "forest": _forest,
            "pareto": _pareto, "stacked_bar": _stacked, "volcano": _volcano}


def visible_text_labels(fig):
    """Inventory displayed labels; locators also create out-of-view tick artists."""
    tick_ids, tick_labels = set(), []
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            lo, hi = sorted(axis.get_view_interval())
            eps = max(1, abs(lo), abs(hi)) * 1e-10
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                for label in (tick.label1, tick.label2):
                    tick_ids.add(id(label))
                    if ax.get_visible() and label.get_visible() and lo - eps <= tick.get_loc() <= hi + eps:
                        tick_labels.extend(label.get_text().splitlines())
    other_labels = [line for artist in fig.findobj(Text)
                    if id(artist) not in tick_ids and artist.get_visible()
                    and (artist.axes is None or artist.axes.get_visible())
                    for line in artist.get_text().splitlines()]
    return list(dict.fromkeys(line for line in other_labels + tick_labels if line.strip()))


def render_plots(spec, output, *, base_dir=".", overwrite=False):
    if not isinstance(spec, dict):
        raise ValueError("Figure spec must be a JSON object.")
    if spec.get("version", 1) != 1:
        raise ValueError("Unsupported figure spec version; expected 1.")
    panels = spec.get("panels", [])
    if not isinstance(panels, list) or not panels or len(panels) > 26 or any(not isinstance(p, dict) for p in panels):
        raise ValueError("A plot spec needs 1–26 panels.")
    settings = spec.get("figure", {})
    if not isinstance(settings, dict):
        raise ValueError("figure settings must be a JSON object.")
    width, height = float(settings.get("width_mm", 180)), float(settings.get("height_mm", 110))
    rows, cols = int(settings.get("rows", 1)), int(settings.get("cols", len(panels)))
    if rows < 1 or cols < 1 or rows * cols < len(panels):
        raise ValueError("Figure rows/cols cannot hold all panels.")
    font = float(settings.get("font_pt", 8))
    min_font = float(settings.get("min_font_pt", 6))
    if font < min_font or min_font <= 0:
        raise ValueError("Figure font_pt must be >= positive min_font_pt.")
    palette = Palette(spec.get("palette"))
    rc = {"font.family": settings.get("font_family", "DejaVu Sans"), "font.size": font,
          "axes.titlesize": font, "axes.labelsize": font, "xtick.labelsize": font,
          "ytick.labelsize": font, "legend.fontsize": max(min_font, font - 0.5),
          "axes.linewidth": 0.65, "xtick.major.width": 0.65, "ytick.major.width": 0.65,
          "text.usetex": False, "text.parse_math": False, "svg.fonttype": "none",
          "savefig.bbox": None, "axes.spines.top": False, "axes.spines.right": False}
    reports, expected_labels, source_data = [], [], {}
    with plt.rc_context(rc):
        fig, axes = plt.subplots(rows, cols, figsize=(width / 25.4, height / 25.4),
                                 layout="constrained", squeeze=False)
        try:
            for idx, panel in enumerate(panels):
                kind = panel.get("kind")
                if kind not in HANDLERS:
                    raise ValueError(f"Unsupported kind {kind!r}; use capabilities or a custom source script.")
                ax = axes.flat[idx]
                source = (Path(base_dir) / panel["data"]).resolve()
                cache_key = (str(source), str(panel.get("sheet", 0)))
                if cache_key not in source_data:
                    source_data[cache_key] = read_table(source, sheet=panel.get("sheet", 0))
                df, provenance = source_data[cache_key]
                report = {"id": panel.get("id", chr(97 + idx)), "kind": kind,
                          "source": provenance, "warnings": []}
                for axis in ("x", "y"):
                    if panel.get(axis + "scale") == "log":
                        column = panel.get(axis)
                        if column and column in df and (numeric(df, column).dropna() <= 0).any():
                            raise ValueError(f"Log {axis} axis would discard nonpositive {column} observations.")
                HANDLERS[kind](ax, df, panel, palette, report)
                for prop in ("xlabel", "ylabel", "title"):
                    text = panel.get(prop)
                    if text:
                        getattr(ax, "set_" + prop)(str(text))
                        expected_labels.append(str(text))
                for scale in ("xscale", "yscale"):
                    if panel.get(scale):
                        if panel[scale] not in {"linear", "log", "symlog"}:
                            raise ValueError(f"Unsupported {scale}")
                        if kind in {"bar", "stacked_bar"} and scale == "yscale" and panel[scale] == "log":
                            raise ValueError("Logarithmic bars have no zero baseline; use points or lines.")
                        getattr(ax, "set_" + scale)(panel[scale])
                        if panel[scale] == "log":
                            # Use literal numeric labels instead of mathtext glyph paths.
                            getattr(ax, scale[0] + "axis").set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
                for limits in ("xlim", "ylim"):
                    if panel.get(limits) is not None:
                        values = panel[limits]
                        if len(values) != 2 or not all(np.isfinite(values)) or values[0] >= values[1]:
                            raise ValueError(f"{limits} must contain two increasing finite values.")
                        if panel.get(limits[0] + "scale") == "log" and values[0] <= 0:
                            raise ValueError(f"Logarithmic {limits} must be strictly positive; Matplotlib would otherwise clamp them silently.")
                        getattr(ax, "set_" + limits)(values)
                        report[limits] = values
                        report["warnings"].append(f"Explicit {limits} applied; visually verify excluded observations are disclosed.")
                if panel.get("x_tick_rotation"):
                    ax.tick_params(axis="x", labelrotation=float(panel["x_tick_rotation"]))
                if panel.get("spines") == "all":
                    for spine in ax.spines.values():
                        spine.set_visible(True)
                if kind not in {"heatmap", "confusion", "correlation"}:
                    ax.set_axisbelow(True)
                    ax.grid(axis="y", color="#DDE2E7", linewidth=0.5, alpha=0.7)
                handles, labels = ax.get_legend_handles_labels()
                if handles and panel.get("legend", True):
                    ax.legend(frameon=False, loc=panel.get("legend_loc", "best"),
                              ncol=int(panel.get("legend_cols", 1)), handlelength=2)
                    expected_labels.extend(labels)
                if len(panels) > 1 or panel.get("show_panel_id", False):
                    ax.set_title(str(report["id"]), loc="left", fontweight="bold", fontsize=font + 1)
                reports.append(report)
            for ax in list(axes.flat)[len(panels):]:
                ax.set_visible(False)
            title = spec.get("title")
            if title:
                fig.suptitle(str(title), fontsize=font + 1, fontweight="bold")
                expected_labels.append(str(title))
            if spec.get("data_status") == "synthetic" and "synthetic" not in str(title).lower():
                raise ValueError("Synthetic demonstration data must be visibly labeled 'Synthetic' in the figure title.")
            fig.canvas.draw()
            # Keep this checked layout identical across the SVG/PDF/PNG writers.
            fig.set_layout_engine("none")
            expected_labels = visible_text_labels(fig)
            provenance = {"claim": spec.get("claim"), "data_status": spec.get("data_status", "user-supplied"),
                          "journal": spec.get("journal", {"status": "not specified"}),
                          "panels": reports, "spec": spec,
                          "transformations": "Only explicit plot aggregations/transforms recorded in this manifest."}
            result = export_figure(fig, output, width_mm=width, height_mm=height,
                                   min_font_pt=min_font, formats=spec.get("formats", ["svg", "pdf", "png"]),
                                   expected_labels=list(dict.fromkeys(expected_labels)), provenance=provenance,
                                   dpi=settings.get("preview_dpi", 300), overwrite=overwrite)
        finally:
            plt.close(fig)
    return result
