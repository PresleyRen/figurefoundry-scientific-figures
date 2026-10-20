"""Explicit table loading, independent-unit summaries and provenance.

Original FigureFoundry implementation. No observations are invented, filtered
for significance, or silently coerced to missing values.
"""
from __future__ import annotations

import hashlib
import json
import csv
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def read_table(path, *, sheet=0):
    path = Path(path).resolve()
    suffix = path.suffix.lower()
    # pandas mangles duplicate header names before its DataFrame is returned.
    # Inspect source headers first so ambiguous field identity cannot be hidden.
    if suffix in {".csv", ".tsv", ".txt"}:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            header = next(csv.reader(stream, delimiter="," if suffix == ".csv" else "\t"), [])
        if len(header) != len(set(header)):
            raise ValueError("Source column names must be unique; duplicate header detected.")
    elif suffix in {".xlsx", ".xls"}:
        header_frame = pd.read_excel(path, sheet_name=sheet, header=None, nrows=1)
        if not header_frame.empty:
            header = header_frame.iloc[0].astype(str).tolist()
            if len(header) != len(set(header)):
                raise ValueError("Source column names must be unique; duplicate header detected.")
    if suffix == ".csv":
        frame = pd.read_csv(path)
    elif suffix in {".tsv", ".txt"}:
        frame = pd.read_csv(path, sep="\t")
    elif suffix in {".xlsx", ".xls"}:
        frame = pd.read_excel(path, sheet_name=sheet)
    elif suffix in {".json", ".jsonl", ".ndjson"}:
        if suffix == ".json":
            rows = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
                raise ValueError("JSON data must be an array of row objects.")
            frame = pd.DataFrame(rows)
        else:
            frame = pd.read_json(path, lines=True)
    else:
        raise ValueError(f"Unsupported data extension: {suffix}")
    if frame.empty:
        raise ValueError(f"No observations in {path.name}")
    frame.columns = frame.columns.map(str)
    if not frame.columns.is_unique:
        raise ValueError("Column names must be unique.")
    provenance = {
        "file": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "rows": len(frame),
        "columns": list(frame.columns),
        "missing_by_column": {str(k): int(v) for k, v in frame.isna().sum().items()},
    }
    if suffix in {".xlsx", ".xls"}:
        provenance["sheet"] = sheet
    return frame, provenance


def require_columns(frame, columns):
    missing = [c for c in columns if c is not None and c not in frame.columns]
    if missing:
        raise ValueError(f"Missing columns: {', '.join(map(str, missing))}")


def numeric(frame, column, *, allow_missing=True):
    require_columns(frame, [column])
    if column is None:
        raise ValueError("A numeric column name is required.")
    try:
        values = pd.to_numeric(frame[column], errors="raise").astype(float)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Column {column!r} contains non-numeric observations.") from exc
    if np.isinf(values.to_numpy()).any():
        raise ValueError(f"Column {column!r} contains infinite observations.")
    if not allow_missing and values.isna().any():
        raise ValueError(f"Column {column!r} contains missing observations.")
    return values


def complete_cases(frame, columns, *, warnings):
    """Omit only the rows a named plot cannot position; disclose the count."""
    require_columns(frame, columns)
    columns = list(dict.fromkeys(c for c in columns if c is not None))
    mask = frame[columns].notna().all(axis=1)
    n_missing = int((~mask).sum())
    if n_missing:
        warnings.append(f"Omitted {n_missing} rows missing required plot fields {columns}; source unchanged.")
    result = frame.loc[mask].copy()
    if result.empty:
        raise ValueError("No complete observations for the requested plot fields.")
    return result


def wide_to_long(frame, *, x, y_columns, value_name="value", series_name="series"):
    """Melt only explicitly selected curve fields, retaining every other ID field.

    Source values, missing values, row order within a series, and declared series
    order survive the conversion. No numeric-column inference is performed.
    """
    if not isinstance(y_columns, list) or not y_columns or any(not isinstance(c, str) or not c for c in y_columns):
        raise ValueError("y_columns must be a nonempty array of explicit column names.")
    if len(set(y_columns)) != len(y_columns):
        raise ValueError("y_columns contains duplicate column names.")
    if not isinstance(x, str) or not x or x in y_columns:
        raise ValueError("The x column must be named separately from y_columns.")
    if any(not isinstance(name, str) or not name for name in (value_name, series_name)) or value_name == series_name:
        raise ValueError("value_name and series_name must be distinct nonempty strings.")
    if value_name in frame.columns or series_name in frame.columns:
        raise ValueError("Wide-table output names already occur in the source; choose new value_name/series_name fields.")
    require_columns(frame, [x] + y_columns)
    working = frame.copy()
    for name in y_columns:
        working[name] = numeric(working, name)
    id_columns = [name for name in frame.columns if name not in y_columns]
    result = working.melt(id_vars=id_columns, value_vars=y_columns,
                          var_name=series_name, value_name=value_name)
    return result, {
        "operation": "wide-to-long", "x": x, "y_columns": list(y_columns),
        "value_name": value_name, "series_name": series_name,
        "id_columns": id_columns, "input_rows": len(frame), "output_rows": len(result),
        "missing_values_retained": int(result[value_name].isna().sum()),
        "row_order": "declared series order, then source row order within each series",
    }


