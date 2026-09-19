/**
 * Shared DataviewJS View: Native Interactive Canvas Financial Chart (Zero-Iframe, Zero-Dependency)
 *
 * Renders a responsive, interactive SVG/Canvas financial chart directly in Obsidian DOM.
 * Works 100% reliably with zero external plugins, zero iframes, and zero CSP blocking.
 *
 * Features:
 *   - Predefined range buttons: [ 1D | 5D | 1M | 3M | 6M | 1Y | 5Y | MAX ]
 *   - Interactive crosshair & hover price tooltips
 *   - Dynamic KPI calculations (Latest Price, Period Return %, High, Low)
 *   - Direct 1-click launch links to Stooq.pl and Yahoo Finance
 *
 * Parameters passed via `input`:
 *   - ticker: (Optional) Symbol or Stooq ticker (e.g. "aapl.us", "kgh", "v80a.de", "xauusd")
 *   - defaultRange: (Optional) "1D" | "5D" | "1M" | "3M" | "6M" | "1Y" | "5Y" | "MAX" (default: "1Y")
 *   - height: (Optional) Chart height in px (default: 300)
 */

const current = dv.current();
const root = dv.container || dv.el("div", "");

// 1. Resolve Symbol Mappings
let rawStooq = input?.ticker || current?.stooq_ticker || "";
let rawYahoo = current?.yahoo_ticker || "";
let rawTicker = current?.ticker || "";
let rawIsin = current?.isin || "";
let assetType = (current?.asset_type || "").toLowerCase();
let assetName = (current?.name || "").toLowerCase();

let querySymbol = "";
let stooqSymbol = rawStooq;

// 1. Known Specific ISIN & Ticker Overrides
if (rawIsin === "IE00BMVB5R75" || rawTicker === "V80A_IKZE" || stooqSymbol === "v80a.de") {
    querySymbol = "V80A.DE";
    stooqSymbol = "v80a.de";
} else if (rawIsin === "IE00BMVB5P51" || stooqSymbol === "v60a.de") {
    querySymbol = "V60A.DE";
    stooqSymbol = "v60a.de";
} else if (rawIsin === "NL0011683594" || stooqSymbol === "tdiv.nl") {
    querySymbol = "TDIV.AS";
    stooqSymbol = "tdiv.nl";
} else if (rawIsin === "IE00BK5BQT80" || stooqSymbol === "vwra.uk") {
    querySymbol = "VWRA.L";
    stooqSymbol = "vwra.uk";
} else if (rawIsin === "IE00B8GKDB10" || stooqSymbol === "vhyl.uk") {
    querySymbol = "VHYL.L";
    stooqSymbol = "vhyl.uk";
} else if (rawIsin === "IE00B43HR379" || stooqSymbol === "iuhc.uk") {
    querySymbol = "IUHC.L";
    stooqSymbol = "iuhc.uk";
} else if (rawIsin === "IE00BYXPSP02" || rawTicker.startsWith("IBTA") || stooqSymbol === "ibta.uk") {
    querySymbol = "IBTA.L";
    stooqSymbol = "ibta.uk";
} else if (rawIsin === "IE000YYE6WK5" || stooqSymbol === "dfen.de") {
    querySymbol = "DFEN.DE";
    stooqSymbol = "dfen.de";
}
// Gold / Commodities
else if (assetType === "commodities" || rawTicker.toUpperCase() === "GOLD" || assetName.includes("gold") || stooqSymbol === "xauusd") {
    querySymbol = "GC=F";
    stooqSymbol = "xauusd";
} else if (stooqSymbol === "xagusd" || assetName.includes("silver")) {
    querySymbol = "SI=F";
    stooqSymbol = "xagusd";
}
// Polish Retail Bonds (EDO, ROD)
else if (assetType === "bond" || rawTicker.startsWith("EDO") || rawTicker.startsWith("ROD") || stooqSymbol === "10ply.b") {
    querySymbol = "^TNX";
    stooqSymbol = "10ply.b";
}
// Polish GPW Equities & ETFs
else if (rawIsin.startsWith("PL") || rawYahoo.endsWith(".WA") || (stooqSymbol && !stooqSymbol.includes("."))) {
    let base = rawYahoo.endsWith(".WA") ? rawYahoo.replace(".WA", "") : (stooqSymbol || rawTicker);
    querySymbol = `${base.toUpperCase()}.WA`;
    stooqSymbol = base.toLowerCase();
}
// European UCITS ETFs / Equities
else if (rawYahoo.endsWith(".DE") || (stooqSymbol && stooqSymbol.endsWith(".de"))) {
    let base = rawYahoo.endsWith(".DE") ? rawYahoo.replace(".DE", "") : stooqSymbol.replace(".de", "");
    querySymbol = `${base.toUpperCase()}.DE`;
    stooqSymbol = `${base.toLowerCase()}.de`;
} else if (rawYahoo.endsWith(".L") || rawYahoo.endsWith(".LN") || (stooqSymbol && stooqSymbol.endsWith(".uk"))) {
    let base = rawYahoo.replace(/\.LN?$/, "").replace(/\.uk$/i, "");
    if (!base && stooqSymbol) base = stooqSymbol.replace(".uk", "");
    querySymbol = `${base.toUpperCase()}.L`;
    stooqSymbol = `${base.toLowerCase()}.uk`;
} else if (rawYahoo.endsWith(".AS") || (stooqSymbol && stooqSymbol.endsWith(".nl"))) {
    let base = rawYahoo.endsWith(".AS") ? rawYahoo.replace(".AS", "") : stooqSymbol.replace(".nl", "");
    querySymbol = `${base.toUpperCase()}.AS`;
    stooqSymbol = `${base.toLowerCase()}.nl`;
}
// US Equities & ETFs
else if (rawYahoo && !rawYahoo.includes(".")) {
    querySymbol = rawYahoo.toUpperCase();
    stooqSymbol = `${rawYahoo.toLowerCase()}.us`;
} else if (stooqSymbol && stooqSymbol.endsWith(".us")) {
    let base = stooqSymbol.replace(".us", "");
    querySymbol = base.toUpperCase();
} else if (rawTicker && !rawTicker.includes(".")) {
    querySymbol = rawTicker.toUpperCase();
    stooqSymbol = `${rawTicker.toLowerCase()}.us`;
} else if (rawYahoo) {
    querySymbol = rawYahoo;
}

