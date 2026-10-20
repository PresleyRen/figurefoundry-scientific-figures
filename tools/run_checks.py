#!/usr/bin/env python3
"""Run behavioral tests and optionally write machine-readable release evidence."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
import platform
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "figurefoundry-mpl"))


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed_ids = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.passed_ids.append(test.id())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    started = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2, resultclass=RecordedResult).run(suite)
    report = {
        "schema_version": 1, "checked_at": datetime.now(timezone.utc).isoformat(),
        "passed": result.wasSuccessful(), "test_methods_run": result.testsRun,
        "successes": result.passed_ids,
        "failures": [{"test": t.id(), "traceback": msg} for t, msg in result.failures],
        "errors": [{"test": t.id(), "traceback": msg} for t, msg in result.errors],
        "skipped": [{"test": t.id(), "reason": msg} for t, msg in result.skipped],
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "environment": {"python": platform.python_version(), "platform": platform.system(),
                        "packages": {name: importlib.metadata.version(name) for name in
                                     ("matplotlib", "numpy", "pandas", "scipy", "openpyxl")}},
        "scope": "Automated behavioral test methods. The 16 native charts, five themes, five normalizations and four Seaborn recipes use subtests; they are not additional method counts. Visual and independent-use evidence is recorded separately.",
    }
    try:
        report["environment"]["packages"]["seaborn"] = importlib.metadata.version("seaborn")
    except importlib.metadata.PackageNotFoundError:
        report["environment"]["packages"]["seaborn"] = "not installed"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "test_methods_run": result.testsRun,
                      "skipped": len(result.skipped), "elapsed_seconds": report["elapsed_seconds"]}))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
