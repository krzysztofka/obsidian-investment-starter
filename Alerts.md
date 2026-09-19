# 🚨 Portfolio Alerts

```dataviewjs
let alertPages = dv.pages('"10_Finance/Assets" and #alert');

let totalAlertValue = 0;
let count = 0;

for (let p of alertPages) {
    totalAlertValue += (p.value_pln || 0);
    count += 1;
}

if (count === 0) {
    dv.paragraph("> [!SUCCESS] **All clear!** No active alerts across portfolio assets.");
} else {
    dv.paragraph(`> [!WARNING] **${count} asset(s)** currently flagged with alerts totaling **${totalAlertValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} PLN** in portfolio exposure.`);
}
```

## Active Alerts

```dataview
TABLE 
    name AS "Name",
    tags AS "Alerts",
    last_updated AS "Last Updated"
FROM "10_Finance/Assets" AND #alert
SORT value_pln DESC
```

## 📈 Overvalued Assets (`P/E > 40`)

```dataview
TABLE 
    name AS "Name",
    pe_ratio AS "P/E",
    current_price AS "Current Price",
    currency AS "Currency",
    value_pln AS "Value (PLN)"
FROM "10_Finance/Assets" AND #alert/overvalued
SORT pe_ratio DESC
```

## 📉 Insider Selling (`Net Insider Selling Detected`)

```dataview
TABLE 
    name AS "Name",
    yahoo_ticker AS "Ticker",
    analyst_rating AS "Analyst Rating",
    current_price AS "Current Price",
    currency AS "Currency",
    value_pln AS "Value (PLN)"
FROM "10_Finance/Assets" AND #alert/insider_sell
SORT value_pln DESC
```

## ⚠️ Delisting Risk (`AUM < 50M`)

```dataview
TABLE 
    name AS "Name",
    fund_size AS "Fund Size / AUM",
    current_price AS "Current Price",
    currency AS "Currency",
    value_pln AS "Value (PLN)"
FROM "10_Finance/Assets" AND #alert/delisting_risk
SORT value_pln DESC
```

## ⚖️ Allocation Drift (`Weight > Limit`)

```dataview
TABLE 
    name AS "Name",
    portfolio AS "Portfolio",
    asset_type AS "Type",
    current_price AS "Current Price",
    value_pln AS "Value (PLN)"
FROM "10_Finance/Assets" AND #alert/allocation_drift
SORT value_pln DESC
```

## 🛑 Stop Loss Breached (`Price <= Stop Loss`)

```dataview
TABLE 
    name AS "Name",
    current_price AS "Current Price",
    stop_loss AS "Stop Loss Level",
    currency AS "Currency",
    value_pln AS "Value (PLN)"
FROM "10_Finance/Assets" AND #alert/stop_loss
SORT value_pln DESC
```