if (!querySymbol) {
    dv.paragraph("> [!NOTE] ℹ️ **No Market Chart Available:** Asset is unquoted cash, real estate, or missing market ticker.");
    return;
}

// Range definitions
const rangeOptions = [
    { label: "1D", range: "1d", interval: "5m" },
    { label: "5D", range: "5d", interval: "15m" },
    { label: "1M", range: "1mo", interval: "1d" },
    { label: "3M", range: "3mo", interval: "1d" },
    { label: "6M", range: "6mo", interval: "1d" },
    { label: "1Y", range: "1y", interval: "1d" },
    { label: "5Y", range: "5y", interval: "1wk" },
    { label: "MAX", range: "max", interval: "1mo" }
];

let currentRange = input?.defaultRange || "1Y";
const chartHeight = input?.height || 280;

// Outer Card Container
const card = root.createDiv({ cls: "native-price-chart-card" });
card.style.border = "1px solid var(--background-modifier-border)";
card.style.borderRadius = "8px";
card.style.backgroundColor = "var(--background-secondary)";
card.style.padding = "14px 18px";
card.style.margin = "14px 0";
card.style.boxShadow = "0 2px 10px rgba(0,0,0,0.1)";

// Top Bar (Controls + External Links)
const topBar = card.createDiv();
topBar.style.display = "flex";
topBar.style.justifyContent = "space-between";
topBar.style.alignItems = "center";
topBar.style.flexWrap = "wrap";
topBar.style.gap = "10px";
topBar.style.paddingBottom = "10px";
topBar.style.borderBottom = "1px solid var(--background-modifier-border)";

// Range Button Group
const btnGroup = topBar.createDiv();
btnGroup.style.display = "inline-flex";
btnGroup.style.gap = "4px";
btnGroup.style.backgroundColor = "var(--background-primary)";
btnGroup.style.padding = "3px";
btnGroup.style.borderRadius = "6px";
btnGroup.style.border = "1px solid var(--background-modifier-border)";