def independent_unit_values(frame, group_columns, value_column, *, unit, within_unit=None):
    """Return one observed value per independent unit in each experimental group.

    This uses the same explicitly declared within-unit mean/median as summarize,
    so raw-point overlays show the units contributing to the bar statistics.
    """
    if not unit:
        raise ValueError("Raw-point overlays require an explicit independent unit column.")
    if within_unit not in {None, "mean", "median"}:
        raise ValueError("within_unit must be mean or median when supplied")
    keys = list(dict.fromkeys(list(group_columns) + [unit]))
    require_columns(frame, keys + [value_column])
    working = frame.copy()
    working[value_column] = numeric(working, value_column)
    if working[keys].isna().any().any():
        raise ValueError("Group and independent unit identifiers cannot be missing.")
    if working.duplicated(keys).any() and within_unit is None:
        raise ValueError("Repeated unit within group; specify within_unit explicitly to avoid pseudoreplication.")
    result = (working.groupby(keys, sort=False, observed=True)[value_column]
              .agg(within_unit or "first").reset_index())
    return result.dropna(subset=[value_column]).reset_index(drop=True)


def summarize(frame, group_columns, value_column, *, unit=None, estimator="mean",
              error="none", within_unit=None, seed=1729, bootstrap_draws=2000):
    """Summarize groups, treating the explicitly named unit as independent.

    CI95 is a two-sided Student-t interval for an arithmetic mean. Bootstrap95
    resamples independent unit summaries. Missing values are counted, not filled.
    A repeated unit within a group needs an explicit within-unit reduction.
    """
    if estimator not in {"mean", "median"}:
        raise ValueError("estimator must be mean or median")
    if error not in {"none", "sd", "sem", "ci95", "bootstrap95"}:
        raise ValueError("error must be none, sd, sem, ci95, or bootstrap95")
    if error != "none" and not unit:
        raise ValueError("Uncertainty requires an explicit independent unit column (e.g. seed or subject).")
    if estimator != "mean" and error in {"sem", "ci95"}:
        raise ValueError("SEM and Student-t CI95 are defined here for means; use bootstrap95 for medians.")
    if within_unit not in {None, "mean", "median"}:
        raise ValueError("within_unit must be mean or median when supplied")
    if int(bootstrap_draws) < 200:
        raise ValueError("bootstrap_draws must be at least 200")
    group_columns = list(group_columns)
    if not group_columns:
        raise ValueError("At least one grouping column is required.")
    require_columns(frame, group_columns + [value_column, unit])
    df = frame.copy()
    df[value_column] = numeric(df, value_column)
    if df[group_columns].isna().any().any():
        raise ValueError("Missing group identifiers cannot be silently assigned to a group.")
    if unit and df[unit].isna().any():
        raise ValueError("Independent unit identifiers cannot be missing.")
    messages, records = [], []
    rng = np.random.default_rng(int(seed))
    grouper = group_columns[0] if len(group_columns) == 1 else group_columns
    for key, group in df.groupby(grouper, sort=False, observed=True):
        keys = (key,) if len(group_columns) == 1 else key
        original = group[value_column]
        missing = int(original.isna().sum())
        if unit:
            if group.duplicated([unit]).any() and within_unit is None:
                raise ValueError(f"Repeated unit within group {keys}; specify within_unit explicitly to avoid pseudoreplication.")
            values = (group.groupby(unit, sort=False, observed=True)[value_column]
                      .agg(within_unit or "first").dropna().to_numpy(float))
        else:
            values = original.dropna().to_numpy(float)
        n = len(values)
        est = float(getattr(np, estimator)(values)) if n else float("nan")
        lo = hi = float("nan")
        if missing:
            messages.append(f"Group {keys}: {missing} missing observations; no imputation.")
        if error != "none" and n < 2:
            messages.append(f"Group {keys}: n={n}; uncertainty unavailable (not set to zero).")
        if error != "none" and n >= 2:
            sd = float(np.std(values, ddof=1))
            if error == "bootstrap95":
                # Chunking bounds memory for large unit counts.
                samples = []
                for start in range(0, int(bootstrap_draws), 100):
                    size = min(100, int(bootstrap_draws) - start)
                    draws = rng.choice(values, size=(size, n), replace=True)
                    samples.extend(getattr(np, estimator)(draws, axis=1))
                lo, hi = map(float, np.quantile(samples, [0.025, 0.975]))
            else:
                delta = sd if error == "sd" else sd / np.sqrt(n)
                if error == "ci95":
                    delta *= stats.t.ppf(0.975, n - 1)
                lo, hi = est - float(delta), est + float(delta)
        record = dict(zip(group_columns, keys))
        record.update(estimate=est, lower=lo, upper=hi, n=n,
                      observations=len(group), missing=missing)
        records.append(record)
    return pd.DataFrame(records), {
        "estimator": estimator, "uncertainty": error,
        "independent_unit": unit, "within_unit": within_unit,
        "confidence_level": 0.95 if error in {"ci95", "bootstrap95"} else None,
        "bootstrap_draws": int(bootstrap_draws) if error == "bootstrap95" else None,
        "random_seed": int(seed) if error == "bootstrap95" else None,
        "warnings": messages,
        "groups": clean_json(records),
    }


def clean_json(value):
    """JSON with null for missing values, never non-standard NaN/Infinity."""
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, np.bool_):
        return bool(value)
    return value
