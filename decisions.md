# Decisions

- Candidates = all 299 unique drugs from any of the six signatures in Table S3 (Oskotsky et al. 2024), not only the 221 shared by all six, so no candidate is missed.
- Naproxen, mefenamic acid and letrozole were on both lists; I kept them only as standard because they are already used as treatments, leaving 296 candidates.
- Dropped 15 candidates that had no RxNorm match, because drugs not in RxNorm almost never appear in FAERS, leaving 281 candidates and 15 standard drugs (296 total):
  - Lab research compounds never sold as medicines: camptothecin, nocodazole, staurosporine, geldanamycin, puromycin, 8-azaguanine, alsterpaullone, bicuculline, ginkgolide A.
  - Not approved in the US (used elsewhere or only in animals): hexestrol, pentolonium, sulfaphenazole, epirizole, ribostamycin, apramycin.
