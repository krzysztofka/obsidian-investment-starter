/**
 * Shared DataviewJS View: Rebalancing & Model Portfolio Drift Alerting Dashboard
 *
 * Parameters passed via `input`:
 *   - portfolio: (Required) String name of sub-portfolio (e.g. "Aggressive", "Long term", "Safety net")
 *
 * Usage:
 *   await dv.view("99_System/Views/rebalance_status", { portfolio: "Aggressive" });
 */

let portfolioParam = input?.portfolio ? String(input.portfolio).trim() : null;
if (!portfolioParam) {
    dv.paragraph("> [!WARNING] ⚠️ **Rebalance View:** No portfolio specified.");
    return;
}

// 1. Load config.yaml via Obsidian vault adapter or Dataview I/O
let configContent = null;
try {
    let obsApp = (typeof app !== "undefined" && app) ? app : (dv?.app || window?.app);
    if (obsApp && obsApp.vault && obsApp.vault.adapter) {
        configContent = await obsApp.vault.adapter.read("config.yaml");
    }
} catch (e) {
    configContent = null;
}

if (!configContent && dv?.io?.load) {
    try {
        configContent = await dv.io.load("config.yaml");
    } catch (e) {
        configContent = null;
    }
}

function parseScalarYamlValue(rawVal) {
    let v = (rawVal || "").trim();
    if (!v) return "";
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) {
        return v.slice(1, -1);
    }
    let commentIdx = v.indexOf(" #");
    if (commentIdx !== -1) {
        v = v.slice(0, commentIdx).trim();
    }
    if (v === "true") return true;
    if (v === "false") return false;
    if (v === "null" || v === "~") return null;
    if (/^-?\d+(\.\d+)?$/.test(v)) return parseFloat(v);
    return v;
}

function parseConfigYamlFallback(yamlText) {
    let result = { localization: {}, model_portfolios: {} };
    if (!yamlText || typeof yamlText !== "string") return result;

    let lines = yamlText.split(/\r?\n/);
    let topSection = null;
    let currentPortKey = null;
    let currentPort = null;
    let inLayers = false;
    let currentLayer = null;
    let currentItem = null;

    for (let rawLine of lines) {
        if (!rawLine || !rawLine.trim() || rawLine.trim().startsWith("#")) continue;

        let indentMatch = rawLine.match(/^(\s*)/);
        let indent = indentMatch ? indentMatch[1].length : 0;
        let trimmed = rawLine.trim();

        if (indent === 0) {
            let m = trimmed.match(/^([a-zA-Z0-9_\-]+):\s*(.*)$/);
            if (m) {
                topSection = m[1];
                currentPortKey = null;
                currentPort = null;
                inLayers = false;
                currentLayer = null;
                currentItem = null;
            }
            continue;
        }

        if (topSection === "localization" && indent >= 2) {
            let m = trimmed.match(/^([a-zA-Z0-9_\-]+):\s*(.*)$/);
            if (m && m[2]) {
                result.localization[m[1]] = parseScalarYamlValue(m[2]);
            }
        } else if (topSection === "model_portfolios") {
            if (indent === 2 && !trimmed.startsWith("-")) {
                let m = trimmed.match(/^([a-zA-Z0-9_\-]+):\s*$/);
                if (m) {
                    currentPortKey = m[1];
                    currentPort = { layers: { asset_classes: [], sectors: [], assets: [] } };
                    result.model_portfolios[currentPortKey] = currentPort;
                    inLayers = false;
                    currentLayer = null;
                    currentItem = null;
                }
            } else if (currentPort && indent === 4 && !trimmed.startsWith("-")) {
                let m = trimmed.match(/^([a-zA-Z0-9_\-]+):\s*(.*)$/);
                if (m) {
                    let k = m[1];
                    let v = m[2];
                    if (k === "layers") {
                        inLayers = true;
                        currentLayer = null;
                        currentItem = null;
                    } else {
                        inLayers = false;
                        currentLayer = null;
                        currentItem = null;
                        currentPort[k] = parseScalarYamlValue(v);
                    }
                }
            } else if (currentPort && inLayers) {
                if (indent === 6 && !trimmed.startsWith("-")) {
                    let m = trimmed.match(/^([a-zA-Z0-9_\-]+):\s*(.*)$/);
                    if (m) {
                        currentLayer = m[1];
                        if (!currentPort.layers[currentLayer]) {
                            currentPort.layers[currentLayer] = [];
                        }
                        currentItem = null;
                    }
                } else if (currentLayer && trimmed.startsWith("-")) {
                    let itemLine = trimmed.replace(/^-\s*/, "");
                    currentItem = {};
                    currentPort.layers[currentLayer].push(currentItem);
                    let m = itemLine.match(/^([a-zA-Z0-9_\-]+):\s*(.*)$/);
                    if (m) {
                        currentItem[m[1]] = parseScalarYamlValue(m[2]);
                    }
                } else if (currentLayer && currentItem && indent >= 8) {
                    let m = trimmed.match(/^([a-zA-Z0-9_\-]+):\s*(.*)$/);
                    if (m) {
                        currentItem[m[1]] = parseScalarYamlValue(m[2]);
                    }
                }
            }
        }
    }
    return result;
}

