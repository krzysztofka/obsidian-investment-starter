---
aliases:
  - "Long Term Portfolio"
  - "Long_term_portfolio"
---
# 🏛️ Long Term Portfolio

> 🧭 **Portfolio Views:** [[Overview|📊 Consolidated Overview]] · [[Safety_portfolio|🛡️ Safety Net]] · [[Long_term_portfolio|🏛️ Long Term]] · [[Aggressive_portfolio|🚀 Aggressive]]

```dataviewjs
// 1. Fetch all pages from Assets directory
let allPages = dv.pages('"10_Finance/Assets"');

let totalGlobalValue = 0;
let portfolioValue = 0;
let positionCount = 0;

let classData = {
    "Equities": 0,
    "Bonds / Obligations": 0,
    "Real Estate": 0,
    "Commodities": 0,
    "Cash": 0
};
let sectorData = {};
let myPages = [];

// Filter function for Long Term portfolio
function isLongTermPortfolio(p) {
    let port = (p.portfolio || "").toLowerCase().trim();
    return port === "long term" || port === "long_term";
}

for (let p of allPages) {
    let val = p.value_pln || 0;
    totalGlobalValue += val;

    if (!isLongTermPortfolio(p)) continue;
    if (val <= 0 && !p.name && !p.ticker) continue;

    myPages.push(p);
    portfolioValue += val;
    positionCount++;

    // --- Asset Class Breakdown ---
    let alloc = (p.file && p.file.frontmatter && p.file.frontmatter.asset_allocation) || p.asset_allocation;
    if (typeof alloc === 'string') {
        try { alloc = JSON.parse(alloc); } catch(e) {}
    }

    if (alloc && typeof alloc === 'object') {
        let eq = (alloc.equity || alloc.equities || 0) / 100;
        let bd = (alloc.bonds || alloc.bond || alloc.fixed_income || alloc.obligations || 0) / 100;
        let re = (alloc.real_estate || alloc.reits || 0) / 100;
        let cm = (alloc.commodities || alloc.commodity || alloc.gold || 0) / 100;
        let cs = (alloc.cash || 0) / 100;
        
        let sumAlloc = eq + bd + re + cm + cs;
        if (sumAlloc > 0) {
            classData["Equities"] += val * eq;
            classData["Bonds / Obligations"] += val * bd;
            classData["Real Estate"] += val * re;
            classData["Commodities"] += val * cm;
            classData["Cash"] += val * cs;
        } else {
            classData["Equities"] += val;
        }
    } else {
        let atype = (p.asset_type || "").toLowerCase();
        let sec = (p.dominant_sector || p.industry || "").toLowerCase();
        let name = (p.name || "").toLowerCase();
        let ticker = (p.ticker || "").toLowerCase();

        if (atype === "cash" || ticker.includes("cash") || sec === "cash") {
            classData["Cash"] += val;
        } else if (atype.includes("real estate") || sec.includes("real estate") || atype.includes("reit")) {
            classData["Real Estate"] += val;
        } else if (atype.includes("gold") || sec.includes("precious metals") || atype.includes("commodity") || ticker === "gold") {
            classData["Commodities"] += val;
        } else if (sec === "sovereign" || name.includes("bond") || name.includes("treasury") || atype.includes("bond")) {
            classData["Bonds / Obligations"] += val;
        } else {
            classData["Equities"] += val;
        }
    }

    // --- Sector Breakdown ---
    let secName = p.dominant_sector || p.industry || "Diversified";
    if (val > 0) {
        sectorData[secName] = (sectorData[secName] || 0) + val;
    }
}

// Global share
let globalSharePct = totalGlobalValue > 0 ? ((portfolioValue / totalGlobalValue) * 100).toFixed(1) : "0.0";
let formattedVal = portfolioValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

dv.paragraph(`## 💰 Long Term Value: ${formattedVal} PLN`);
dv.paragraph(`> [!INFO] 🏛️ **Strategy Summary:** Broad-market index ETFs, sovereign bond ETFs, real estate, and physical gold.  
> Currently representing **${globalSharePct}%** of total portfolio across **${positionCount} positions**.`);

