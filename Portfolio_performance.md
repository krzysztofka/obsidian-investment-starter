# 📈 Portfolio History & Performance

```dataviewjs
// 1. Load CSV data from 10_Finance/History/portfolio.csv
let rawCsv = "";
try {
    rawCsv = await app.vault.adapter.read("10_Finance/History/portfolio.csv");
} catch (e) {
    dv.paragraph("> [!ERROR] Could not read file `10_Finance/History/portfolio.csv`.");
    return;
}

// 2. Parse CSV helper (handles quoted fields)
function parseCSV(text) {
    const lines = text.trim().split(/\r?\n/);
    if (lines.length < 2) return [];
    const headers = lines[0].split(',').map(h => h.trim());
    const results = [];
    
    for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;
        
        const row = [];
        let inQuotes = false;
        let token = "";
        for (let j = 0; j < line.length; j++) {
            const char = line[j];
            if (char === '"' || char === "'") {
                inQuotes = !inQuotes;
            } else if (char === ',' && !inQuotes) {
                row.push(token.trim());
                token = "";
            } else {
                token += char;
            }
        }
        row.push(token.trim());
        
        const obj = {};
        headers.forEach((h, idx) => {
            let val = row[idx] !== undefined ? row[idx] : "";
            if (val.startsWith('"') && val.endsWith('"')) {
                val = val.slice(1, -1);
            }
            obj[h] = val;
        });
        results.push(obj);
    }
    return results;
}

const records = parseCSV(rawCsv);

if (records.length === 0) {
    dv.paragraph("> [!WARNING] No historical records found in `10_Finance/History/portfolio.csv`.");
    return;
}

// 3. Multi-platform forward-fill aggregation
// Handles imports from different brokers (Degiro, Exante) on different dates
const assetPortfolioMap = new Map();
try {
    for (const p of dv.pages('"10_Finance/Assets"')) {
        const rawPort = (p.portfolio || "").toLowerCase().trim();
        let port = "Unallocated";
        if (rawPort === "safety net" || rawPort === "safety" || rawPort === "safety_net") port = "Safety net";
        else if (rawPort === "long term" || rawPort === "long_term") port = "Long term";
        else if (rawPort === "aggressive") port = "Aggressive";
        if (p.ticker) assetPortfolioMap.set(p.ticker.trim(), port);
        if (p.file && p.file.name) assetPortfolioMap.set(p.file.name.trim(), port);
    }
    for (const d of dv.pages('"20_Decisions"')) {
        if (d.ticker && !assetPortfolioMap.has(d.ticker.trim())) {
            const rawPort = (d.portfolio || "").toLowerCase().trim();
            let port = "Unallocated";
            if (rawPort === "safety net" || rawPort === "safety" || rawPort === "safety_net") port = "Safety net";
            else if (rawPort === "long term" || rawPort === "long_term") port = "Long term";
            else if (rawPort === "aggressive") port = "Aggressive";
            assetPortfolioMap.set(d.ticker.trim(), port);
        }
    }
} catch (e) {}

const rowsByDate = new Map();
for (const r of records) {
    if (!rowsByDate.has(r.date)) rowsByDate.set(r.date, []);
    rowsByDate.get(r.date).push(r);
}

const sortedDates = Array.from(rowsByDate.keys()).sort();
const activeHoldings = new Map();
const portfolioSnapshots = [];

for (const d of sortedDates) {
    const dayRows = rowsByDate.get(d) || [];
    for (const r of dayRows) {
        const valPln = parseFloat(r.value_pln) || 0;
        const price = parseFloat(r.current_price) || 0;
        const pe = r.pe_ratio && !isNaN(parseFloat(r.pe_ratio)) ? parseFloat(r.pe_ratio) : null;
        const qty = parseFloat(r.quantity) || 0;
        const name = r.name || r.ticker;
        
        let port = (r.portfolio || "").trim();
        if (!port && assetPortfolioMap.has(r.ticker)) port = assetPortfolioMap.get(r.ticker);
        const portLower = port.toLowerCase();
        if (portLower === "safety net" || portLower === "safety" || portLower === "safety_net") port = "Safety net";
        else if (portLower === "long term" || portLower === "long_term") port = "Long term";
        else if (portLower === "aggressive") port = "Aggressive";
        else port = "Unallocated";
        
        activeHoldings.set(r.ticker, {
            ticker: r.ticker,
            name: name,
            valPln: valPln,
            price: price,
            pe: pe,
            qty: qty,
            port: port,
            lastUpdatedDate: d
        });
    }

    let totalVal = 0;
    let aggVal = 0;
    let ltVal = 0;
    let snVal = 0;
    let unallocVal = 0;
    let topAsset = { name: '', val: 0 };
    const snapshotAssets = [];

    for (const [ticker, h] of activeHoldings.entries()) {
        totalVal += h.valPln;
        if (h.port === "Aggressive") aggVal += h.valPln;
        else if (h.port === "Long term") ltVal += h.valPln;
        else if (h.port === "Safety net") snVal += h.valPln;
        else unallocVal += h.valPln;

        if (h.valPln > topAsset.val) {
            topAsset = { name: h.name, val: h.valPln };
        }
        snapshotAssets.push({ ...h });
    }

    portfolioSnapshots.push({
        date: d,
        totalValue: totalVal,
        subValues: {
            aggressive: aggVal,
            longTerm: ltVal,
            safetyNet: snVal,
            unallocated: unallocVal
        },
        assets: snapshotAssets,
        topAsset: topAsset,
        count: activeHoldings.size
    });
}

// 4. Calculate key metrics
const latest = portfolioSnapshots[portfolioSnapshots.length - 1];
const previous = portfolioSnapshots.length > 1 ? portfolioSnapshots[portfolioSnapshots.length - 2] : null;
const earliest = portfolioSnapshots[0];

const totalChangePln = latest.totalValue - earliest.totalValue;
const totalChangePct = earliest.totalValue > 0 ? ((totalChangePln / earliest.totalValue) * 100) : 0;

let periodChangePln = 0;
let periodChangePct = 0;
if (previous) {
    periodChangePln = latest.totalValue - previous.totalValue;
    periodChangePct = previous.totalValue > 0 ? ((periodChangePln / previous.totalValue) * 100) : 0;
}

const changeIcon = periodChangePln >= 0 ? "🟢 +" : "🔴 ";
const totalChangeIcon = totalChangePln >= 0 ? "🟢 +" : "🔴 ";

const ltVal = latest.subValues?.longTerm || 0;
const aggVal = latest.subValues?.aggressive || 0;
const snVal = latest.subValues?.safetyNet || 0;
const ltPct = latest.totalValue > 0 ? ((ltVal / latest.totalValue) * 100).toFixed(1) : "0.0";
const aggPct = latest.totalValue > 0 ? ((aggVal / latest.totalValue) * 100).toFixed(1) : "0.0";
const snPct = latest.totalValue > 0 ? ((snVal / latest.totalValue) * 100).toFixed(1) : "0.0";

dv.paragraph(`
> [!NOTE] 📊 **Portfolio Historical Snapshot**
> **Current Total Value (${latest.date}):** \`${latest.totalValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} PLN\`  
> **Sub-Portfolios:** 🏛️ Long Term: \`${ltVal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} PLN\` (${ltPct}%) · 🚀 Aggressive: \`${aggVal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} PLN\` (${aggPct}%) · 🛡️ Safety Net: \`${snVal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} PLN\` (${snPct}%)  
> **Change vs Previous (${previous ? previous.date : 'N/A'}):** \`${changeIcon}${periodChangePln.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} PLN (${periodChangePct >= 0 ? '+' : ''}${periodChangePct.toFixed(2)}%)\`  
> **Overall Tracked Change (${earliest.date} ➔ ${latest.date}):** \`${totalChangeIcon}${totalChangePln.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} PLN (${totalChangePct >= 0 ? '+' : ''}${totalChangePct.toFixed(2)}%)\`  
> **Active Positions:** \`${latest.count}\` | **Total Snapshots:** \`${sortedDates.length}\`
`);
```

## 📊 Portfolio Valuation Over Time (PLN)

```dataviewjs
// Load and prepare data for multi-line portfolio valuation chart with multi-broker forward-fill
let rawCsv = "";
try {
    rawCsv = await app.vault.adapter.read("10_Finance/History/portfolio.csv");
} catch (e) {
    dv.paragraph("> [!ERROR] Could not read file `10_Finance/History/portfolio.csv`.");
    return;
}

