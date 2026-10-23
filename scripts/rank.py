"""Rank drugs by how few priority side-effect signals they have.

For each drug with enough data (50+ reports), count its signals on the
priority side effects listed in decisions.md:
  priority_signals     signal (a >= 3 and lower CI > 1), before correction
  priority_signals_bh  signal that is also significant after
                       Benjamini-Hochberg correction (p_bh < 0.05)

Drugs are sorted from fewest to most signals after correction, then before
correction, then by total reports (more reports first, since a clean result
backed by more reports is better supported). Drugs with not enough data are
listed separately at the bottom, without a rank.

Input:  data/clean/signals.csv, data/clean/drug_totals.csv
Output: data/clean/ranked_drugs.csv
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
ALPHA = 0.05


def main():
    signals = pd.read_csv(CLEAN / "signals.csv")
    totals = pd.read_csv(CLEAN / "drug_totals.csv")
    drugs = totals[totals["group"] != "population"][["drug_name", "group", "total_reports", "data_status"]]

    priority = signals[signals["priority"] & signals["signal"]].copy()
    priority["after_bh"] = priority["p_bh"] < ALPHA

    before = priority.groupby("drug_name").size()
    after = priority[priority["after_bh"]].groupby("drug_name").size()
    terms = (
        priority[priority["after_bh"]]
        .sort_values("ror", ascending=False)
        .groupby("drug_name")["reaction"]
        .agg("; ".join)
    )

    drugs["priority_signals"] = drugs["drug_name"].map(before).fillna(0).astype(int)
    drugs["priority_signals_bh"] = drugs["drug_name"].map(after).fillna(0).astype(int)
    drugs["signal_side_effects_bh"] = drugs["drug_name"].map(terms).fillna("")

    enough = drugs[drugs["data_status"] == "enough data"].sort_values(
        ["priority_signals_bh", "priority_signals", "total_reports"],
        ascending=[True, True, False],
    )
    enough.insert(0, "rank", range(1, len(enough) + 1))

    insufficient = drugs[drugs["data_status"] != "enough data"].sort_values(
        "total_reports", ascending=False
    )
    insufficient.insert(0, "rank", pd.NA)
    # Signals for these drugs are not trustworthy, so they are not reported.
    insufficient[["priority_signals", "priority_signals_bh"]] = pd.NA
    insufficient["signal_side_effects_bh"] = ""

    ranked = pd.concat([enough, insufficient], ignore_index=True)
    ranked = ranked.rename(columns={"data_status": "status"})
    ranked.to_csv(CLEAN / "ranked_drugs.csv", index=False)

    print(f"Ranked drugs (enough data): {len(enough)}")
    print(f"  candidates: {(enough['group'] == 'candidate').sum()}, standard: {(enough['group'] == 'standard').sum()}")
    print(f"  with 0 priority signals after correction: {(enough['priority_signals_bh'] == 0).sum()}")
    print(f"Listed separately (not enough data): {len(insufficient)}")
    print()
    print("Top 15:")
    cols = ["rank", "drug_name", "group", "total_reports", "priority_signals", "priority_signals_bh"]
    print(enough.head(15)[cols].to_string(index=False))
    print("Saved data/clean/ranked_drugs.csv")


if __name__ == "__main__":
    main()
