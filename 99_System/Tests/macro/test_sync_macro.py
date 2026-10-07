"""Unit tests for macroeconomic sync engine and dashboard rendering."""

import os
import tempfile

from sync_macro import extract_custom_thesis_log, render_macro_markdown


def test_extract_custom_thesis_log():
    sample_content = """---
last_updated: "2026-10-01"
---
# Macro Dashboard

Some text here.

## 📝 Observations & Macro Thesis Log
### 2026-10-01: Previous thesis note
- We expect rate cuts soon.
"""
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as f:
        f.write(sample_content)
        tmp_name = f.name

    try:
        extracted = extract_custom_thesis_log(tmp_name)
        assert extracted is not None
        assert "## 📝 Observations & Macro Thesis Log" in extracted
        assert "We expect rate cuts soon." in extracted
    finally:
        os.remove(tmp_name)


def test_render_macro_markdown():
    template_content = """---
us_10y_yield: {{ us_10y_yield }}
yield_spread_10y_2y_bps: {{ yield_spread_10y_2y_bps }}
yield_curve_status: {{ yield_curve_status }}
last_updated: "{{ last_updated }}"
---
# Macro Overview

US 10Y Yield: {{ us_10y_yield }}%
Spread: {{ spread_display }}

{{ custom_notes_section }}
"""
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as f:
        f.write(template_content)
        template_path = f.name

    dataset = {
        "last_updated": "2026-10-06",
        "us_10y_yield": 4.12,
        "us_2y_yield": 3.95,
        "yield_spread_10y_2y_bps": 17.0,
        "yield_curve_status": "Normal",
        "spread_display": "+17 bps",
        "pl_10y_yield": 5.40,
        "nbp_reference_rate": 5.75,
        "gold_usd": 2650.0,
        "gold_pln": 10500.0,
        "copper_usd": 4.50,
        "brent_usd": 75.0,
    }

    try:
        rendered = render_macro_markdown(
            dataset=dataset,
            template_path=template_path,
            existing_notes_section="## 📝 Observations & Macro Thesis Log\n- User custom thesis.",
        )
        assert "us_10y_yield: 4.12" in rendered
        assert "yield_spread_10y_2y_bps: 17.0" in rendered
        assert "US 10Y Yield: 4.12%" in rendered
        assert "User custom thesis." in rendered
    finally:
        os.remove(template_path)