function parseCSV(text) {
    const lines = text.trim().split(/\r?\n/);
    if (lines.length < 2) return [];
    const headers = lines[0].split(',').map(h => h.trim());
    const results = [];
    for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;
        const row = [];
        let inQuotes = false;
        let token = "";
        for (let j = 0; j < line.length; j++) {
            const char = line[j];
            if (char === '"' || char === "'") inQuotes = !inQuotes;
            else if (char === ',' && !inQuotes) { row.push(token.trim()); token = ""; }
            else token += char;
        }
        row.push(token.trim());
        const obj = {};
        headers.forEach((h, idx) => {
            let val = row[idx] !== undefined ? row[idx] : "";
            if (val.startsWith('"') && val.endsWith('"')) val = val.slice(1, -1);
            obj[h] = val;
        });
        results.push(obj);
    }
    return results;
}

const records = parseCSV(rawCsv);
if (records.length === 0) {
    dv.paragraph("> [!WARNING] No historical records found in `10_Finance/History/portfolio.csv`.");
    return;
}

// Build ticker-to-portfolio mapping from 10_Finance/Assets and 20_Decisions
const assetPortfolioMap = new Map();
try {
    const assetPages = dv.pages('"10_Finance/Assets"');
    for (const p of assetPages) {
        const rawPort = (p.portfolio || "").toLowerCase().trim();
        let port = "Unallocated";
        if (rawPort === "safety net" || rawPort === "safety" || rawPort === "safety_net") port = "Safety net";
        else if (rawPort === "long term" || rawPort === "long_term") port = "Long term";
        else if (rawPort === "aggressive") port = "Aggressive";

        if (p.ticker) assetPortfolioMap.set(p.ticker.trim(), port);
        if (p.file && p.file.name) assetPortfolioMap.set(p.file.name.trim(), port);
    }
    const decisionPages = dv.pages('"20_Decisions"');
    for (const d of decisionPages) {
        if (d.ticker && !assetPortfolioMap.has(d.ticker.trim())) {
            const rawPort = (d.portfolio || "").toLowerCase().trim();
            let port = "Unallocated";
            if (rawPort === "safety net" || rawPort === "safety" || rawPort === "safety_net") port = "Safety net";
            else if (rawPort === "long term" || rawPort === "long_term") port = "Long term";
            else if (rawPort === "aggressive") port = "Aggressive";
            assetPortfolioMap.set(d.ticker.trim(), port);
        }
    }
} catch (e) {
    console.error("Error reading asset portfolios:", e);
}

// Group records by date
const rowsByDate = new Map();
for (const r of records) {
    if (!rowsByDate.has(r.date)) rowsByDate.set(r.date, []);
    rowsByDate.get(r.date).push(r);
}

const sortedDates = Array.from(rowsByDate.keys()).sort();
const activeHoldings = new Map();
const historyData = [];

for (const d of sortedDates) {
    const dayRows = rowsByDate.get(d) || [];
    for (const r of dayRows) {
        const valPln = parseFloat(r.value_pln) || 0;
        let port = (r.portfolio || "").trim();
        if (!port && assetPortfolioMap.has(r.ticker)) {
            port = assetPortfolioMap.get(r.ticker);
        }
        const portLower = port.toLowerCase();
        if (portLower === "safety net" || portLower === "safety" || portLower === "safety_net") port = "Safety net";
        else if (portLower === "long term" || portLower === "long_term") port = "Long term";
        else if (portLower === "aggressive") port = "Aggressive";
        else port = "Unallocated";

        activeHoldings.set(r.ticker, {
            ticker: r.ticker,
            name: r.name || r.ticker,
            valPln: valPln,
            port: port
        });
    }

    let totalVal = 0;
    let aggVal = 0;
    let ltVal = 0;
    let snVal = 0;
    let unallocVal = 0;

    for (const h of activeHoldings.values()) {
        totalVal += h.valPln;
        if (h.port === "Aggressive") aggVal += h.valPln;
        else if (h.port === "Long term") ltVal += h.valPln;
        else if (h.port === "Safety net") snVal += h.valPln;
        else unallocVal += h.valPln;
    }

    historyData.push({
        date: d,
        total: Math.round(totalVal * 100) / 100,
        aggressive: Math.round(aggVal * 100) / 100,
        longTerm: Math.round(ltVal * 100) / 100,
        safetyNet: Math.round(snVal * 100) / 100,
        unallocated: Math.round(unallocVal * 100) / 100
    });
}

