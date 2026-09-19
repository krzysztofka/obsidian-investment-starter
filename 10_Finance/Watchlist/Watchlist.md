---
type: watchlist
title: Main Watchlist
last_updated: "2026-08-30"
tags:
  - watchlist
---

# Investment Watchlist & Ideas

## Dynamic Watchlist Items

```dataview
TABLE 
    ticker AS "Ticker",
    target_entry_price + " " + currency AS "Target Entry",
    current_price + " " + currency AS "Price",
    upside_potential AS "Upside",
    sharpe_ratio AS "Sharpe (1Y)",
    volatility AS "Vol (1Y)",
    max_drawdown AS "Max DD",
    analyst_rating AS "Analyst Rating",
    industry AS "Industry",
    status AS "Status",
    platforms AS "Available Platforms"
FROM "10_Finance/Watchlist"
WHERE contains(tags, "watchlist") AND file.name != "Watchlist"
SORT status ASC, file.name ASC
```

## Potential Investment Ideas
- High-yield dividend opportunities in energy & financials
- Undervalued European industrials / value plays
- Defense & aerospace thematic ETFs

## Dataview: Open Decisions
```dataview
TABLE action AS "Action", platform AS "Platform", status AS "Status", date AS "Date"
FROM "20_Decisions"
WHERE type = "decision"
SORT date DESC
```
