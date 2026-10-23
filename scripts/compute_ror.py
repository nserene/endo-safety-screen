"""Compute a reporting odds ratio (ROR) for every drug and side effect.

For each drug and side effect, reports in the population fall into a 2x2 table:

                         has side effect    does not
    mentions the drug          a                b
    does not mention it        c                d

    a = reports with the drug and the side effect
    b = drug total - a
    c = population count of the side effect - a
    d = population total - a - b - c

ROR = (a/b) / (c/d). The 95% confidence interval is computed on the log scale:
    log(ROR) +/- 1.96 * sqrt(1/a + 1/b + 1/c + 1/d)

A signal is flagged when a >= 3 and the lower end of the interval is above 1.
The p-value tests whether ROR differs from 1, and the Benjamini-Hochberg
adjusted p-value (p_bh) corrects for testing thousands of pairs at once.

Input:  data/clean/drug_totals.csv, data/clean/drug_reaction_counts.csv, decisions.md
Output: data/clean/signals.csv
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from statsmodels.stats.multitest import multipletests

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"

Z = norm.ppf(0.975)  # 1.96, for a 95% confidence interval
MIN_A = 3


def load_priority_terms():
    """Read the priority side effects from decisions.md.

    They are the indented lines under the "Priority side effects" bullet, written
    as "  - TERM IN CAPITALS (count): reason".
    """
    lines = (ROOT / "decisions.md").read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("- Priority side effects"))
    terms = []
    for line in lines[start + 1:]:
        match = re.match(r"^\s+- ([A-Z][A-Z0-9' -]+?) \(", line)
        if not match:
            break
        terms.append(match.group(1))
    if not terms:
        raise SystemExit("No priority side effects found in decisions.md")
    return terms


def main():
    totals = pd.read_csv(CLEAN / "drug_totals.csv")
    counts = pd.read_csv(CLEAN / "drug_reaction_counts.csv")
    priority = load_priority_terms()

    population_total = int(totals.loc[totals["group"] == "population", "total_reports"].iloc[0])
    population_counts = (
        counts[counts["group"] == "population"].set_index("reaction")["count"]
    )

    drug_info = totals[totals["group"] != "population"].set_index("drug_name")
    pairs = counts[counts["group"] != "population"].rename(columns={"count": "a"})
    pairs["drug_total"] = pairs["drug_name"].map(drug_info["total_reports"])
    pairs["population_count"] = pairs["reaction"].map(population_counts)

    # The 2x2 table
    pairs["b"] = pairs["drug_total"] - pairs["a"]
    pairs["c"] = pairs["population_count"] - pairs["a"]
    pairs["d"] = population_total - pairs["a"] - pairs["b"] - pairs["c"]

    # ROR needs every cell above zero, and a population count for the side effect.
    # Side effects outside the population's top 1000 have no population count.
    cells = pairs[["a", "b", "c", "d"]]
    computable = cells.notna().all(axis=1) & (cells > 0).all(axis=1)
    a, b, c, d = (pairs.loc[computable, col].astype(float) for col in ["a", "b", "c", "d"])

    log_ror = np.log((a / b) / (c / d))
    se = np.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
    pairs.loc[computable, "ror"] = np.exp(log_ror)
    pairs.loc[computable, "ci_lower"] = np.exp(log_ror - Z * se)
    pairs.loc[computable, "ci_upper"] = np.exp(log_ror + Z * se)
    pairs.loc[computable, "p_value"] = 2 * norm.sf(np.abs(log_ror / se))

    pairs["signal"] = (pairs["a"] >= MIN_A) & (pairs["ci_lower"] > 1)
    pairs["priority"] = pairs["reaction"].isin(priority)
    pairs["insufficient_data"] = pairs["drug_name"].map(drug_info["data_status"]) == "not enough data"

    # Benjamini-Hochberg across every pair with a p-value, for drugs with enough data.
    # Drugs with too few reports are not ranked, so they are left out of the correction.
    tested = computable & ~pairs["insufficient_data"]
    pairs.loc[tested, "p_bh"] = multipletests(pairs.loc[tested, "p_value"], method="fdr_bh")[1]

    columns = [
        "drug_name", "group", "reaction", "a", "b", "c", "d",
        "ror", "ci_lower", "ci_upper", "p_value", "p_bh",
        "signal", "priority", "insufficient_data",
    ]
    for col in ["c", "d"]:
        pairs[col] = pairs[col].astype("Int64")
    signals = pairs[columns].sort_values(["drug_name", "reaction"])
    signals.to_csv(CLEAN / "signals.csv", index=False)

    enough = signals[~signals["insufficient_data"]]
    print(f"Priority side effects read from decisions.md: {len(priority)}")
    missing = sorted(set(priority) - set(population_counts.index))
    if missing:
        print(f"  WARNING: not in population counts, so no ROR: {', '.join(missing)}")
    print(f"Drug-side effect pairs: {len(signals):,}")
    print(f"  with an ROR: {computable.sum():,}")
    print(f"  no ROR, side effect outside the population's top 1000: {pairs['population_count'].isna().sum():,}")
    print(f"  no ROR, a zero cell in the 2x2 table: {(pairs['population_count'].notna() & ~computable).sum():,}")
    print(f"Pairs in the Benjamini-Hochberg correction (drugs with enough data): {tested.sum():,}")
    print(f"Signals (a >= {MIN_A}, lower CI > 1), drugs with enough data: {enough['signal'].sum():,}")
    print(f"  of which still significant after correction (p_bh < 0.05): "
          f"{(enough['signal'] & (enough['p_bh'] < 0.05)).sum():,}")
    print(f"Priority-side-effect signals, drugs with enough data: {(enough['signal'] & enough['priority']).sum()}")
    print("Saved data/clean/signals.csv")


if __name__ == "__main__":
    main()
