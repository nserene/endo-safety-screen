"""Run every step of the analysis in order, then the check test.

Run from the project folder with: .venv/bin/python scripts/run_all.py

Needs an internet connection (RxNav and openFDA) and an openFDA API key in
fda.env or .env. Saved openFDA responses in data/raw/openfda/ are reused, so a
rerun on the same computer does not download them again.
"""

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

STEPS = [
    "scripts/make_drug_list.py",     # candidates + standard drugs -> drug_list.csv
    "scripts/standardize_names.py",  # RxNorm IDs and standard names
    "scripts/fetch_counts.py",       # FAERS counts from openFDA
    "scripts/compute_ror.py",        # reporting odds ratios -> signals.csv
    "scripts/rank.py",               # ranking -> ranked_drugs.csv
    "scripts/figures.py",            # three figures -> figures/
    "tests/test_counts.py",          # ibuprofen total matches the hand query
]


def main():
    start = time.monotonic()
    for i, step in enumerate(STEPS, start=1):
        print(f"\n=== Step {i}/{len(STEPS)}: {step} ===", flush=True)
        result = subprocess.run([sys.executable, str(ROOT / step)], cwd=ROOT)
        if result.returncode != 0:
            sys.exit(f"\nStopped: {step} failed (exit code {result.returncode}).")
    print(f"\nAll {len(STEPS)} steps finished in {time.monotonic() - start:.0f} seconds.")


if __name__ == "__main__":
    main()