let parsedConfig = null;
if (configContent) {
    try {
        let parseYamlFn = window?.parseYaml;
        if (!parseYamlFn && typeof require === "function") {
            try { parseYamlFn = require("obsidian")?.parseYaml; } catch(err) {}
        }
        if (!parseYamlFn && typeof window?.require === "function") {
            try { parseYamlFn = window.require("obsidian")?.parseYaml; } catch(err) {}
        }
        if (typeof parseYamlFn === "function") {
            parsedConfig = parseYamlFn(configContent);
        }
    } catch (e) {
        parsedConfig = null;
    }

    if (!parsedConfig || !parsedConfig.model_portfolios) {
        parsedConfig = parseConfigYamlFallback(configContent);
    }
}

// 2. Locate model portfolio configuration
function normalizeName(str) {
    return (str || "").toLowerCase().replace(/[\s_\-]+/g, "");
}

let targetNorm = normalizeName(portfolioParam);
let modelPortfolios = parsedConfig?.model_portfolios || {};
let modelConfig = null;
let portfolioKey = null;

for (let key in modelPortfolios) {
    let cfg = modelPortfolios[key];
    if (normalizeName(key) === targetNorm || normalizeName(cfg?.name) === targetNorm) {
        modelConfig = cfg;
        portfolioKey = key;
        break;
    }
}

let primaryLayer = modelConfig?.primary_layer || "asset_classes";
let layerTargets = modelConfig?.layers?.[primaryLayer] || [];

// Fallback message if model portfolio is not configured
if (!modelConfig || !layerTargets || layerTargets.length === 0) {
    dv.paragraph(`> [!NOTE] ℹ️ **Model Portfolio:** Targets are not configured for **${portfolioParam}** in \`config.yaml\`.`);
    return;
}

// 3. Collect assets for this portfolio
let allPages = dv.pages('"10_Finance/Assets"');
let portfolioPages = [];
let totalPortfolioValue = 0;

function isMatchingPortfolio(p) {
    let port = normalizeName(p.portfolio);
    return port === targetNorm;
}

for (let p of allPages) {
    let val = (p.value_base !== undefined && p.value_base !== null) ? p.value_base : (p.value_pln || 0);
    if (!isMatchingPortfolio(p)) continue;
    if (val <= 0 && !p.name && !p.ticker) continue;

    portfolioPages.push(p);
    totalPortfolioValue += val;
}

// 4. Calculate actual distribution based on primary layer
let actualBuckets = {};

