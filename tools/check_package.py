#!/usr/bin/env python3
"""Validate package paths, Skill frontmatter, version alignment and local links."""
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "figurefoundry"


def check_indexes(registry, coverage, atlas):
    """Resolve source-feature and specialty navigation against concrete files."""
    errors = []
    capabilities = {entry["id"] for entry in registry["capabilities"]}
    source_ids = [entry["id"] for entry in coverage["sources"]]
    if len(source_ids) != len(set(source_ids)):
        errors.append("Duplicate source IDs in source coverage")
    documented = set(re.findall(r"^\| (S\d+) \|", (ROOT / "docs" / "SOURCES.md").read_text(), re.M))
    if set(source_ids) != documented:
        errors.append(f"Source coverage and SOURCES.md differ: {sorted(set(source_ids) ^ documented)}")
    if coverage.get("version") != registry["version"]:
        errors.append("Source coverage version differs from capability version")
    feature_ids = []

    def pointer(path, base, label):
        target = (base / path).resolve()
        if not target.is_relative_to(base.resolve()) or not target.is_file():
            errors.append(f"Unresolved {label}: {path}")
            return False
        return True

    for source in coverage["sources"]:
        if not re.fullmatch(r"https://github.com/[^/]+/[^/]+/blob/[0-9a-f]{40}/.+", source.get("url", "")):
            errors.append(f"Source {source['id']} must use its pinned Skill URL")
        if not source.get("features"):
            errors.append(f"Source {source['id']} has no feature-level coverage")
        for feature in source["features"]:
            ident = feature["id"]
            feature_ids.append(ident)
            if not re.fullmatch(re.escape(source["id"]) + r"-F\d{2,}", ident):
                errors.append(f"Feature ID does not belong to source: {ident}")
            if feature.get("mode") not in {"native", "workflow", "recipe", "external-adapter"}:
                errors.append(f"Unrecognized integration mode: {ident}")
            if not feature.get("capabilities") or set(feature["capabilities"]) - capabilities:
                errors.append(f"Unresolved capability mapping: {ident}")
            for field in ("implementation", "references", "tests"):
                if not feature.get(field):
                    errors.append(f"Missing {field} coverage target: {ident}")
            for field in ("implementation", "references"):
                for path in feature.get(field, []):
                    pointer(path, SKILL, f"{ident} {field}")
            for path in feature.get("tests", []):
                if pointer(path, ROOT, f"{ident} tests"):
                    tree = ast.parse((ROOT / path).read_text())
                    if not any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test_")
                               for n in ast.walk(tree)):
                        errors.append(f"Feature {ident} test target contains no tests: {path}")
            if set(feature.get("complements", [])) - set(source_ids):
                errors.append(f"Unknown complementary source: {ident}")
            extension = feature.get("extension", {})
            if not extension.get("target") or not extension.get("how"):
                errors.append(f"Missing extension target/action: {ident}")
            else:
                pointer(extension["target"], SKILL, f"{ident} extension")
    if len(feature_ids) != len(set(feature_ids)):
        errors.append("Duplicate feature IDs in source coverage")
    route_ids = [route["id"] for route in atlas["routes"]]
    if len(route_ids) != len(set(route_ids)):
        errors.append("Duplicate specialty route IDs")
    pointer(atlas["reference"], SKILL, "specialty atlas reference")
    for route in atlas["routes"]:
        if not route.get("keywords") or not route.get("data") or not route.get("integration"):
            errors.append(f"Specialty route needs keywords, data and integration: {route['id']}")
        if set(route.get("capabilities", [])) - capabilities:
            errors.append(f"Unresolved specialty capabilities: {route['id']}")
    return errors


def check():
    errors = []
    source = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", source, re.S)
    if not match:
        errors.append("Skill frontmatter is missing.")
    else:
        fields = dict(re.findall(r"^(\w+):\s*(.+)$", match.group(1), re.M))
        if set(fields) != {"name", "description"} or fields.get("name") != "figurefoundry":
            errors.append("Skill frontmatter must declare name=figurefoundry and description.")
        if len(fields.get("description", "")) < 80:
            errors.append("Skill description lacks trigger/context detail.")
    if len(source.splitlines()) > 500:
        errors.append("Main SKILL.md should remain below 500 lines; route details into references.")
    if re.search(r"\bTODO\b|\[INSERT|\[PLACEHOLDER", source):
        errors.append("Unfinished Skill boilerplate remains.")
    registry = json.loads((SKILL / "assets" / "capabilities.json").read_text())
    coverage = json.loads((SKILL / "assets" / "source-coverage.json").read_text())
    atlas = json.loads((SKILL / "assets" / "specialty-routes.json").read_text())
    errors.extend(check_indexes(registry, coverage, atlas))
    ids = [c["id"] for c in registry["capabilities"]]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate capability IDs.")
    for entry in registry["capabilities"]:
        for key in ("module", "reference", "tests"):
            if entry.get(key):
                target = (ROOT if key == "tests" else SKILL) / entry[key]
                if not target.is_file():
                    errors.append(f"Unresolved {entry['id']} {key}: {entry[key]}")
    for script in list((SKILL / "scripts").glob("*.py")) + list((ROOT / "tools").glob("*.py")):
        try:
            ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
        except SyntaxError as exc:
            errors.append(f"Invalid Python: {exc}")
    for name in ("figurefoundry.py", "ff_export.py"):
        text = (SKILL / "scripts" / name).read_text()
        if f'VERSION = "{registry["version"]}"' not in text:
            errors.append(f"Version drift in {name}")
    for file in ROOT.rglob("*.md"):
        if ".git" in file.parts or ".venv" in file.parts:
            continue
        text = re.sub(r"```.*?```", "", file.read_text(encoding="utf-8"), flags=re.S)
        for link in re.findall(r"\]\(([^)]+)\)", text):
            if re.match(r"[a-zA-Z]+://", link) or link.startswith("#"):
                continue
            path = link.split("#", 1)[0]
            if path and not (file.parent / path).exists():
                errors.append(f"Broken local link in {file.relative_to(ROOT)}: {path}")
    return {"passed": not errors, "errors": errors, "version": registry["version"],
            "capabilities": len(ids), "source_skills": len(coverage["sources"]),
            "source_features": sum(len(item["features"]) for item in coverage["sources"]),
            "specialty_routes": len(atlas["routes"]), "skill_lines": len(source.splitlines())}


if __name__ == "__main__":
    result = check()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["passed"] else 1)
