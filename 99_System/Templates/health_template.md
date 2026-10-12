---
type: health_dashboard
title: Integrations Health & Connectivity Diagnostics
last_checked: "{{ last_checked }}"
status_summary: "{{ status_summary }}"
total_probed: {{ total_probed }}
passed_count: {{ passed_count }}
warn_count: {{ warn_count }}
failed_count: {{ failed_count }}
all_ok: {{ all_ok | lower }}
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

{% if failed_count > 0 %}
> [!CAUTION] ❌ **Integration Failures Detected**
> **{{ failed_count }} service(s)** failed connectivity checks. Review the diagnostic table and troubleshooting hints below.
{% elif warn_count > 0 %}
> [!WARNING] ⚠️ **Configuration Warnings Detected**
> **{{ passed_count }} service(s)** passed, but **{{ warn_count }} optional service(s)** have warnings (unconfigured API keys or optional libraries). Core functionality is intact.
{% else %}
> [!SUCCESS] ✅ **All Systems Operational**
> All **{{ passed_count }} external integrations** responded successfully with valid responses and healthy latencies.
{% endif %}

**Last Diagnostic Scan:** `{{ last_checked }}` · **Overall Result:** `{{ status_summary }}`

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
{% for r in results -%}
| **{{ r.name }}** | `{{ r.category }}` | {{ r.auth_requirement }} | {% if r.status == "OK" %}✅ `OK`{% elif r.status == "WARN" %}⚠️ `WARN`{% elif r.status == "FAIL" %}❌ `FAIL`{% else %}⚪ `{{ r.status }}`{% endif %} | {% if r.latency_ms is not none %}{{ "%.0f"|format(r.latency_ms) }} ms{% else %}—{% endif %} | `{{ r.endpoint_display }}` | {{ r.message }} |
{% endfor %}

---

## 🛠️ Actionable Troubleshooting & Remediation Guide

{% if failed_count == 0 and warn_count == 0 %}
> [!NOTE] ℹ️ **No Actions Required**
> All probed services and API keys are verified and functioning normally.
{% else %}
{% for r in results if r.status in ["FAIL", "WARN"] %}
### 🔧 {{ r.name }} ({% if r.status == "FAIL" or (r.status.value is defined and r.status.value == "FAIL") %}❌ Action Required{% else %}⚠️ Configuration Notice{% endif %})

- **Status:** `{{ r.status.value if r.status.value is defined else r.status }}` ({{ r.message }})
- **Endpoint:** `{{ r.endpoint_display }}`
- **Remediation:**
{{ r.troubleshooting }}

{% endfor %}
{% endif %}

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