if (primaryLayer === "asset_classes") {
    // Canonical asset class buckets
    actualBuckets = {
        "Equities": 0,
        "Bonds": 0,
        "Real Estate": 0,
        "Commodities": 0,
        "Cash": 0
    };

    for (let p of portfolioPages) {
        let val = (p.value_base !== undefined && p.value_base !== null) ? p.value_base : (p.value_pln || 0);
        let alloc = (p.file && p.file.frontmatter && p.file.frontmatter.asset_allocation) || p.asset_allocation;
        if (typeof alloc === "string") {
            try { alloc = JSON.parse(alloc); } catch(e) {}
        }

        if (alloc && typeof alloc === "object") {
            let eq = (alloc.equity || alloc.equities || 0) / 100;
            let bd = (alloc.bonds || alloc.bond || alloc.fixed_income || alloc.obligations || 0) / 100;
            let re = (alloc.real_estate || alloc.reits || 0) / 100;
            let cm = (alloc.commodities || alloc.commodity || alloc.gold || 0) / 100;
            let cs = (alloc.cash || 0) / 100;

            let sumAlloc = eq + bd + re + cm + cs;
            if (sumAlloc > 0) {
                actualBuckets["Equities"] += val * eq;
                actualBuckets["Bonds"] += val * bd;
                actualBuckets["Real Estate"] += val * re;
                actualBuckets["Commodities"] += val * cm;
                actualBuckets["Cash"] += val * cs;
            } else {
                actualBuckets["Equities"] += val;
            }
        } else {
            let atype = (p.asset_type || "").toLowerCase();
            let sec = (p.dominant_sector || p.industry || "").toLowerCase();
            let name = (p.name || "").toLowerCase();
            let ticker = (p.ticker || "").toLowerCase();

            if (atype === "cash" || ticker.includes("cash") || sec === "cash") {
                actualBuckets["Cash"] += val;
            } else if (atype.includes("real estate") || sec.includes("real estate") || atype.includes("reit")) {
                actualBuckets["Real Estate"] += val;
            } else if (atype.includes("gold") || sec.includes("precious metals") || atype.includes("commodity") || ticker === "gold") {
                actualBuckets["Commodities"] += val;
            } else if (sec === "sovereign" || name.includes("bond") || name.includes("treasury") || atype.includes("bond")) {
                actualBuckets["Bonds"] += val;
            } else {
                actualBuckets["Equities"] += val;
            }
        }
    }
} else if (primaryLayer === "sectors") {
    for (let p of portfolioPages) {
        let val = (p.value_base !== undefined && p.value_base !== null) ? p.value_base : (p.value_pln || 0);
        let secName = p.dominant_sector || p.industry || "Diversified";
        actualBuckets[secName] = (actualBuckets[secName] || 0) + val;
    }
} else if (primaryLayer === "assets") {
    for (let p of portfolioPages) {
        let val = (p.value_base !== undefined && p.value_base !== null) ? p.value_base : (p.value_pln || 0);
        let aKey = p.ticker || p.name || p.file.name;
        actualBuckets[aKey] = (actualBuckets[aKey] || 0) + val;
    }
}

// Helper to normalize bucket lookups
function getActualValue(targetName) {
    let tNorm = normalizeName(targetName);
    for (let b in actualBuckets) {
        let bNorm = normalizeName(b);
        if (bNorm === tNorm) return actualBuckets[b];
        // Handle Bonds vs Bonds / Obligations
        if ((tNorm.includes("bond") || tNorm.includes("obligation")) && (bNorm.includes("bond") || bNorm.includes("obligation"))) {
            return actualBuckets[b];
        }
        // Handle Gold vs Commodities
        if ((tNorm.includes("gold") || tNorm.includes("commodit")) && (bNorm.includes("gold") || bNorm.includes("commodit"))) {
            return actualBuckets[b];
        }
    }
    return actualBuckets[targetName] || 0;
}

// 5. Evaluate Targets & Drift
let tableRows = [];
let driftCount = 0;
let breachSummaries = [];
let baseCurrency = parsedConfig?.localization?.base_currency || "PLN";
let currencySymbol = parsedConfig?.localization?.currency_symbol || "zł";
let symbolPosition = parsedConfig?.localization?.symbol_position || "suffix";
let defaultBand = modelConfig.tolerance_band_pct !== undefined ? modelConfig.tolerance_band_pct : 5.0;
let defaultMinTrade = modelConfig.min_trade_amount !== undefined ? modelConfig.min_trade_amount : (modelConfig.min_trade_amount_pln !== undefined ? modelConfig.min_trade_amount_pln : 500.0);
let strategy = modelConfig.rebalance_strategy || "inflow_first";

if (totalPortfolioValue <= 0) {
    dv.paragraph(`> [!INFO] ℹ️ **[[Alerts|Rebalance Status]]:** Portfolio **${portfolioParam}** has no holdings yet (0 ${baseCurrency}) — drift evaluation skipped.`);
    return;
}

