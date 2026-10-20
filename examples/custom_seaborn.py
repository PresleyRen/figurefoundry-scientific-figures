#!/usr/bin/env python3
"""Build the four labelled Seaborn demonstrations using the bundled recipes."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "figurefoundry" / "scripts"))
from ff_seaborn import KINDS, build_recipe, export_recipe, synthetic_data, main

if __name__ == "__main__":
    main(["--synthetic-demo", *sys.argv[1:]])
