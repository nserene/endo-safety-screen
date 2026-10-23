"""Download FAERS report counts from openFDA for the study population and every drug.

Population: female (patient.patientsex:2), age 12-35 years at onset
(patient.patientonsetage:[12 TO 35] AND patient.patientonsetageunit:801).

Downloads:
  1. total reports in the population
  2. side-effect counts for the whole population (top 1000 MedDRA terms)
  3. for each drug in data/clean/drug_list.csv, matched on
     patient.drug.openfda.generic_name: its total reports and side-effect counts

Each drug is searched by its RxNorm standard_name first. If that finds no
reports, the original drug_name is tried (e.g. RxNorm says "vitamin B12" but
FAERS labels say "cyanocobalamin"). The name used is saved as query_name.

Every API response is saved as JSON in data/raw/openfda/, so a rerun reads the
saved file instead of downloading again.

Outputs:
  data/clean/drug_totals.csv           one row per drug, plus a "population" row
  data/clean/drug_reaction_counts.csv  one row per drug and side effect, plus
                                       "population" rows for the whole population
"""

import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
CACHE = ROOT / "data" / "raw" / "openfda"
ENV_FILES = [ROOT / "fda.env", ROOT / ".env"]

ENDPOINT = "https://api.fda.gov/drug/event.json"
POPULATION = (
    "patient.patientsex:2"
    "+AND+patient.patientonsetage:[12+TO+35]"
    "+AND+patient.patientonsetageunit:801"
)
REACTION_FIELD = "patient.reaction.reactionmeddrapt.exact"
COUNT_LIMIT = 1000

# A search for "estradiol" also matches "ethinyl estradiol", a different drug,
# so those reports are excluded from the estradiol search.
EXCLUDE = {"estradiol": ["ethinyl estradiol"]}

MIN_REPORTS = 50  # drugs with fewer reports are labelled "not enough data"

MIN_INTERVAL = 0.26  # seconds between requests: about 230 per minute, under the 240 limit
MAX_TRIES = 5

_last_request = 0.0


def load_api_key():
    """Read OPENFDA_API_KEY from fda.env or .env in the project folder."""
    for path in ENV_FILES:
        if path.exists():
            for line in path.read_text().splitlines():
                name, _, value = line.partition("=")
                if name.strip() == "OPENFDA_API_KEY" and value.strip():
                    return value.strip().strip('"').strip("'")
    raise SystemExit("No OPENFDA_API_KEY found in fda.env or .env")


def cache_path(label, query):
    """File name for a saved response: a readable label plus a short hash of the query."""
    slug = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
    digest = hashlib.sha1(query.encode()).hexdigest()[:8]
    return CACHE / f"{slug}_{digest}.json"


def fetch(label, query, api_key):
    """Return the openFDA JSON for a query, from the saved file if there is one.

    A "No matches found" answer (HTTP 404) is saved too, as {"results": []}.
    """
    path = cache_path(label, query)
    if path.exists():
        return json.loads(path.read_text())

    global _last_request
    url = f"{ENDPOINT}?api_key={api_key}&{query}"
    for attempt in range(1, MAX_TRIES + 1):
        wait = MIN_INTERVAL - (time.monotonic() - _last_request)
        if wait > 0:
            time.sleep(wait)
        _last_request = time.monotonic()
        try:
            response = requests.get(url, timeout=60)
        except requests.RequestException as error:
            problem = f"network error ({type(error).__name__})"
        else:
            if response.status_code == 200:
                data = response.json()
                break
            if response.status_code == 404:
                data = {"results": []}
                break
            if response.status_code in (429, 500, 502, 503, 504):
                problem = f"HTTP {response.status_code}"
            else:
                # Any other error means the query itself is wrong: stop.
                response.raise_for_status()
        if attempt == MAX_TRIES:
            raise SystemExit(f"Giving up on {label} after {MAX_TRIES} tries: {problem}")
        print(f"  {label}: {problem}, retrying...")
        time.sleep(2 ** attempt)

    path.write_text(json.dumps(data))
    return data


def search_for(name=None):
    """The search part of a query: the population, optionally plus one drug."""
    search = POPULATION
    if name:
        search += f'+AND+patient.drug.openfda.generic_name:"{quote(name)}"'
        for other in EXCLUDE.get(name.lower(), []):
            search += f'+AND+NOT+patient.drug.openfda.generic_name:"{quote(other)}"'
    return f"search={search}"