// Portfolio line configuration
const lineConfigs = [
    {
        key: "total",
        label: "🌐 Total Portfolio",
        shortLabel: "Total",
        color: "#6366f1",
        bgColor: "rgba(99, 102, 241, 0.08)",
        borderColor: "#6366f1",
        pointColor: "#4f46e5",
        borderWidth: 3,
        borderDash: [],
        defaultActive: true
    },
    {
        key: "aggressive",
        label: "🚀 Aggressive",
        shortLabel: "Aggressive",
        color: "#ef4444",
        bgColor: "rgba(239, 68, 68, 0.06)",
        borderColor: "#ef4444",
        pointColor: "#dc2626",
        borderWidth: 2.5,
        borderDash: [],
        defaultActive: true
    },
    {
        key: "longTerm",
        label: "🏛️ Long Term",
        shortLabel: "Long Term",
        color: "#0ea5e9",
        bgColor: "rgba(14, 165, 233, 0.06)",
        borderColor: "#0ea5e9",
        pointColor: "#0284c7",
        borderWidth: 2.5,
        borderDash: [],
        defaultActive: true
    },
    {
        key: "safetyNet",
        label: "🛡️ Safety Net",
        shortLabel: "Safety Net",
        color: "#10b981",
        bgColor: "rgba(16, 185, 129, 0.06)",
        borderColor: "#10b981",
        pointColor: "#059669",
        borderWidth: 2.5,
        borderDash: [],
        defaultActive: true
    },
    {
        key: "unallocated",
        label: "💵 Unallocated Cash",
        shortLabel: "Unallocated",
        color: "#94a3b8",
        bgColor: "rgba(148, 163, 184, 0.06)",
        borderColor: "#94a3b8",
        pointColor: "#64748b",
        borderWidth: 2,
        borderDash: [5, 5],
        defaultActive: false
    }
];

// Active visibility state
const activeState = {};
lineConfigs.forEach(c => { activeState[c.key] = c.defaultActive; });
let selectedDateRange = "ALL";

// UI Container
const container = this.container;
const uiWrapper = container.createDiv({ cls: "portfolio-valuation-controls-wrapper" });
uiWrapper.style.display = "flex";
uiWrapper.style.flexDirection = "column";
uiWrapper.style.gap = "10px";
uiWrapper.style.marginBottom = "14px";

// Controls Row 1: Line Toggles & Quick Presets
const row1 = uiWrapper.createDiv({ cls: "line-toggles-row" });
row1.style.display = "flex";
row1.style.flexWrap = "wrap";
row1.style.alignItems = "center";
row1.style.gap = "8px";
row1.style.padding = "6px 10px";
row1.style.backgroundColor = "var(--background-secondary)";
row1.style.borderRadius = "8px";
row1.style.border = "1px solid var(--background-modifier-border)";

const togglesLabel = row1.createEl("span", { text: "Lines: " });
togglesLabel.style.fontWeight = "bold";
togglesLabel.style.fontSize = "0.9em";

const toggleElements = {};

lineConfigs.forEach(c => {
    const chip = row1.createDiv({ cls: `portfolio-toggle-chip-${c.key}` });
    chip.style.display = "inline-flex";
    chip.style.alignItems = "center";
    chip.style.gap = "5px";
    chip.style.padding = "3px 8px";
    chip.style.borderRadius = "6px";
    chip.style.cursor = "pointer";
    chip.style.fontSize = "0.85em";
    chip.style.userSelect = "none";
    chip.style.transition = "all 0.15s ease";

    const cb = chip.createEl("input", { attr: { type: "checkbox" } });
    cb.checked = activeState[c.key];
    cb.style.cursor = "pointer";
    cb.style.accentColor = c.color;

    const dot = chip.createSpan();
    dot.style.display = "inline-block";
    dot.style.width = "8px";
    dot.style.height = "8px";
    dot.style.borderRadius = "50%";
    dot.style.backgroundColor = c.color;

    const textSpan = chip.createSpan({ text: c.label });
    textSpan.style.fontWeight = "500";

    function updateChipStyle() {
        if (activeState[c.key]) {
            chip.style.backgroundColor = "var(--background-secondary-alt)";
            chip.style.border = `1px solid ${c.color}`;
            chip.style.opacity = "1";
        } else {
            chip.style.backgroundColor = "transparent";
            chip.style.border = "1px solid var(--background-modifier-border)";
            chip.style.opacity = "0.55";
        }
    }
    updateChipStyle();

    chip.addEventListener("click", (e) => {
        if (e.target !== cb) cb.checked = !cb.checked;
        activeState[c.key] = cb.checked;
        updateChipStyle();
        updateView();
    });

    cb.addEventListener("change", () => {
        activeState[c.key] = cb.checked;
        updateChipStyle();
        updateView();
    });

    toggleElements[c.key] = { chip, cb, updateStyle: updateChipStyle };
});

// Separator
const sep = row1.createSpan({ text: "|" });
sep.style.color = "var(--text-muted)";
sep.style.margin = "0 4px";

// Quick Presets
const presetsGroup = row1.createDiv({ cls: "presets-group" });
presetsGroup.style.display = "inline-flex";
presetsGroup.style.gap = "6px";
presetsGroup.style.alignItems = "center";

function createPresetBtn(label, title, onClick) {
    const btn = presetsGroup.createEl("button", { text: label });
    btn.title = title;
    btn.style.padding = "2px 8px";
    btn.style.fontSize = "0.8em";
    btn.style.borderRadius = "4px";
    btn.style.backgroundColor = "var(--background-primary)";
    btn.style.color = "var(--text-normal)";
    btn.style.border = "1px solid var(--background-modifier-border)";
    btn.style.cursor = "pointer";
    btn.addEventListener("click", onClick);
    return btn;
}

createPresetBtn("All Lines", "Show all lines", () => {
    lineConfigs.forEach(c => {
        activeState[c.key] = true;
        toggleElements[c.key].cb.checked = true;
        toggleElements[c.key].updateStyle();
    });
    updateView();
});

createPresetBtn("Sub-Portfolios Only", "Compare Aggressive, Long Term & Safety Net on the same scale", () => {
    lineConfigs.forEach(c => {
        const isSub = (c.key === "aggressive" || c.key === "longTerm" || c.key === "safetyNet");
        activeState[c.key] = isSub;
        toggleElements[c.key].cb.checked = isSub;
        toggleElements[c.key].updateStyle();
    });
    updateView();
});

createPresetBtn("Total Only", "Show only Total Portfolio line", () => {
    lineConfigs.forEach(c => {
        const isTotal = (c.key === "total");
        activeState[c.key] = isTotal;
        toggleElements[c.key].cb.checked = isTotal;
        toggleElements[c.key].updateStyle();
    });
    updateView();
});