// Quick Companion Links
const linksDiv = topBar.createDiv();
linksDiv.style.display = "flex";
linksDiv.style.alignItems = "center";
linksDiv.style.gap = "8px";
linksDiv.style.fontSize = "0.82em";
linksDiv.innerHTML = `
    ${stooqSymbol ? `<a href="https://stooq.pl/q/?s=${stooqSymbol}" target="_blank" style="color: var(--text-accent); text-decoration: none; font-weight: 500;">🇵🇱 Stooq (${stooqSymbol.toUpperCase()})</a><span style="color: var(--text-faint);">•</span>` : ''}
    <a href="https://finance.yahoo.com/quote/${querySymbol}" target="_blank" style="color: var(--text-muted); text-decoration: none;">🌐 Yahoo (${querySymbol})</a>
`;

// KPI Statistics Strip
const kpiStrip = card.createDiv();
kpiStrip.style.display = "flex";
kpiStrip.style.justifyContent = "space-between";
kpiStrip.style.alignItems = "baseline";
kpiStrip.style.flexWrap = "wrap";
kpiStrip.style.margin = "10px 0 6px 0";

// Chart Wrapper
const chartWrapper = card.createDiv();
chartWrapper.style.width = "100%";
chartWrapper.style.height = `${chartHeight}px`;
chartWrapper.style.position = "relative";
chartWrapper.style.cursor = "crosshair";

// Data Fetcher
async function fetchHistoricalData(symbol, range, interval) {
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?range=${range}&interval=${interval}`;
    try {
        let text = "";
        if (typeof requestUrl === "function") {
            const resp = await requestUrl({ url: url, headers: { "User-Agent": "Mozilla/5.0" } });
            text = resp.text;
        } else {
            const resp = await fetch(url);
            text = await resp.text();
        }
        const json = JSON.parse(text);
        const result = json.chart?.result?.[0];
        if (!result) return null;

        const timestamps = result.timestamp || [];
        const quote = result.indicators?.quote?.[0] || {};
        const closes = quote.close || [];
        const currency = result.meta?.currency || "";

        const points = [];
        for (let i = 0; i < timestamps.length; i++) {
            if (closes[i] !== null && closes[i] !== undefined && !isNaN(closes[i])) {
                const dt = new Date(timestamps[i] * 1000);
                const isIntraday = (range === "1d" || range === "5d");
                const label = isIntraday 
                    ? `${dt.toLocaleDateString([], {month: 'numeric', day: 'numeric'})} ${dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
                    : dt.toISOString().split("T")[0];
                points.push({
                    date: label,
                    timestamp: timestamps[i],
                    price: closes[i]
                });
            }
        }
        return { points, currency, meta: result.meta };
    } catch (e) {
        console.error("Failed to fetch chart data:", e);
        return null;
    }
}

