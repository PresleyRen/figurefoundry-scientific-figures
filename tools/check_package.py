#!/usr/bin/env python3
"""Validate package paths, Skill frontmatter, version alignment and local links."""
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "figurefoundry"


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
            "capabilities": len(ids), "skill_lines": len(source.splitlines())}


if __name__ == "__main__":
    result = check()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["passed"] else 1)