// Controls Row 2: Date Range Filter
const row2 = uiWrapper.createDiv({ cls: "filter-range-row" });
row2.style.display = "flex";
row2.style.flexWrap = "wrap";
row2.style.alignItems = "center";
row2.style.gap = "10px";

const dateRangeBox = row2.createDiv({ cls: "date-range-box" });
dateRangeBox.style.display = "flex";
dateRangeBox.style.alignItems = "center";
dateRangeBox.style.gap = "8px";

const rangeLabel = dateRangeBox.createEl("label", { text: "📅 Date Range: " });
rangeLabel.style.fontWeight = "bold";
rangeLabel.style.fontSize = "0.9em";

const dateRangeSelect = dateRangeBox.createEl("select");
dateRangeSelect.style.padding = "4px 8px";
dateRangeSelect.style.borderRadius = "6px";
dateRangeSelect.style.backgroundColor = "var(--background-secondary)";
dateRangeSelect.style.color = "var(--text-normal)";
dateRangeSelect.style.border = "1px solid var(--background-modifier-border)";
dateRangeSelect.style.cursor = "pointer";
dateRangeSelect.style.fontSize = "0.85em";

const optAll = dateRangeSelect.createEl("option", { value: "ALL", text: "📅 All History (ALL)" });
optAll.selected = true;
dateRangeSelect.createEl("option", { value: "1Y", text: "📅 Last 1 Year (1Y)" });
dateRangeSelect.createEl("option", { value: "YTD", text: "📅 Year to Date (YTD)" });
dateRangeSelect.createEl("option", { value: "6M", text: "📅 Last 6 Months (6M)" });
dateRangeSelect.createEl("option", { value: "3M", text: "📅 Last 3 Months (3M)" });
dateRangeSelect.createEl("option", { value: "1M", text: "📅 Last 1 Month (1M)" });

// KPI Summary Strip
const kpiStrip = uiWrapper.createDiv({ cls: "portfolio-kpi-summary-strip" });
kpiStrip.style.display = "grid";
kpiStrip.style.gridTemplateColumns = "repeat(auto-fit, minmax(170px, 1fr))";
kpiStrip.style.gap = "8px";

// Chart Box
const chartBox = container.createDiv({ cls: "portfolio-valuation-chart-box" });

function getFilteredHistory(rangePreset) {
    if (historyData.length === 0) return [];
    const latestDateStr = historyData[historyData.length - 1].date;
    const latestDate = new Date(latestDateStr);
    let fromStr = "";

    if (rangePreset === "ALL") return historyData;
    else if (rangePreset === "1M") {
        const d = new Date(latestDate); d.setMonth(d.getMonth() - 1);
        fromStr = d.toISOString().split('T')[0];
    } else if (rangePreset === "3M") {
        const d = new Date(latestDate); d.setMonth(d.getMonth() - 3);
        fromStr = d.toISOString().split('T')[0];
    } else if (rangePreset === "6M") {
        const d = new Date(latestDate); d.setMonth(d.getMonth() - 6);
        fromStr = d.toISOString().split('T')[0];
    } else if (rangePreset === "1Y") {
        const d = new Date(latestDate); d.setFullYear(d.getFullYear() - 1);
        fromStr = d.toISOString().split('T')[0];
    } else if (rangePreset === "YTD") {
        fromStr = `${latestDate.getFullYear()}-01-01`;
    }

    const filtered = historyData.filter(h => h.date >= fromStr);
    return filtered.length > 0 ? filtered : historyData;
}

function updateView() {
    selectedDateRange = dateRangeSelect.value;
    const currentHistory = getFilteredHistory(selectedDateRange);
    const dates = currentHistory.map(h => h.date);

    chartBox.empty();
    kpiStrip.empty();

    if (currentHistory.length === 0) {
        chartBox.createEl("p", { text: "No historical data in selected range." });
        return;
    }

    const firstPoint = currentHistory[0];
    const latestPoint = currentHistory[currentHistory.length - 1];
    const latestTotalVal = latestPoint.total > 0 ? latestPoint.total : 1;

    // Render KPI Cards for enabled lines
    lineConfigs.forEach(c => {
        if (!activeState[c.key]) return;

        const currentVal = latestPoint[c.key] || 0;
        const startVal = firstPoint[c.key] || 0;
        const diffVal = currentVal - startVal;
        const pctDiff = startVal > 0 ? ((diffVal / startVal) * 100) : 0;
        const sharePct = ((currentVal / latestTotalVal) * 100).toFixed(1);

        const card = kpiStrip.createDiv({ cls: `kpi-card-${c.key}` });
        card.style.padding = "8px 12px";
        card.style.borderRadius = "8px";
        card.style.backgroundColor = "var(--background-secondary-alt)";
        card.style.border = `1px solid ${c.color}`;
        card.style.display = "flex";
        card.style.flexDirection = "column";
        card.style.gap = "2px";

        const headerDiv = card.createDiv();
        headerDiv.style.display = "flex";
        headerDiv.style.justifyContent = "space-between";
        headerDiv.style.alignItems = "center";
        headerDiv.style.fontSize = "0.8em";
        headerDiv.style.color = "var(--text-muted)";
        headerDiv.innerHTML = `<span><strong>${c.label}</strong></span><span>${c.key !== 'total' ? sharePct + '%' : ''}</span>`;

        const valDiv = card.createDiv();
        valDiv.style.fontSize = "1.05em";
        valDiv.style.fontWeight = "bold";
        valDiv.style.color = "var(--text-normal)";
        valDiv.textContent = `${currentVal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} PLN`;

        const changeDiv = card.createDiv();
        changeDiv.style.fontSize = "0.78em";
        if (currentHistory.length > 1 && startVal > 0) {
            const sign = diffVal >= 0 ? "🟢 +" : "🔴 ";
            changeDiv.textContent = `${sign}${diffVal.toLocaleString('en-US', { maximumFractionDigits: 0 })} PLN (${pctDiff >= 0 ? '+' : ''}${pctDiff.toFixed(1)}%)`;
        } else {
            changeDiv.textContent = `Baseline snapshot`;
            changeDiv.style.color = "var(--text-muted)";
        }
    });

    // Build Chart Datasets for enabled lines
    const activeConfigs = lineConfigs.filter(c => activeState[c.key]);

    if (activeConfigs.length === 0) {
        chartBox.createEl("div", {
            text: "⚠️ All portfolio lines are disabled. Please enable at least one line above to view the valuation chart.",
            cls: "empty-chart-notice"
        }).style.padding = "24px";
        return;
    }

    const datasets = activeConfigs.map(c => {
        const isSingleLine = activeConfigs.length === 1;
        return {
            label: c.label,
            data: currentHistory.map(h => h[c.key]),
            borderColor: c.borderColor,
            backgroundColor: c.bgColor,
            borderWidth: c.borderWidth,
            borderDash: c.borderDash,
            fill: isSingleLine,
            tension: 0.22,
            pointRadius: currentHistory.length > 30 ? 2 : 4,
            pointHoverRadius: 6,
            pointBackgroundColor: c.pointColor,
            spanGaps: true
        };
    });

    window.renderChart({
        type: 'line',
        data: {
            labels: dates,
            datasets: datasets
        },
        options: {
            responsive: true,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        boxWidth: 8,
                        padding: 14
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(ctx) {
                            const val = ctx.raw;
                            if (val === null || val === undefined) return ctx.dataset.label + ': no data';
                            return ' ' + ctx.dataset.label + ': ' + Number(val).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' PLN';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    ticks: {
                        callback: function(val) {
                            return val.toLocaleString('en-US') + ' PLN';
                        }
                    }
                }
            }
        }
    }, chartBox);
}