for (let item of layerTargets) {
    let targetName = item.target;
    let targetWeight = item.weight_pct || 0;
    let band = item.tolerance_band_pct !== undefined && item.tolerance_band_pct !== null ? item.tolerance_band_pct : defaultBand;
    let minTrade = item.min_trade_amount !== undefined && item.min_trade_amount !== null ? item.min_trade_amount : (item.min_trade_amount_pln !== undefined && item.min_trade_amount_pln !== null ? item.min_trade_amount_pln : defaultMinTrade);

    let actualVal = getActualValue(targetName);
    let actualWeight = totalPortfolioValue > 0 ? (actualVal / totalPortfolioValue) * 100 : 0;
    let drift = actualWeight - targetWeight;

    let lowerBound = Math.max(0, targetWeight - band);
    let upperBound = Math.min(100, targetWeight + band);

    let isOver = actualWeight > upperBound;
    let isUnder = actualWeight < lowerBound;
    let corridorBreach = isOver ? (actualWeight - upperBound) : (isUnder ? (actualWeight - lowerBound) : 0);

    // Delta in base currency: positive means need to BUY/ADD, negative means need to TRIM/SELL
    let deltaBase = ((targetWeight - actualWeight) / 100) * totalPortfolioValue;
    let meetsMinTrade = Math.abs(deltaBase) >= minTrade;
    let isActionable = (isOver || isUnder) && meetsMinTrade;

    let deltaSign = deltaBase >= 0 ? "+" : "-";
    let formattedNum = Math.abs(deltaBase).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
    let valStr = symbolPosition === "prefix" ? `${deltaSign}${currencySymbol}${formattedNum}` : `${deltaSign}${formattedNum} ${currencySymbol}`;
    let deltaFormatted = meetsMinTrade
        ? valStr
        : "— (Below min)";

    let driftSign = drift >= 0 ? "+" : "";
    let breachSign = corridorBreach >= 0 ? "+" : "";
    let driftFormatted = isActionable
        ? `${driftSign}${drift.toFixed(1)}% (${breachSign}${corridorBreach.toFixed(1)}% corridor)`
        : `${driftSign}${drift.toFixed(1)}%`;

    let statusBadge = "🟢 **Balanced**";
    if (isActionable && isOver) {
        statusBadge = "🟠 **Overweight**";
        driftCount++;
        breachSummaries.push(`**${targetName}** (${actualWeight.toFixed(1)}% vs ${targetWeight.toFixed(1)}% ±${band.toFixed(1)}%, drift ${driftSign}${drift.toFixed(1)}% / ${breachSign}${corridorBreach.toFixed(1)}% above corridor, delta ${valStr})`);
    } else if (isActionable && isUnder) {
        statusBadge = "🔵 **Underweight**";
        driftCount++;
        breachSummaries.push(`**${targetName}** (${actualWeight.toFixed(1)}% vs ${targetWeight.toFixed(1)}% ±${band.toFixed(1)}%, drift ${driftSign}${drift.toFixed(1)}% / ${breachSign}${corridorBreach.toFixed(1)}% below corridor, delta ${valStr})`);
    }

    tableRows.push([
        `**${targetName}**`,
        `${actualWeight.toFixed(1)}%`,
        `${targetWeight.toFixed(1)}%`,
        `[${lowerBound.toFixed(1)}% – ${upperBound.toFixed(1)}%]`,
        driftFormatted,
        statusBadge,
        deltaFormatted
    ]);
}

// 6. Render Alert Banner & Table
if (driftCount > 0) {
    let detailsStr = breachSummaries.map(s => `> - ⚠️ ${s}`).join("\n");
    dv.paragraph(`> [!WARNING] ⚖️ **[[Alerts|Rebalance Alert]]:** Rebalancing required in **${portfolioParam}**! **${driftCount} target(s)** breached Tolerance Corridor (strategy: \`${strategy}\`):\n${detailsStr}`);
} else {
    dv.paragraph(`> [!SUCCESS] ⚖️ **[[Alerts|Rebalance Status]]:** All configured targets in **${portfolioParam}** are within Tolerance Corridor.`);
}

dv.table(
    ["Target Allocation", "Actual %", "Target %", "Corridor", "Drift %", "Status", `Rebalance Delta (${baseCurrency})`],
    tableRows
);
