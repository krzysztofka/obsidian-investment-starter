# 🔬 ETF Underlying Holdings Overview

Deconstructed look-through exposures across all portfolio ETFs.

```dataview
TABLE
  holding_name AS "Company",
  round(sum_exposure_pln, 2) AS "Total Exposure (PLN)",
  sector AS "Sector",
  country AS "Country",
  round(avg_weight_pct, 2) AS "Avg Weight %",
  length(in_etfs) AS "ETFs Count"
FROM "10_Finance/ETF_Holdings"
WHERE file.name != "Holdings_Overview"
SORT sum_exposure_pln DESC
```
