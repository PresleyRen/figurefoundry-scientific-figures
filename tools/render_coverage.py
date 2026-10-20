#!/usr/bin/env python3
"""Render the human source-feature map from its machine-readable registry."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "figurefoundry"
MODES = {"native": "内置模块", "recipe": "可执行配方", "workflow": "Agent 工作流", "external-adapter": "既有项目后端"}


def link(path, *, skill=True):
    prefix = "../skills/figurefoundry/" if skill else "../"
    return f"[{Path(path).name}]({prefix}{path})"


def render():
    data = json.loads((SKILL / "assets" / "source-coverage.json").read_text())
    count = sum(len(s["features"]) for s in data["sources"])
    lines = ["# 来源特点、互补能力与扩展位置", "",
             f"版本 **{data['version']}**。逐项记录 **{len(data['sources'])} 个来源、{count} 个特点**。",
             "", "本表由 `assets/source-coverage.json` 生成。特点采用稳定 Sxx-Fxx 编号，能力采用 FF 编号。",
             "测试文件列指向相关行为的用例；具体执行次数与结果见 [TEST_REPORT.md](TEST_REPORT.md)。",
             "内置模块、可执行配方、Agent 工作流、既有项目后端分别说明使用方式；整合不以复制上游文件数量计数。",
             "", "```bash", "python skills/figurefoundry/scripts/figurefoundry.py coverage --source S08",
             "python skills/figurefoundry/scripts/figurefoundry.py coverage --query 主源", "```", ""]
    for source in data["sources"]:
        lines += [f"## {source['id']} · {source['name']}", "", f"[固定版本原始 Skill]({source['url']})", "",
                  "| 特点编号与作用 | 使用方式 / 能力 | 实现与说明 | 相关测试 | 互补来源 | 后续扩展入口与方法 |",
                  "|---|---|---|---|---|---|"]
        for f in source["features"]:
            target = f["extension"]["target"]
            detail = f"**{f['id']}** · {f['name']}" + ("；" + f["coverage_note"] if f.get("coverage_note") else "")
            fields = [detail, MODES[f["mode"]] + "；" + ", ".join(f["capabilities"]),
                      "；".join(link(p) for p in f.get("implementation", []) + f["references"]),
                      "；".join(link(p, skill=False) for p in f.get("tests", [])) or "按该条参考流程核验",
                      ", ".join(f.get("complements", [])), link(target) + "；" + f["extension"]["how"]]
            lines.append("| " + " | ".join(str(v).replace("|", "\\|").replace("\n", " ") for v in fields) + " |")
        if source.get("excluded_methods"):
            lines += ["", "方法取舍："]
            for method in source["excluded_methods"]:
                if isinstance(method, dict):
                    method = "；".join(f"{key}: {value}" for key, value in method.items())
                lines.append("- " + str(method))
        lines.append("")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    (ROOT / "docs" / "COVERAGE.md").write_text(render(), encoding="utf-8")
