---
type: health_dashboard
title: Integrations Health & Connectivity Diagnostics
last_checked: "2026-10-19 20:36:12"
status_summary: "8/10 Passed, 2 Warnings"
total_probed: 10
passed_count: 8
warn_count: 2
failed_count: 0
all_ok: true
tags:
  - system
  - diagnostics
  - health
---

# 🩺 Integrations Health & Connectivity Diagnostics

A real-time diagnostic dashboard monitoring external data providers, financial APIs, broker endpoints, and web scrapers used across the Investment Second Brain.

> 🧭 **Related Dashboards:** [[Welcome|🏠 Welcome]] · [[Overview|📊 Main Overview]] · [[Alerts|🚨 Active Alerts]] · [[10_Finance/Macro|🌐 Macro Dashboard]]

---

## 🚦 Connectivity Status Overview


> [!WARNING] ⚠️ **Configuration Warnings Detected**
> **8 service(s)** passed, but **2 optional service(s)** have warnings (unconfigured API keys or optional libraries). Core functionality is intact.


**Last Diagnostic Scan:** `2026-10-19 20:36:12` · **Overall Result:** `8/10 Passed, 2 Warnings`

---

## ⚡ Manual Health Re-Scan

Click the button below to re-run external connectivity probes and update this dashboard:

```dataviewjs
const btn = dv.el("button", "🔄 Re-run Connectivity Diagnostics (--health)", {
    cls: "mod-cta",
    attr: { style: "padding: 8px 16px; font-weight: 600; cursor: pointer; border-radius: 6px;" }
});

btn.onclick = async () => {
    let childProcess = null;
    try {
        if (typeof require !== "undefined") childProcess = require("child_process");
        else if (window && window.require) childProcess = window.require("child_process");
    } catch (e) {}

    let vaultPath = ".";
    try {
        if (app && app.vault && app.vault.adapter && app.vault.adapter.basePath) {
            vaultPath = app.vault.adapter.basePath;
        }
    } catch (e) {}

    if (childProcess && (childProcess.spawn || childProcess.exec)) {
        btn.disabled = true;
        btn.textContent = "⏳ Running diagnostics...";
        childProcess.exec("python run.py --health", { cwd: vaultPath }, (err, stdout, stderr) => {
            btn.disabled = false;
            btn.textContent = "🔄 Re-run Connectivity Diagnostics (--health)";
            if (err) {
                new Notice("❌ Health check completed with errors. Refreshing page...");
            } else {
                new Notice("✅ Health check completed successfully! Refreshing page...");
            }
        });
    } else {
        if (navigator.clipboard) {
            navigator.clipboard.writeText("python run.py --health");
            new Notice("📋 Copied 'python run.py --health' to clipboard!");
        }
    }
};
```

---

## 📊 External Integrations Diagnostic Matrix

| Service | Category | Auth / Requirement | Status | Latency | Target Endpoint / Probe | Details / Status Message |
| :--- | :--- | :--- | :---: | :---: | :--- | :--- |
| **Yahoo Finance** | `Market Data` | Public / Free | ✅ `OK` | 2268 ms | `query1.finance.yahoo.com (Ticker: SPY)` | Success: retrieved SPY close ($766.96) |
| **National Bank of Poland (NBP)** | `Macro / FX Rates` | Public / Free | ✅ `OK` | 581 ms | `api.nbp.pl/api/exchangerates/tables/a` | HTTP 200: Active FX Table A fixing (203/A/NBP/2026) |
| **Eurostat** | `Macro / Sovereign Yields` | Public / Free | ✅ `OK` | 671 ms | `ec.europa.eu/eurostat/api/dissemination (10Y Yield PL)` | HTTP 200: Valid JSON dataset received (data present) |
| **Stooq** | `Market Quotes & Charts` | Public / Free | ✅ `OK` | 646 ms | `stooq.pl/q/d/l/?s=aapl.us&i=d` | HTTP 200: CSV quote data stream accessible |
| **JustETF** | `ETF Metadata & Scraper` | Public / Free | ✅ `OK` | 991 ms | `justetf.com/en/etf-profile.html (ISIN: IE00B4L5Y983)` | HTTP 200: Profile page reachable (ETF metadata detected) |
| **Finnhub** | `Market Intelligence / SEC` | API Key in .env (`FINNHUB_API_KEY`) | ⚠️ `WARN` | — | `finnhub.io` | FINNHUB_API_KEY not configured (placeholder detected in .env) |
| **OpenBB Platform** | `Local Quantitative SDK` | Optional Python Library | ⚠️ `WARN` | 0 ms | `openbb python package` | OpenBB package not installed (optional, yfinance fallback active) |
| **iShares (BlackRock)** | `ETF Issuer Scraper` | Public / Free | ✅ `OK` | 2005 ms | `ishares.com/uk (Core MSCI World)` | HTTP 200: iShares fund portal reachable |
| **Vanguard** | `ETF Issuer Scraper` | Public / Free | ✅ `OK` | 1088 ms | `vanguardinvestor.co.uk` | HTTP 200: Vanguard portal reachable |
| **VanEck** | `ETF Issuer Scraper` | Public / Free | ✅ `OK` | 1671 ms | `vaneck.com/nl/en/etf/equity/tdiv/overview/` | HTTP 200: VanEck portal reachable |


---

## 🛠️ Actionable Troubleshooting & Remediation Guide



### 🔧 Finnhub (⚠️ Configuration Notice)

- **Status:** `WARN` (FINNHUB_API_KEY not configured (placeholder detected in .env))
- **Endpoint:** `finnhub.io`
- **Remediation:**
Register for a free key at https://finnhub.io and set `FINNHUB_API_KEY=your_key` in `.env` to enable analyst ratings and SEC insider trading alerts.


### 🔧 OpenBB Platform (⚠️ Configuration Notice)

- **Status:** `WARN` (OpenBB package not installed (optional, yfinance fallback active))
- **Endpoint:** `openbb python package`
- **Remediation:**
OpenBB is optional. The vault automatically falls back to Yahoo Finance for fundamental metrics. To install, run: `pip install openbb`.




---

## 📖 Command Line Quick Reference

```bash
# Execute standalone diagnostic check and refresh Health.md
python run.py --health

# Run health check without updating Health.md (terminal output only)
python 99_System/Scripts/health_check.py --no-md

# Probe a single integration
python 99_System/Scripts/health_check.py --integration finnhub
python 99_System/Scripts/health_check.py --integration exante
python 99_System/Scripts/health_check.py --integration yfinance

# Output structured JSON for automation or scripting
python 99_System/Scripts/health_check.py --json
```