dateRangeSelect.addEventListener("change", updateView);

// Initial render
updateView();
```

---

## 🔍 Asset Valuation Over Time (Interactive Filter)

```dataviewjs
// Interactive Asset Filter & History Chart with multi-platform forward-fill
const rawCsv = await app.vault.adapter.read("10_Finance/History/portfolio.csv");

function parseCSV(text) {
    const lines = text.trim().split(/\r?\n/);
    if (lines.length < 2) return [];
    const headers = lines[0].split(',').map(h => h.trim());
    const results = [];
    for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;
        const row = [];
        let inQuotes = false;
        let token = "";
        for (let j = 0; j < line.length; j++) {
            const char = line[j];
            if (char === '"' || char === "'") inQuotes = !inQuotes;
            else if (char === ',' && !inQuotes) { row.push(token.trim()); token = ""; }
            else token += char;
        }
        row.push(token.trim());
        const obj = {};
        headers.forEach((h, idx) => {
            let val = row[idx] !== undefined ? row[idx] : "";
            if (val.startsWith('"') && val.endsWith('"')) val = val.slice(1, -1);
            obj[h] = val;
        });
        results.push(obj);
    }
    return results;
}

const records = parseCSV(rawCsv);
if (records.length === 0) {
    dv.paragraph("No historical records found.");
    return;
}

// Multi-platform timeline construction
const rowsByDate = new Map();
for (const r of records) {
    if (!rowsByDate.has(r.date)) rowsByDate.set(r.date, []);
    rowsByDate.get(r.date).push(r);
}

const sortedDates = Array.from(rowsByDate.keys()).sort();
const activeHoldings = new Map(); // ticker -> current state
const tickerMap = new Map(); // ticker -> { name, history: Map(date -> record), latestVal, firstDate }

for (const d of sortedDates) {
    const dayRows = rowsByDate.get(d) || [];
    for (const r of dayRows) {
        const valPln = parseFloat(r.value_pln) || 0;
        const price = parseFloat(r.current_price) || 0;
        const pe = r.pe_ratio && !isNaN(parseFloat(r.pe_ratio)) ? parseFloat(r.pe_ratio) : null;
        const qty = parseFloat(r.quantity) || 0;
        const name = r.name || r.ticker;

        activeHoldings.set(r.ticker, {
            ticker: r.ticker,
            name: name,
            valPln: valPln,
            price: price,
            pe: pe,
            qty: qty,
            lastUpdatedDate: d
        });

        if (!tickerMap.has(r.ticker)) {
            tickerMap.set(r.ticker, {
                ticker: r.ticker,
                name: name,
                history: new Map(),
                latestVal: 0,
                firstDate: d
            });
        }
    }

    // Forward-fill each ticker's state for date d
    for (const [ticker, h] of activeHoldings.entries()) {
        const tObj = tickerMap.get(ticker);
        if (tObj.name === ticker && h.name !== ticker) tObj.name = h.name;
        tObj.history.set(d, { ...h });
        tObj.latestVal = h.valPln;
    }
}

const sortedTickers = Array.from(tickerMap.values()).sort((a, b) => b.latestVal - a.latestVal);

// Container UI
const container = this.container;
const uiWrapper = container.createDiv({ cls: "asset-history-filter-wrapper" });
uiWrapper.style.display = "flex";
uiWrapper.style.flexDirection = "column";
uiWrapper.style.gap = "12px";
uiWrapper.style.marginBottom = "16px";

const controlsRow = uiWrapper.createDiv({ cls: "controls-row" });
controlsRow.style.display = "flex";
controlsRow.style.flexWrap = "wrap";
controlsRow.style.gap = "12px";
controlsRow.style.alignItems = "center";

// 1. Asset select
const selectLabel = controlsRow.createEl("label", { text: "Asset / View: " });
selectLabel.style.fontWeight = "bold";

const assetSelect = controlsRow.createEl("select");
assetSelect.style.padding = "6px 10px";
assetSelect.style.borderRadius = "6px";
assetSelect.style.backgroundColor = "var(--background-secondary)";
assetSelect.style.color = "var(--text-normal)";
assetSelect.style.border = "1px solid var(--background-modifier-border)";
assetSelect.style.cursor = "pointer";

// Comparison presets
const presetGroup = assetSelect.createEl("optgroup", { attr: { label: "Preset Comparisons" } });
presetGroup.createEl("option", { value: "__TOP_5__", text: "🔥 Top 5 Assets" });
presetGroup.createEl("option", { value: "__TOP_10__", text: "🔥 Top 10 Assets" });
presetGroup.createEl("option", { value: "__ALL__", text: "🌐 All Assets" });
presetGroup.createEl("option", { value: "__CASH__", text: "💵 Cash Only" });

// Individual assets
const assetGroup = assetSelect.createEl("optgroup", { attr: { label: "Individual Assets (by valuation)" } });
for (const t of sortedTickers) {
    const opt = assetGroup.createEl("option", {
        value: t.ticker,
        text: `${t.name} [${t.ticker}] (${t.latestVal.toLocaleString('en-US', { maximumFractionDigits: 0 })} PLN)`
    });
}

// 2. Metric select
const metricLabel = controlsRow.createEl("label", { text: "Metric: " });
metricLabel.style.fontWeight = "bold";

const metricSelect = controlsRow.createEl("select");
metricSelect.style.padding = "6px 10px";
metricSelect.style.borderRadius = "6px";
metricSelect.style.backgroundColor = "var(--background-secondary)";
metricSelect.style.color = "var(--text-normal)";
metricSelect.style.border = "1px solid var(--background-modifier-border)";
metricSelect.style.cursor = "pointer";