// Native Canvas Drawing with Interactive Crosshair & Tooltips
function drawInteractiveCanvas(wrapper, points, currency) {
    wrapper.empty();

    const canvas = wrapper.createEl("canvas");
    const dpr = window.devicePixelRatio || 1;
    const w = wrapper.clientWidth || 600;
    const h = chartHeight;

    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;

    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);

    const prices = points.map(p => p.price);
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const priceRange = (maxPrice - minPrice) || 1;

    const firstPrice = prices[0];
    const lastPrice = prices[prices.length - 1];
    const isPositive = lastPrice >= firstPrice;
    const mainColor = isPositive ? "#10b981" : "#ef4444";

    const padLeft = 10;
    const padRight = 60;
    const padTop = 15;
    const padBottom = 25;
    const plotW = w - padLeft - padRight;
    const plotH = h - padTop - padBottom;

    function getX(idx) {
        return padLeft + (idx / (points.length - 1)) * plotW;
    }

    function getY(val) {
        return padTop + plotH - ((val - minPrice) / priceRange) * plotH;
    }

    // Tooltip overlay element
    const tooltip = wrapper.createDiv();
    tooltip.style.position = "absolute";
    tooltip.style.display = "none";
    tooltip.style.backgroundColor = "var(--background-primary)";
    tooltip.style.color = "var(--text-normal)";
    tooltip.style.border = `1px solid ${mainColor}`;
    tooltip.style.borderRadius = "5px";
    tooltip.style.padding = "4px 8px";
    tooltip.style.fontSize = "0.78em";
    tooltip.style.pointerEvents = "none";
    tooltip.style.boxShadow = "0 2px 8px rgba(0,0,0,0.2)";
    tooltip.style.zIndex = "10";

    function render(hoverIdx = -1) {
        ctx.clearRect(0, 0, w, h);

        // 1. Draw Grid Lines & Price Ticks
        ctx.strokeStyle = "rgba(150, 150, 150, 0.12)";
        ctx.lineWidth = 1;
        ctx.fillStyle = "rgba(150, 150, 150, 0.7)";
        ctx.font = "10px sans-serif";
        ctx.textAlign = "left";

        const gridSteps = 4;
        for (let i = 0; i <= gridSteps; i++) {
            const yVal = minPrice + (i / gridSteps) * priceRange;
            const yPx = getY(yVal);
            
            ctx.beginPath();
            ctx.moveTo(padLeft, yPx);
            ctx.lineTo(w - padRight + 5, yPx);
            ctx.stroke();

            ctx.fillText(yVal.toFixed(2), w - padRight + 8, yPx + 3);
        }

        // 2. Draw Price Area Gradient
        const grad = ctx.createLinearGradient(0, padTop, 0, padTop + plotH);
        grad.addColorStop(0, isPositive ? "rgba(16, 185, 129, 0.22)" : "rgba(239, 68, 68, 0.22)");
        grad.addColorStop(1, "rgba(0, 0, 0, 0)");

        ctx.beginPath();
        for (let i = 0; i < points.length; i++) {
            const px = getX(i);
            const py = getY(prices[i]);
            if (i === 0) ctx.moveTo(px, py);
            else ctx.lineTo(px, py);
        }
        ctx.lineTo(getX(points.length - 1), padTop + plotH);
        ctx.lineTo(getX(0), padTop + plotH);
        ctx.closePath();
        ctx.fillStyle = grad;
        ctx.fill();

        // 3. Draw Main Price Line
        ctx.beginPath();
        for (let i = 0; i < points.length; i++) {
            const px = getX(i);
            const py = getY(prices[i]);
            if (i === 0) ctx.moveTo(px, py);
            else ctx.lineTo(px, py);
        }
        ctx.strokeStyle = mainColor;
        ctx.lineWidth = 2.2;
        ctx.stroke();

        // 4. Draw Date Labels at bottom
        ctx.fillStyle = "rgba(150, 150, 150, 0.65)";
        ctx.font = "9.5px sans-serif";
        const dateIdxs = [0, Math.floor(points.length / 2), points.length - 1];
        dateIdxs.forEach((idx, i) => {
            const px = getX(idx);
            ctx.textAlign = i === 0 ? "left" : (i === 2 ? "right" : "center");
            ctx.fillText(points[idx].date, px, h - 6);
        });

        // 5. Draw Crosshair & Hover Point
        if (hoverIdx >= 0 && hoverIdx < points.length) {
            const hx = getX(hoverIdx);
            const hy = getY(prices[hoverIdx]);

            // Vertical dashed line
            ctx.beginPath();
            ctx.setLineDash([3, 3]);
            ctx.strokeStyle = "rgba(200, 200, 200, 0.5)";
            ctx.moveTo(hx, padTop);
            ctx.lineTo(hx, padTop + plotH);
            ctx.stroke();
            ctx.setLineDash([]);

            // Dot
            ctx.beginPath();
            ctx.arc(hx, hy, 5, 0, Math.PI * 2);
            ctx.fillStyle = mainColor;
            ctx.fill();
            ctx.strokeStyle = "#ffffff";
            ctx.lineWidth = 1.8;
            ctx.stroke();
        }
    }

    render(-1);

    // Mouse Move Interactive Listener
    wrapper.onmousemove = (e) => {
        const rect = canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const relativeX = mouseX - padLeft;

        if (relativeX < 0 || relativeX > plotW) {
            tooltip.style.display = "none";
            render(-1);
            return;
        }

        const idx = Math.round((relativeX / plotW) * (points.length - 1));
        if (idx >= 0 && idx < points.length) {
            const pt = points[idx];
            const px = getX(idx);
            const py = getY(pt.price);

            render(idx);

            tooltip.style.display = "block";
            tooltip.innerHTML = `<strong>${pt.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}</strong><br><span style="color: var(--text-muted); font-size: 0.9em;">${pt.date}</span>`;
            
            const tooltipX = Math.min(Math.max(px - 40, 10), w - 130);
            const tooltipY = Math.max(py - 48, 8);
            tooltip.style.left = `${tooltipX}px`;
            tooltip.style.top = `${tooltipY}px`;
        }
    };

    wrapper.onmouseleave = () => {
        tooltip.style.display = "none";
        render(-1);
    };
}

