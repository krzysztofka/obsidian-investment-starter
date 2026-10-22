/**
 * Shared DataviewJS View: Alert Banner & Risk Summary
 *
 * Parameters passed via `input`:
 *   - pages: Array or Dataview DataArray of asset pages
 *   - portfolioName: (Optional) String name of sub-portfolio (e.g. "Safety Net", "Aggressive")
 *   - render: (Optional) Boolean, whether to render the paragraph banner (default: true)
 *
 * Usage:
 *   await dv.view("99_System/Views/alert_banner", {
 *       pages: pages,
 *       portfolioName: "Aggressive"
 *   });
 */

let pages = input?.pages || [];
let portfolioName = input?.portfolioName || null;
let shouldRender = input?.render !== false;

// 1. Load config.yaml for currency formatting
let configContent = null;
try {
    let obsApp = (typeof app !== "undefined" && app) ? app : (dv?.app || window?.app);
    if (obsApp && obsApp.vault && obsApp.vault.adapter) {
        configContent = await obsApp.vault.adapter.read("config.yaml");
    }
} catch (e) {}

if (!configContent && dv?.io?.load) {
    try { configContent = await dv.io.load("config.yaml"); } catch (e) {}
}

let parsedConfig = null;
if (configContent) {
    try {
        let parseYamlFn = window?.parseYaml || (typeof require === "function" ? require("obsidian")?.parseYaml : null) || window?.require?.("obsidian")?.parseYaml;
        if (typeof parseYamlFn === "function") parsedConfig = parseYamlFn(configContent);
    } catch (e) {}
    if (!parsedConfig) {
        let bc = configContent.match(/base_currency:\s*["']?([A-Za-z]{3})["']?/);
        let cs = configContent.match(/currency_symbol:\s*["']?([^"'\r\n#]+)["']?/);
        let sp = configContent.match(/symbol_position:\s*["']?(prefix|suffix)["']?/);
        parsedConfig = {
            localization: {
                base_currency: bc ? bc[1].trim() : "PLN",
                currency_symbol: cs ? cs[1].trim() : "zł",
                symbol_position: sp ? sp[1].trim() : "suffix"
            }
        };
    }
}

let baseCurrency = parsedConfig?.localization?.base_currency || "PLN";
let currencySymbol = parsedConfig?.localization?.currency_symbol || "zł";
let symbolPosition = parsedConfig?.localization?.symbol_position || "suffix";

function formatCurrency(amount) {
    let formatted = amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (symbolPosition === "prefix") {
        return `${currencySymbol}${formatted}`;
    }
    return `${formatted} ${currencySymbol}`;
}

let alertBreakdown = {
    "Overvalued": 0,
    "Insider Selling": 0,
    "Delisting Risk": 0,
    "Allocation Drift": 0,
    "Stop Loss": 0,
    "Other": 0
};
let alertCount = 0;
let alertValue = 0;

for (let p of pages) {
    let val = (p.value_base !== undefined && p.value_base !== null) ? p.value_base : (p.value_pln || 0);
    let rawTags = [];
    if (p.tags) {
        rawTags = Array.isArray(p.tags) ? p.tags : [p.tags];
    } else if (p.file && p.file.tags) {
        rawTags = Array.isArray(p.file.tags) ? p.file.tags : [p.file.tags];
    }

    let assetHasAlert = false;
    for (let t of rawTags) {
        let tagStr = String(t);
        if (tagStr.startsWith("#alert") || tagStr.startsWith("alert")) {
            assetHasAlert = true;
            if (tagStr.includes("overvalued")) {
                alertBreakdown["Overvalued"]++;
            } else if (tagStr.includes("insider_sell")) {
                alertBreakdown["Insider Selling"]++;
            } else if (tagStr.includes("delisting_risk")) {
                alertBreakdown["Delisting Risk"]++;
            } else if (tagStr.includes("allocation_drift")) {
                alertBreakdown["Allocation Drift"]++;
            } else if (tagStr.includes("stop_loss")) {
                alertBreakdown["Stop Loss"]++;
            } else {
                alertBreakdown["Other"]++;
            }
        }
    }
    if (assetHasAlert) {
        alertCount++;
        alertValue += val;
    }
}

if (shouldRender) {
    if (alertCount > 0) {
        let subBadges = [];
        if (alertBreakdown["Overvalued"] > 0) subBadges.push(`📈 Overvalued: **${alertBreakdown["Overvalued"]}**`);
        if (alertBreakdown["Insider Selling"] > 0) subBadges.push(`📉 Insider Selling: **${alertBreakdown["Insider Selling"]}**`);
        if (alertBreakdown["Delisting Risk"] > 0) subBadges.push(`⚠️ Delisting Risk: **${alertBreakdown["Delisting Risk"]}**`);
        if (alertBreakdown["Allocation Drift"] > 0) subBadges.push(`⚖️ Allocation Drift: **${alertBreakdown["Allocation Drift"]}**`);
        if (alertBreakdown["Stop Loss"] > 0) subBadges.push(`🛑 Stop Loss: **${alertBreakdown["Stop Loss"]}**`);
        if (alertBreakdown["Other"] > 0) subBadges.push(`🔔 Other: **${alertBreakdown["Other"]}**`);

        let breakdownStr = subBadges.length > 0 ? ` (${subBadges.join(" · ")})` : "";
        dv.paragraph(`> [!WARNING] 🚨 **[[Alerts|Active Alerts]]:** **${alertCount} asset(s)** flagged with **${formatCurrency(alertValue)}** exposure${breakdownStr}.`);
    } else {
        let scopeStr = portfolioName ? ` in ${portfolioName}` : "";
        dv.paragraph(`> [!SUCCESS] 🛡️ **[[Alerts|Portfolio Health]]:** All clear — no active alerts${scopeStr}.`);
    }
}

return {
    alertCount,
    alertValue,
    alertBreakdown
};
