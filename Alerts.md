# 🚨 Portfolio Alerts

```dataviewjs
// 1. Load config.yaml for localization
let configContent = null;
try {
    if (app && app.vault && app.vault.adapter) {
        configContent = await app.vault.adapter.read("config.yaml");
    }
} catch (e) {}

let parsedConfig = null;
if (configContent) {
    try {
        let parseYamlFn = window.parseYaml;
        if (!parseYamlFn) {
            try { parseYamlFn = require("obsidian").parseYaml; } catch(err) {}
        }
        if (parseYamlFn) parsedConfig = parseYamlFn(configContent);
    } catch (e) {}
}

let baseCurrency = parsedConfig?.localization?.base_currency || "PLN";
let currencySymbol = parsedConfig?.localization?.currency_symbol || "zł";
let symbolPosition = parsedConfig?.localization?.symbol_position || "suffix";

function formatCurrency(amount) {
    let formatted = (amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (symbolPosition === "prefix") {
        return `${currencySymbol}${formatted}`;
    }
    return `${formatted} ${currencySymbol}`;
}

let alertPages = dv.pages('"10_Finance/Assets" and #alert');

let totalAlertValue = 0;
let count = 0;

for (let p of alertPages) {
    let val = (p.value_base !== undefined && p.value_base !== null) ? p.value_base : (p.value_pln || 0);
    totalAlertValue += val;
    count += 1;
}

if (count === 0) {
    dv.paragraph("> [!SUCCESS] **All clear!** No active alerts across portfolio assets.");
} else {
    dv.paragraph(`> [!WARNING] **${count} asset(s)** currently flagged with alerts totaling **${formatCurrency(totalAlertValue)}** in portfolio exposure.`);
}
```

## Active Alerts

```dataview
TABLE 
    name AS "Name",
    tags AS "Alerts",
    last_updated AS "Last Updated"
FROM "10_Finance/Assets" AND #alert
SORT default(value_base, value_pln) DESC
```

## 📈 Overvalued Assets (`P/E > 40`)

```dataview
TABLE 
    name AS "Name",
    pe_ratio AS "P/E",
    current_price AS "Current Price",
    currency AS "Currency",
    default(value_base, value_pln) AS "Value (Base)"
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
    default(value_base, value_pln) AS "Value (Base)"
FROM "10_Finance/Assets" AND #alert/insider_sell
SORT default(value_base, value_pln) DESC
```

## ⚠️ Delisting Risk (`AUM < 50M`)

```dataview
TABLE 
    name AS "Name",
    fund_size AS "Fund Size / AUM",
    current_price AS "Current Price",
    currency AS "Currency",
    default(value_base, value_pln) AS "Value (Base)"
FROM "10_Finance/Assets" AND #alert/delisting_risk
SORT default(value_base, value_pln) DESC
```

## ⚖️ Allocation Drift (`Weight > Limit`)

```dataview
TABLE 
    name AS "Name",
    portfolio AS "Portfolio",
    asset_type AS "Type",
    current_price AS "Current Price",
    default(value_base, value_pln) AS "Value (Base)"
FROM "10_Finance/Assets" AND #alert/allocation_drift
SORT default(value_base, value_pln) DESC
```

## 🛑 Stop Loss Breached (`Price <= Stop Loss`)

```dataview
TABLE 
    name AS "Name",
    current_price AS "Current Price",
    stop_loss AS "Stop Loss Level",
    currency AS "Currency",
    default(value_base, value_pln) AS "Value (Base)"
FROM "10_Finance/Assets" AND #alert/stop_loss
SORT default(value_base, value_pln) DESC
```

## 📉 Inverted Yield Curve / Macro Recession Risk (`US 10Y-2Y Spread < 0`)

```dataview
TABLE 
    name AS "Name",
    portfolio AS "Portfolio",
    dominant_sector AS "Sector",
    current_price AS "Current Price",
    default(value_base, value_pln) AS "Value (Base)"
FROM "10_Finance/Assets" AND #alert/macro_inverted_yield_curve
SORT default(value_base, value_pln) DESC
```