const buttons = {};

async function loadRangeData(rangeLabel) {
    currentRange = rangeLabel;

    rangeOptions.forEach(opt => {
        const btn = buttons[opt.label];
        if (btn) {
            if (opt.label === rangeLabel) {
                btn.style.backgroundColor = "var(--interactive-accent)";
                btn.style.color = "var(--text-on-accent)";
                btn.style.fontWeight = "bold";
            } else {
                btn.style.backgroundColor = "transparent";
                btn.style.color = "var(--text-muted)";
                btn.style.fontWeight = "normal";
            }
        }
    });

    chartWrapper.empty();
    kpiStrip.empty();

    const loadingEl = chartWrapper.createDiv();
    loadingEl.style.padding = "50px";
    loadingEl.style.textAlign = "center";
    loadingEl.style.color = "var(--text-muted)";
    loadingEl.textContent = `⏳ Loading live data for ${querySymbol} (${rangeLabel})...`;

    const rangeConfig = rangeOptions.find(o => o.label === rangeLabel) || rangeOptions[5];
    const dataRes = await fetchHistoricalData(querySymbol, rangeConfig.range, rangeConfig.interval);

    if (!dataRes || dataRes.points.length === 0) {
        chartWrapper.empty();
        chartWrapper.createEl("p", { text: `⚠️ Unable to load historical data for ${querySymbol}. Please verify symbol or connection.` });
        return;
    }

    const points = dataRes.points;
    const currency = dataRes.currency || "";
    const firstP = points[0].price;
    const lastP = points[points.length - 1].price;
    const diff = lastP - firstP;
    const diffPct = firstP > 0 ? (diff / firstP) * 100 : 0;
    const isUp = diff >= 0;
    const sign = isUp ? "🟢 +" : "🔴 ";
    const trendColor = isUp ? "#10b981" : "#ef4444";

    const allPrices = points.map(p => p.price);
    const lowP = Math.min(...allPrices);
    const highP = Math.max(...allPrices);

    kpiStrip.innerHTML = `
        <div style="display: flex; gap: 10px; align-items: baseline;">
            <span style="font-size: 1.35em; font-weight: 700; color: var(--text-normal);">${lastP.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}</span>
            <span style="font-size: 0.95em; font-weight: 600; color: ${trendColor};">${sign}${diff.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency} (${isUp ? '+' : ''}${diffPct.toFixed(2)}%)</span>
        </div>
        <div style="font-size: 0.82em; color: var(--text-muted);">
            Range Low: <strong style="color: var(--text-normal);">${lowP.toFixed(2)}</strong> · High: <strong style="color: var(--text-normal);">${highP.toFixed(2)}</strong>
        </div>
    `;

    drawInteractiveCanvas(chartWrapper, points, currency);
}

// Generate Range Buttons
rangeOptions.forEach(opt => {
    const btn = btnGroup.createEl("button", { text: opt.label });
    btn.style.border = "none";
    btn.style.borderRadius = "4px";
    btn.style.padding = "2px 8px";
    btn.style.fontSize = "0.78em";
    btn.style.cursor = "pointer";
    btn.style.transition = "all 0.15s ease";
    btn.addEventListener("click", () => loadRangeData(opt.label));
    buttons[opt.label] = btn;
});

// Initial Run
loadRangeData(currentRange);
