"""Locate figure creation/export calls in Python and notebooks without execution."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

EXPORT_CALLS = {"savefig", "write_image", "export_figure", "render_plots", "render_diagram", "compose_svgs"}
CREATE_CALLS = {"subplots", "subplot_mosaic", "add_gridspec", "FacetGrid", "PairGrid", "JointGrid", "clustermap"}
STYLE_CALLS = {"set_xlabel", "set_ylabel", "set_title", "legend", "tick_params", "set_xlim", "set_ylim",
               "set_size_inches", "set_theme", "set_style", "rc_context"}


def _call_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _call_name(node.value)
        return (prefix + "." if prefix else "") + node.attr
    return ""


def _scan(code, *, cell=None):
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [], [{"cell": cell, "line": exc.lineno, "message": exc.msg}]
    entries = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node.func)
        tail = name.rsplit(".", 1)[-1]
        if tail not in EXPORT_CALLS | CREATE_CALLS | STYLE_CALLS:
            continue
        entry = {"call": name, "line": node.lineno, "cell": cell,
                 "category": "export" if tail in EXPORT_CALLS else "layout" if tail in CREATE_CALLS else "style",
                 "source": ast.get_source_segment(code, node)}
        if tail in EXPORT_CALLS:
            position = 1 if tail in {"export_figure", "render_plots", "render_diagram", "compose_svgs"} else 0
            output = node.args[position] if len(node.args) > position else next(
                (kw.value for kw in node.keywords if kw.arg in {"fname", "file", "output", "out"}), None)
            entry["output_expression"] = ast.get_source_segment(code, output) if output is not None else None
            entry["literal_output"] = output.value if isinstance(output, ast.Constant) and isinstance(output.value, str) else None
        entries.append(entry)
    return sorted(entries, key=lambda e: e["line"]), []


def inventory_sources(paths):
    """Inventory explicitly supplied .py/.ipynb files or a project directory."""
    if not isinstance(paths, (list, tuple)) or not paths:
        raise ValueError("Supply at least one Python file, notebook or project directory")
    selected = []
    excluded = {".git", ".venv", "venv", "__pycache__", "node_modules"}
    for item in paths:
        path = Path(item)
        if path.is_dir():
            selected.extend(p for p in path.rglob("*")
                            if p.is_file() and p.suffix in {".py", ".ipynb"}
                            and not (set(p.relative_to(path).parts) & excluded))
        elif path.is_file() and path.suffix in {".py", ".ipynb"}:
            selected.append(path)
        else:
            raise ValueError(f"Inventory expects existing .py/.ipynb sources or a directory: {path}")
    files = []
    for path in sorted(set(p.resolve() for p in selected)):
        content = path.read_bytes()
        text = content.decode("utf-8")
        entries, errors = [], []
        if path.suffix == ".py":
            entries, errors = _scan(text)
        else:
            notebook = json.loads(text)
            if not isinstance(notebook, dict) or not isinstance(notebook.get("cells"), list):
                raise ValueError(f"Notebook needs a cells array: {path}")
            for i, cell in enumerate(notebook["cells"]):
                if not isinstance(cell, dict):
                    raise ValueError(f"Notebook cell {i} must be an object")
                if cell.get("cell_type") != "code":
                    continue
                source = cell.get("source", "")
                if isinstance(source, list) and all(isinstance(s, str) for s in source):
                    source = "".join(source)
                if not isinstance(source, str):
                    raise ValueError(f"Notebook code cell {i} needs textual source")
                found, parse_errors = _scan(source, cell=i)
                entries.extend(found)
                errors.extend(parse_errors)
        files.append({"path": str(path), "sha256": hashlib.sha256(content).hexdigest(),
                      "entries": entries, "parse_errors": errors})
    return {"schema_version": 1, "passed": not any(f["parse_errors"] for f in files),
            "files": files, "file_count": len(files),
            "export_calls": sum(e["category"] == "export" for f in files for e in f["entries"]),
            "method": "Python AST inventory; input code is never executed; notebook cells are zero-based"}
