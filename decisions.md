# Decisions

- Candidates = all 299 unique drugs from any of the six signatures in Table S3 (Oskotsky et al. 2024), not only the 221 shared by all six, so no candidate is missed.
- Naproxen, mefenamic acid and letrozole were on both lists; I kept them only as standard because they are already used as treatments, leaving 296 candidates.
- Dropped 15 candidates that had no RxNorm match, because drugs not in RxNorm almost never appear in FAERS, leaving 281 candidates and 15 standard drugs (296 total):
  - Lab research compounds never sold as medicines: camptothecin, nocodazole, staurosporine, geldanamycin, puromycin, 8-azaguanine, alsterpaullone, bicuculline, ginkgolide A.
  - Not approved in the US (used elsewhere or only in animals): hexestrol, pentolonium, sulfaphenazole, epirizole, ribostamycin, apramycin.
  - Meta --> results --> total: 25500
  - Ibuprofen side-effect counts (&count=patient.reaction.reactionmeddrapt.exact): top side effect is PAIN with 2,477 reports, then NAUSEA 2,046 and VOMITING 1,790.
  - Population: female patients, age 12–35 at onset, all report years. Reason: endometriosis symptoms usually begin in adolescence, and long-term treatment safety matters most for young patients.
- Drugs are matched on openFDA's patient.drug.openfda.generic_name, as planned, because it is consistent and matches the hand query (ibuprofen = 25,500 reports); this field only covers drugs with a current US label, so 98 drugs (mostly sold outside the US) get zero reports and count as insufficient data, which is a stated limitation.
- The estradiol search excludes reports with ethinyl estradiol, because searching "estradiol" also matches "ethinyl estradiol" (a different drug in most birth-control pills) and inflated estradiol from 2,266 to 40,576 reports.
- Headline number: 1,124,641 FAERS reports for female patients aged 12–35 (from scripts/fetch_counts.py, saved in data/clean/drug_totals.csv).
- Drugs with under 50 reports are labelled "not enough data", because with so few reports a side-effect signal can appear or vanish by chance; this applies to 142 candidates (98 with zero reports, 44 with 1–49) and no standard drugs, leaving 154 drugs with enough data (full list in data/clean/not_enough_data.csv).