// Alert Banner
await dv.view("99_System/Views/alert_banner", { pages: myPages, portfolioName: "Long Term" });

// Build Horizontal Flex Container for Charts
const mainContainer = this.container;
const flexWrapper = document.createElement("div");
flexWrapper.style.display = "flex";
flexWrapper.style.flexDirection = "row";
flexWrapper.style.flexWrap = "wrap";
flexWrapper.style.gap = "24px";
flexWrapper.style.justifyContent = "space-between";
flexWrapper.style.alignItems = "flex-start";
flexWrapper.style.margin = "20px 0";

const col1 = document.createElement("div");
col1.style.flex = "1 1 calc(50% - 16px)";
col1.style.minWidth = "320px";
col1.style.boxSizing = "border-box";

const col2 = document.createElement("div");
col2.style.flex = "1 1 calc(50% - 16px)";
col2.style.minWidth = "320px";
col2.style.boxSizing = "border-box";

flexWrapper.appendChild(col1);
flexWrapper.appendChild(col2);
mainContainer.appendChild(flexWrapper);

function createTable(headers, rows) {
    const table = document.createElement("table");
    table.className = "dataview table-view-table";
    table.style.width = "100%";
    table.style.marginTop = "16px";
    
    const thead = document.createElement("thead");
    const trHead = document.createElement("tr");
    headers.forEach((h, idx) => {
        const th = document.createElement("th");
        th.textContent = h;
        if (idx > 0) th.style.textAlign = "right";
        trHead.appendChild(th);
    });
    thead.appendChild(trHead);
    table.appendChild(thead);
    
    const tbody = document.createElement("tbody");
    rows.forEach(r => {
        const tr = document.createElement("tr");
        r.forEach((cell, idx) => {
            const td = document.createElement("td");
            td.textContent = cell;
            if (idx > 0) td.style.textAlign = "right";
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    return table;
}

// Column 1: Asset Class Allocation
const h1 = document.createElement("h3");
h1.textContent = "🏛️ Asset Class Allocation";
h1.style.marginTop = "0";
col1.appendChild(h1);

let classEntries = Object.entries(classData).filter(e => e[1] > 0);
let classLabels = classEntries.map(e => e[0]);
let classPercentages = classEntries.map(e => Number(((e[1] / (portfolioValue || 1)) * 100).toFixed(1)));

const chart1Container = document.createElement("div");
chart1Container.style.maxWidth = "360px";
chart1Container.style.margin = "0 auto";
col1.appendChild(chart1Container);

if (typeof window.renderChart === 'function') {
    window.renderChart({
        type: 'doughnut',
        data: {
            labels: classLabels,
            datasets: [{
                label: 'Asset Class Allocation (%)',
                data: classPercentages,
                backgroundColor: ['#2ecc71', '#3498db', '#e67e22', '#f1c40f', '#9b59b6'],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    }, chart1Container);
}

let classTableRows = classEntries.map(e => [
    e[0],
    ((e[1] / (portfolioValue || 1)) * 100).toFixed(1) + " %",
    e[1].toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " PLN"
]);
col1.appendChild(createTable(["Asset Class", "Allocation (%)", "Value (PLN)"], classTableRows));

// Column 2: Sector Allocation
const h2 = document.createElement("h3");
h2.textContent = "🌐 Sector Allocation";
h2.style.marginTop = "0";
col2.appendChild(h2);

let sortedSectors = Object.entries(sectorData).sort((a, b) => b[1] - a[1]);
let sectorLabels = sortedSectors.map(entry => entry[0]);
let sectorPercentages = sortedSectors.map(entry => Number(((entry[1] / (portfolioValue || 1)) * 100).toFixed(1)));

const chart2Container = document.createElement("div");
chart2Container.style.maxWidth = "360px";
chart2Container.style.margin = "0 auto";
col2.appendChild(chart2Container);

if (typeof window.renderChart === 'function') {
    window.renderChart({
        type: 'pie',
        data: {
            labels: sectorLabels,
            datasets: [{
                label: 'Sector Allocation (%)',
                data: sectorPercentages,
                backgroundColor: [
                    '#3498db', '#2ecc71', '#e74c3c', '#f1c40f', 
                    '#9b59b6', '#e67e22', '#1abc9c', '#34495e', '#16a085'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    }, chart2Container);
}

let sectorTableRows = sortedSectors.map(e => [
    e[0],
    ((e[1] / (portfolioValue || 1)) * 100).toFixed(1) + " %",
    e[1].toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " PLN"
]);
col2.appendChild(createTable(["Sector", "Allocation (%)", "Value (PLN)"], sectorTableRows));
```

## 💼 Long Term Holdings

```dataviewjs
function isLongTermPortfolio(p) {
    let port = (p.portfolio || "").toLowerCase().trim();
    return port === "long term" || port === "long_term";
}

let assets = dv.pages('"10_Finance/Assets"')
    .filter(p => isLongTermPortfolio(p) && (p.value_pln > 0 || p.name || p.ticker))
    .sort(p => p.value_pln, 'desc');

let subTotal = 0;
for (let p of assets) {
    subTotal += (p.value_pln || 0);
}

let rows = assets.map(p => {
    let returnStr = "-";
    if (p.avg_price && p.current_price) {
        let ret = ((p.current_price - p.avg_price) / p.avg_price) * 100;
        let sign = ret >= 0 ? "+" : "";
        returnStr = `${sign}${ret.toFixed(1)}%`;
    }

    let qtyStr = p.quantity !== undefined && p.quantity !== null ? p.quantity.toLocaleString('en-US') : "-";
    let avgPriceStr = p.avg_price ? `${p.avg_price.toLocaleString('en-US')} ${p.currency || ""}` : "-";
    let curPriceStr = p.current_price ? `${p.current_price.toLocaleString('en-US')} ${p.currency || ""}` : "-";
    let valStr = p.value_pln !== undefined && p.value_pln !== null
        ? p.value_pln.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " PLN"
        : "-";
    
    let sharePct = subTotal > 0 && p.value_pln ? ((p.value_pln / subTotal) * 100).toFixed(1) + " %" : "-";
    let platformStr = p.platform && p.platform !== "None" ? dv.fileLink(p.platform, false, p.platform) : (p.platform || "-");

    // Asset allocation string
    let alloc = (p.file && p.file.frontmatter && p.file.frontmatter.asset_allocation) || p.asset_allocation;
    if (typeof alloc === 'string') {
        try { alloc = JSON.parse(alloc); } catch(e) {}
    }
    let classStr = "-";
    if (alloc && typeof alloc === 'object') {
        let parts = [];
        if (alloc.equity || alloc.equities) parts.push(`${alloc.equity || alloc.equities}% Eq`);
        if (alloc.bonds || alloc.bond || alloc.fixed_income || alloc.obligations) parts.push(`${alloc.bonds || alloc.bond || alloc.fixed_income || alloc.obligations}% Bd`);
        if (alloc.real_estate || alloc.reits) parts.push(`${alloc.real_estate || alloc.reits}% RE`);
        if (alloc.commodities || alloc.commodity || alloc.gold) parts.push(`${alloc.commodities || alloc.commodity || alloc.gold}% Comm`);
        if (alloc.cash) parts.push(`${alloc.cash}% Cash`);
        if (parts.length > 0) classStr = parts.join(" / ");
    }

    return [
        dv.fileLink(p.file.path, false, p.name || p.ticker),
        platformStr,
        classStr,
        p.dominant_sector || p.industry || "-",
        qtyStr,
        avgPriceStr,
        curPriceStr,
        valStr,
        sharePct,
        returnStr
    ];
});

dv.table(
    ["Name", "Platform", "Asset Class", "Industry / Sector", "Qty", "Avg Price", "Current Price", "Value (PLN)", "Share (%)", "Return %"],
    rows
);
```

---

## 📋 Open Decisions & Pending Orders

```dataviewjs
await dv.view("99_System/Views/open_decisions", { portfolio: "Long term" });
```
