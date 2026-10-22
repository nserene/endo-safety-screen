"""Build data/clean/drug_list.csv from the candidate spreadsheets plus the standard treatments.

Candidates come from Supplementary Table S3 (data/raw/mmc3.xlsx) of
Oskotsky et al. 2024, iScience. The sheet "drug_instances_six_signatures" is the
union of candidates across all six endometriosis signatures (unstratified, stage
I-II, stage III-IV, PE, ESE, MSE). Table S4 (mmc4.xlsx) only describes a subset
of the same drugs, so it adds no new names.
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"

CANDIDATE_SOURCE = "Oskotsky et al. 2024, iScience (Table S3)"
STANDARD_SOURCE = "standard endometriosis treatment"

STANDARD_DRUGS = [
    "ibuprofen", "naproxen", "mefenamic acid", "celecoxib",
    "norethindrone acetate", "medroxyprogesterone acetate", "dienogest",
    "ethinyl estradiol", "leuprolide", "nafarelin", "elagolix", "relugolix",
    "letrozole", "anastrozole", "danazol",
]


def main():
    sheet = pd.read_excel(RAW / "mmc3.xlsx", sheet_name="drug_instances_six_signatures")
    names = sheet["name"].str.strip().str.lower().drop_duplicates()

    # Drugs that are both candidates and standard treatments stay only in the
    # standard group, since they are already used to treat endometriosis.
    in_both = sorted(set(names) & set(STANDARD_DRUGS))
    names = names[~names.isin(STANDARD_DRUGS)]

    candidates = pd.DataFrame({"drug_name": names, "group": "candidate", "source": CANDIDATE_SOURCE})
    standard = pd.DataFrame({"drug_name": STANDARD_DRUGS, "group": "standard", "source": STANDARD_SOURCE})

    drug_list = pd.concat([candidates, standard], ignore_index=True)
    assert drug_list["drug_name"].is_unique
    CLEAN.mkdir(parents=True, exist_ok=True)
    drug_list.to_csv(CLEAN / "drug_list.csv", index=False)

    print("Rows per group:")
    print(drug_list["group"].value_counts().to_string())
    print(f"Total rows: {len(drug_list)}")

    print(f"Moved from candidate to standard only ({len(in_both)}): {', '.join(in_both)}")


if __name__ == "__main__":
    main()