def get_total(label, name, api_key):
    data = fetch(f"{label}_total", f"{search_for(name)}&limit=1", api_key)
    return data["meta"]["results"]["total"] if data.get("results") else 0


def get_reactions(label, name, api_key):
    query = f"{search_for(name)}&count={REACTION_FIELD}&limit={COUNT_LIMIT}"
    data = fetch(f"{label}_reactions", query, api_key)
    return [(row["term"], row["count"]) for row in data.get("results", [])]


def main():
    api_key = load_api_key()
    CACHE.mkdir(parents=True, exist_ok=True)
    drugs = pd.read_csv(CLEAN / "drug_list.csv", dtype={"rxcui": str})

    population_total = get_total("population", None, api_key)
    population_reactions = get_reactions("population", None, api_key)

    totals = [{
        "drug_name": "(population)", "group": "population", "rxcui": "",
        "standard_name": "", "query_name": "", "total_reports": population_total,
    }]
    reactions = [
        {"drug_name": "(population)", "group": "population", "reaction": term, "count": count}
        for term, count in population_reactions
    ]

    for i, drug in enumerate(drugs.itertuples(), start=1):
        query_name = drug.standard_name
        total = get_total(f"drug_{query_name}", query_name, api_key)
        if total == 0 and drug.drug_name.lower() != drug.standard_name.lower():
            query_name = drug.drug_name
            total = get_total(f"drug_{query_name}", query_name, api_key)

        drug_reactions = get_reactions(f"drug_{query_name}", query_name, api_key) if total else []

        totals.append({
            "drug_name": drug.drug_name, "group": drug.group, "rxcui": drug.rxcui,
            "standard_name": drug.standard_name, "query_name": query_name,
            "total_reports": total,
        })
        reactions += [
            {"drug_name": drug.drug_name, "group": drug.group, "reaction": term, "count": count}
            for term, count in drug_reactions
        ]
        if i % 25 == 0:
            print(f"  {i}/{len(drugs)} drugs done")

    totals = pd.DataFrame(totals)
    reactions = pd.DataFrame(reactions)
    is_drug = totals["group"] != "population"
    totals["data_status"] = ""
    totals.loc[is_drug, "data_status"] = totals.loc[is_drug, "total_reports"].map(
        lambda n: "enough data" if n >= MIN_REPORTS else "not enough data"
    )
    totals.to_csv(CLEAN / "drug_totals.csv", index=False)
    reactions.to_csv(CLEAN / "drug_reaction_counts.csv", index=False)

    drug_rows = totals[is_drug]
    not_enough = drug_rows[drug_rows["data_status"] == "not enough data"]
    not_enough = not_enough.sort_values(["group", "total_reports", "drug_name"], ascending=[False, False, True])
    not_enough[["drug_name", "group", "total_reports"]].to_csv(CLEAN / "not_enough_data.csv", index=False)
    fallback = drug_rows[drug_rows["query_name"] != drug_rows["standard_name"]]
    print()
    print(f"Total reports in population (female, age 12-35): {population_total:,}")
    print(f"Side effects counted for the population: {len(population_reactions):,}")
    print(f"Drugs searched: {len(drug_rows)}")
    print(f"Drugs with at least 1 report: {(drug_rows['total_reports'] > 0).sum()}")
    print(f"Drugs with 0 reports: {(drug_rows['total_reports'] == 0).sum()}")
    print(f"Drugs with enough data ({MIN_REPORTS}+ reports): {len(drug_rows) - len(not_enough)}")
    print(f"Drugs with not enough data (under {MIN_REPORTS} reports): {len(not_enough)}"
          " (listed in data/clean/not_enough_data.csv)")
    print(f"Drugs found by original name instead of standard name: {len(fallback)}")
    print(f"Drug-side effect rows saved: {(reactions['group'] != 'population').sum():,}")
    print("Reports per group (summed over drugs; one report can mention several drugs):")
    print(drug_rows.groupby("group")["total_reports"].sum().map("{:,}".format).to_string())


if __name__ == "__main__":
    main()