metricSelect.createEl("option", { value: "valPln", text: "Value (PLN)" });
metricSelect.createEl("option", { value: "price", text: "Price" });
metricSelect.createEl("option", { value: "pe", text: "P/E Ratio" });
metricSelect.createEl("option", { value: "qty", text: "Quantity" });

// 3. Date Range Filter
const dateRangeLabel = controlsRow.createEl("label", { text: "Date Range: " });
dateRangeLabel.style.fontWeight = "bold";

const dateRangeSelect = controlsRow.createEl("select");
dateRangeSelect.style.padding = "6px 10px";
dateRangeSelect.style.borderRadius = "6px";
dateRangeSelect.style.backgroundColor = "var(--background-secondary)";
dateRangeSelect.style.color = "var(--text-normal)";
dateRangeSelect.style.border = "1px solid var(--background-modifier-border)";
dateRangeSelect.style.cursor = "pointer";

const opt3M = dateRangeSelect.createEl("option", { value: "3M", text: "📅 Last 3 Months (3M)" });
opt3M.selected = true; // DEFAULT: Last 3 Months
dateRangeSelect.createEl("option", { value: "1M", text: "📅 Last 1 Month (1M)" });
dateRangeSelect.createEl("option", { value: "6M", text: "📅 Last 6 Months (6M)" });
dateRangeSelect.createEl("option", { value: "YTD", text: "📅 Year to Date (YTD)" });
dateRangeSelect.createEl("option", { value: "1Y", text: "📅 Last 1 Year (1Y)" });
dateRangeSelect.createEl("option", { value: "ALL", text: "📅 All History (ALL)" });
dateRangeSelect.createEl("option", { value: "CUSTOM", text: "📅 Custom Range" });

// Custom date inputs container
const customDateBox = controlsRow.createDiv({ cls: "custom-date-box" });
customDateBox.style.display = "none";
customDateBox.style.alignItems = "center";
customDateBox.style.gap = "6px";

const dateFromInput = customDateBox.createEl("input", { attr: { type: "date" } });
dateFromInput.style.padding = "4px 8px";
dateFromInput.style.borderRadius = "4px";
dateFromInput.style.backgroundColor = "var(--background-secondary)";
dateFromInput.style.color = "var(--text-normal)";
dateFromInput.style.border = "1px solid var(--background-modifier-border)";

customDateBox.createSpan({ text: "➔" });

const dateToInput = customDateBox.createEl("input", { attr: { type: "date" } });
dateToInput.style.padding = "4px 8px";
dateToInput.style.borderRadius = "4px";
dateToInput.style.backgroundColor = "var(--background-secondary)";
dateToInput.style.color = "var(--text-normal)";
dateToInput.style.border = "1px solid var(--background-modifier-border)";

if (sortedDates.length > 0) {
    dateFromInput.value = sortedDates[0];
    dateToInput.value = sortedDates[sortedDates.length - 1];
}

// KPI / Stats Info Box
const infoBox = uiWrapper.createDiv({ cls: "asset-info-box" });
infoBox.style.padding = "10px 14px";
infoBox.style.borderRadius = "8px";
infoBox.style.backgroundColor = "var(--background-secondary-alt)";
infoBox.style.border = "1px solid var(--background-modifier-border)";
infoBox.style.fontSize = "0.9em";

// Chart box
const chartBox = container.createDiv({ cls: "asset-chart-box" });

const palette = [
    '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', 
    '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1',
    '#14b8a6', '#d946ef', '#eab308', '#64748b'
];

function getFilteredDates(rangePreset, customFrom, customTo) {
    if (sortedDates.length === 0) return [];
    const latestDateStr = sortedDates[sortedDates.length - 1];
    const latestDate = new Date(latestDateStr);

    let fromStr = "";
    let toStr = "";

    if (rangePreset === "ALL") {
        return sortedDates;
    } else if (rangePreset === "3M") {
        const d = new Date(latestDate);
        d.setMonth(d.getMonth() - 3);
        fromStr = d.toISOString().split('T')[0];
    } else if (rangePreset === "1M") {
        const d = new Date(latestDate);
        d.setMonth(d.getMonth() - 1);
        fromStr = d.toISOString().split('T')[0];
    } else if (rangePreset === "6M") {
        const d = new Date(latestDate);
        d.setMonth(d.getMonth() - 6);
        fromStr = d.toISOString().split('T')[0];
    } else if (rangePreset === "1Y") {
        const d = new Date(latestDate);
        d.setFullYear(d.getFullYear() - 1);
        fromStr = d.toISOString().split('T')[0];
    } else if (rangePreset === "YTD") {
        fromStr = `${latestDate.getFullYear()}-01-01`;
    } else if (rangePreset === "CUSTOM") {
        fromStr = customFrom || "";
        toStr = customTo || "";
    }

    const filtered = sortedDates.filter(d => {
        if (fromStr && d < fromStr) return false;
        if (toStr && d > toStr) return false;
        return true;
    });

    return filtered.length > 0 ? filtered : sortedDates;
}

