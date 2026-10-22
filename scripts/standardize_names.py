"""Add an RxNorm ID (rxcui) and standard name to every drug in data/clean/drug_list.csv.

For each drug_name, ask RxNav for its RxNorm ID, then ask for the official
RxNorm name of that ID. Drugs with no match are written to
data/clean/unmatched.csv so they can be fixed or dropped by hand.
"""

import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
API = "https://rxnav.nlm.nih.gov/REST"
WAIT = 0.1  # seconds between requests


def get_json(url, params=None, tries=3):
    """GET a URL and return its JSON, retrying on network errors."""
    for attempt in range(tries):
        try:
            time.sleep(WAIT)
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt)


def lookup(name):
    """Return (rxcui, standard_name) for a drug name, or (None, None) if no match."""
    data = get_json(f"{API}/rxcui.json", params={"name": name})
    ids = data.get("idGroup", {}).get("rxnormId", [])
    if not ids:
        return None, None
    rxcui = ids[0]
    props = get_json(f"{API}/rxcui/{rxcui}/properties.json").get("properties") or {}
    return rxcui, props.get("name")


def main():
    drugs = pd.read_csv(CLEAN / "drug_list.csv")
    drugs = drugs.drop(columns=["rxcui", "standard_name"], errors="ignore")

    results = []
    for i, name in enumerate(drugs["drug_name"], start=1):
        results.append(lookup(name))
        if i % 25 == 0:
            print(f"  looked up {i}/{len(drugs)}")

    drugs["rxcui"] = [r[0] for r in results]
    drugs["standard_name"] = [r[1] for r in results]

    # Unmatched drugs are dropped from the main list (reasons in decisions.md).
    matched = drugs[drugs["rxcui"].notna()]
    unmatched = drugs[drugs["rxcui"].isna()][["drug_name", "group", "source"]]
    matched.to_csv(CLEAN / "drug_list.csv", index=False)
    unmatched.to_csv(CLEAN / "unmatched.csv", index=False)

    print(f"Matched: {len(matched)} of {len(drugs)}")
    print(f"Unmatched and dropped: {len(unmatched)} (saved to data/clean/unmatched.csv)")
    print("Rows per group:")
    print(matched["group"].value_counts().to_string())


if __name__ == "__main__":
    main()
