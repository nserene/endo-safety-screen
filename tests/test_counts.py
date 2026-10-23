"""Check the downloaded counts against a number found independently.

25,500 is the ibuprofen total from the hand query typed into a browser
(recorded in decisions.md). If the script and the hand query agree, the
script's search is built correctly.

Run with: .venv/bin/python tests/test_counts.py
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EXPECTED_IBUPROFEN_TOTAL = 25500


def test_ibuprofen_total():
    totals = pd.read_csv(ROOT / "data" / "clean" / "drug_totals.csv")
    ibuprofen = totals.loc[totals["drug_name"] == "ibuprofen", "total_reports"]
    assert len(ibuprofen) == 1, f"expected 1 ibuprofen row, found {len(ibuprofen)}"
    actual = int(ibuprofen.iloc[0])
    assert actual == EXPECTED_IBUPROFEN_TOTAL, (
        f"ibuprofen total is {actual:,}, expected {EXPECTED_IBUPROFEN_TOTAL:,}"
    )


if __name__ == "__main__":
    test_ibuprofen_total()
    print(f"PASS: ibuprofen total in drug_totals.csv equals {EXPECTED_IBUPROFEN_TOTAL:,}")