function updateView() {
    const selected = assetSelect.value;
    const metric = metricSelect.value;
    const dateRange = dateRangeSelect.value;

    if (dateRange === "CUSTOM") {
        customDateBox.style.display = "inline-flex";
    } else {
        customDateBox.style.display = "none";
    }

    const currentDates = getFilteredDates(dateRange, dateFromInput.value, dateToInput.value);
    chartBox.empty();

    let datasets = [];
    let metricTitle = "Value (PLN)";
    let unit = " PLN";
    if (metric === "price") { metricTitle = "Price"; unit = ""; }
    else if (metric === "pe") { metricTitle = "P/E Ratio"; unit = ""; }
    else if (metric === "qty") { metricTitle = "Quantity"; unit = " units"; }

    const dateRangeText = currentDates.length > 0 ? `${currentDates[0]} ➔ ${currentDates[currentDates.length - 1]} (${currentDates.length} snapshots)` : 'No data';

    if (selected === "__TOP_5__" || selected === "__TOP_10__" || selected === "__ALL__" || selected === "__CASH__") {
        let targets = [];
        if (selected === "__TOP_5__") targets = sortedTickers.slice(0, 5);
        else if (selected === "__TOP_10__") targets = sortedTickers.slice(0, 10);
        else if (selected === "__ALL__") targets = sortedTickers;
        else if (selected === "__CASH__") targets = sortedTickers.filter(t => t.ticker.includes("CASH"));

        infoBox.innerHTML = `
            <div style="display: flex; flex-wrap: wrap; gap: 16px; justify-content: space-between; align-items: center;">
                <div><strong>Comparison Mode:</strong> <code>${targets.length}</code> positions for metric <strong>${metricTitle}</strong></div>
                <div><strong>📅 Date Range:</strong> <code>${dateRangeText}</code></div>
            </div>
        `;

        datasets = targets.map((t, idx) => {
            const data = currentDates.map(d => {
                const rec = t.history.get(d);
                if (!rec) return null;
                return rec[metric] !== undefined ? rec[metric] : null;
            });
            const color = palette[idx % palette.length];
            return {
                label: t.name.length > 22 ? t.name.substring(0, 22) + '...' : t.name,
                data: data,
                borderColor: color,
                backgroundColor: color,
                borderWidth: 2,
                tension: 0.2,
                spanGaps: true,
                pointRadius: 4
            };
        });
    } else {
        // Individual asset
        const t = tickerMap.get(selected);
        if (!t) return;

        const data = currentDates.map(d => {
            const rec = t.history.get(d);
            if (!rec) return null;
            return rec[metric] !== undefined ? rec[metric] : null;
        });

        // Calculate stats in selected date range
        const validRecords = currentDates.filter(d => t.history.has(d)).map(d => ({ date: d, ...t.history.get(d) }));
        const firstRec = validRecords[0];
        const lastRec = validRecords[validRecords.length - 1];
        
        let deltaValStr = "-";
        if (firstRec && lastRec && firstRec.valPln > 0) {
            const diff = lastRec.valPln - firstRec.valPln;
            const pct = (diff / firstRec.valPln) * 100;
            const sign = diff >= 0 ? "🟢 +" : "🔴 ";
            deltaValStr = `${sign}${diff.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} PLN (${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%)`;
        }

        infoBox.innerHTML = `
            <div style="display: flex; flex-wrap: wrap; gap: 16px; justify-content: space-between;">
                <div><strong>📌 Asset:</strong> ${t.name} (<code>${t.ticker}</code>)</div>
                <div><strong>📅 Date Range:</strong> <code>${dateRangeText}</code></div>
                <div><strong>💰 Current Value:</strong> <code>${(lastRec?.valPln || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} PLN</code></div>
                <div><strong>📈 Period Change:</strong> <code>${deltaValStr}</code></div>
                <div><strong>🏷️ Price:</strong> <code>${lastRec?.price ?? '-'}</code> | <strong>P/E:</strong> <code>${lastRec?.pe ?? '-'}</code> | <strong>Qty:</strong> <code>${lastRec?.qty ?? '-'}</code></div>
            </div>
        `;

        datasets = [{
            label: `${t.name} - ${metricTitle}`,
            data: data,
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.15)',
            borderWidth: 3,
            fill: true,
            tension: 0.2,
            spanGaps: true,
            pointRadius: 5,
            pointHoverRadius: 7,
            pointBackgroundColor: '#2563eb'
        }];
    }

    window.renderChart({
        type: 'line',
        data: {
            labels: currentDates,
            datasets: datasets
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        label: function(ctx) {
                            const val = ctx.raw;
                            if (val === null || val === undefined) return ctx.dataset.label + ': no data';
                            return ctx.dataset.label + ': ' + (typeof val === 'number' ? val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : val) + unit;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    ticks: {
                        callback: function(v) {
                            return typeof v === 'number' ? v.toLocaleString('en-US') + unit : v;
                        }
                    }
                }
            }
        }
    }, chartBox);
}

assetSelect.addEventListener("change", updateView);
metricSelect.addEventListener("change", updateView);
dateRangeSelect.addEventListener("change", updateView);
dateFromInput.addEventListener("change", updateView);
dateToInput.addEventListener("change", updateView);

// Initial render (defaults to 3M)
updateView();
```

---

## 🍰 Top Holdings Evolution Over Time

```dataviewjs
// Top holdings evolution stacked bar with multi-platform forward-fill
const rawCsv = await app.vault.adapter.read("10_Finance/History/portfolio.csv");

function parseCSV(text) {
    const lines = text.trim().split(/\r?\n/);
    if (lines.length < 2) return [];
    const headers = lines[0].split(',').map(h => h.trim());
    const results = [];
    for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;
        const row = [];
        let inQuotes = false;
        let token = "";
        for (let j = 0; j < line.length; j++) {
            const char = line[j];
            if (char === '"' || char === "'") inQuotes = !inQuotes;
            else if (char === ',' && !inQuotes) { row.push(token.trim()); token = ""; }
            else token += char;
        }
        row.push(token.trim());
        const obj = {};
        headers.forEach((h, idx) => {
            let val = row[idx] !== undefined ? row[idx] : "";
            if (val.startsWith('"') && val.endsWith('"')) val = val.slice(1, -1);
            obj[h] = val;
        });
        results.push(obj);
    }
    return results;
}

const records = parseCSV(rawCsv);
const rowsByDate = new Map();
for (const r of records) {
    if (!rowsByDate.has(r.date)) rowsByDate.set(r.date, []);
    rowsByDate.get(r.date).push(r);
}

const sortedDates = Array.from(rowsByDate.keys()).sort();
const activeHoldings = new Map(); // ticker -> { name, valPln }
const tickerCumulative = new Map();
const tickerNameMap = new Map();
const timelineSnapshots = new Map(); // date -> { ticker -> valPln }

for (const d of sortedDates) {
    const dayRows = rowsByDate.get(d) || [];
    for (const r of dayRows) {
        const val = parseFloat(r.value_pln) || 0;
        const name = r.name || r.ticker;
        activeHoldings.set(r.ticker, { name, valPln: val });
        tickerCumulative.set(r.ticker, (tickerCumulative.get(r.ticker) || 0) + val);
        if (!tickerNameMap.has(r.ticker) || tickerNameMap.get(r.ticker) === r.ticker) {
            tickerNameMap.set(r.ticker, name.length > 25 ? name.substring(0, 25) + '...' : name);
        }
    }

    const dateState = {};
    for (const [ticker, h] of activeHoldings.entries()) {
        dateState[ticker] = h.valPln;
    }
    timelineSnapshots.set(d, dateState);
}

// Select top 6 tickers by cumulative value, group remaining into "Other holdings"
const sortedTickers = Array.from(tickerCumulative.entries()).sort((a, b) => b[1] - a[1]);
const topTickers = sortedTickers.slice(0, 6).map(e => e[0]);
const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#94a3b8'];

const datasets = topTickers.map((ticker, idx) => {
    return {
        label: tickerNameMap.get(ticker) || ticker,
        data: sortedDates.map(d => Math.round((timelineSnapshots.get(d)[ticker] || 0) * 100) / 100),
        backgroundColor: colors[idx % colors.length]
    };
});

// Calculate "Other holdings"
const otherData = sortedDates.map(d => {
    const dateObj = timelineSnapshots.get(d) || {};
    let otherSum = 0;
    for (const [t, v] of Object.entries(dateObj)) {
        if (!topTickers.includes(t)) {
            otherSum += v;
        }
    }
    return Math.round(otherSum * 100) / 100;
});

datasets.push({
    label: 'Other holdings',
    data: otherData,
    backgroundColor: '#94a3b8'
});

window.renderChart({
    type: 'bar',
    data: {
        labels: sortedDates,
        datasets: datasets
    },
    options: {
        responsive: true,
        plugins: {
            legend: {
                position: 'bottom'
            },
            tooltip: {
                callbacks: {
                    label: function(ctx) {
                        return ctx.dataset.label + ': ' + Number(ctx.raw).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' PLN';
                    }
                }
            }
        },
        scales: {
            x: {
                stacked: true
            },
            y: {
                stacked: true,
                ticks: {
                    callback: function(val) {
                        return val.toLocaleString('en-US') + ' PLN';
                    }
                }
            }
        }
    }
}, this.container);
```

---

## 📋 Historical Snapshots Summary

```dataviewjs
// Render detailed snapshot comparison table with multi-platform forward-fill
const rawCsv = await app.vault.adapter.read("10_Finance/History/portfolio.csv");

function parseCSV(text) {
    const lines = text.trim().split(/\r?\n/);
    if (lines.length < 2) return [];
    const headers = lines[0].split(',').map(h => h.trim());
    const results = [];
    for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;
        const row = [];
        let inQuotes = false;
        let token = "";
        for (let j = 0; j < line.length; j++) {
            const char = line[j];
            if (char === '"' || char === "'") inQuotes = !inQuotes;
            else if (char === ',' && !inQuotes) { row.push(token.trim()); token = ""; }
            else token += char;
        }
        row.push(token.trim());
        const obj = {};
        headers.forEach((h, idx) => {
            let val = row[idx] !== undefined ? row[idx] : "";
            if (val.startsWith('"') && val.endsWith('"')) val = val.slice(1, -1);
            obj[h] = val;
        });
        results.push(obj);
    }
    return results;
}

const records = parseCSV(rawCsv);
const rowsByDate = new Map();
for (const r of records) {
    if (!rowsByDate.has(r.date)) rowsByDate.set(r.date, []);
    rowsByDate.get(r.date).push(r);
}

const assetPortfolioMap = new Map();
try {
    for (const p of dv.pages('"10_Finance/Assets"')) {
        const rawPort = (p.portfolio || "").toLowerCase().trim();
        let port = "Unallocated";
        if (rawPort === "safety net" || rawPort === "safety" || rawPort === "safety_net") port = "Safety net";
        else if (rawPort === "long term" || rawPort === "long_term") port = "Long term";
        else if (rawPort === "aggressive") port = "Aggressive";
        if (p.ticker) assetPortfolioMap.set(p.ticker.trim(), port);
        if (p.file && p.file.name) assetPortfolioMap.set(p.file.name.trim(), port);
    }
    for (const d of dv.pages('"20_Decisions"')) {
        if (d.ticker && !assetPortfolioMap.has(d.ticker.trim())) {
            const rawPort = (d.portfolio || "").toLowerCase().trim();
            let port = "Unallocated";
            if (rawPort === "safety net" || rawPort === "safety" || rawPort === "safety_net") port = "Safety net";
            else if (rawPort === "long term" || rawPort === "long_term") port = "Long term";
            else if (rawPort === "aggressive") port = "Aggressive";
            assetPortfolioMap.set(d.ticker.trim(), port);
        }
    }
} catch (e) {}

const sortedDates = Array.from(rowsByDate.keys()).sort();
const activeHoldings = new Map();
const snapshotEntries = [];

for (const d of sortedDates) {
    const dayRows = rowsByDate.get(d) || [];
    for (const r of dayRows) {
        const valPln = parseFloat(r.value_pln) || 0;
        const name = r.name || r.ticker;
        let port = (r.portfolio || "").trim();
        if (!port && assetPortfolioMap.has(r.ticker)) port = assetPortfolioMap.get(r.ticker);
        const portLower = port.toLowerCase();
        if (portLower === "safety net" || portLower === "safety" || portLower === "safety_net") port = "Safety net";
        else if (portLower === "long term" || portLower === "long_term") port = "Long term";
        else if (portLower === "aggressive") port = "Aggressive";
        else port = "Unallocated";

        activeHoldings.set(r.ticker, { name, valPln, port });
    }

    let totalVal = 0;
    let aggVal = 0;
    let ltVal = 0;
    let snVal = 0;
    let topAsset = { name: '', val: 0 };
    for (const h of activeHoldings.values()) {
        totalVal += h.valPln;
        if (h.port === "Aggressive") aggVal += h.valPln;
        else if (h.port === "Long term") ltVal += h.valPln;
        else if (h.port === "Safety net") snVal += h.valPln;

        if (h.valPln > topAsset.val) {
            topAsset = { name: h.name, val: h.valPln };
        }
    }

    snapshotEntries.push({
        date: d,
        totalValue: totalVal,
        aggressive: aggVal,
        longTerm: ltVal,
        safetyNet: snVal,
        count: activeHoldings.size,
        topAsset: topAsset
    });
}

// Reverse chronological order for summary display
const reversedEntries = [...snapshotEntries].reverse();

const tableRows = [];
for (let i = 0; i < reversedEntries.length; i++) {
    const cur = reversedEntries[i];
    const prev = i < reversedEntries.length - 1 ? reversedEntries[i + 1] : null;
    
    let changeStr = "-";
    let changePctStr = "-";
    
    if (prev && prev.totalValue > 0) {
        const diff = cur.totalValue - prev.totalValue;
        const pct = (diff / prev.totalValue) * 100;
        const sign = diff >= 0 ? "+" : "";
        changeStr = `${sign}${diff.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} PLN`;
        changePctStr = `${sign}${pct.toFixed(2)}%`;
    }
    
    tableRows.push([
        cur.date,
        `${cur.totalValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} PLN`,
        `${cur.longTerm.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} PLN`,
        `${cur.aggressive.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} PLN`,
        `${cur.safetyNet.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} PLN`,
        changeStr,
        changePctStr
    ]);
}

dv.table(
    ["Snapshot Date", "Total Value", "🏛️ Long Term", "🚀 Aggressive", "🛡️ Safety Net", "Change (PLN)", "Change (%)"],
    tableRows
);
```
