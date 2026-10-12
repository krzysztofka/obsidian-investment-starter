"""Unit tests for Vault Sanity & Data Integrity Checker."""

import os
import sys
import tempfile

SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from sanity_check import (
    probe_assets,
    probe_environment,
    probe_history,
    probe_raw_exports,
    run_sanity_check,
)


def test_probe_assets_clean():
    with tempfile.TemporaryDirectory() as tmp_dir:
        assets_dir = os.path.join(tmp_dir, "10_Finance", "Assets")
        os.makedirs(assets_dir, exist_ok=True)

        valid_equity = """---
ticker: AAPL
name: Apple Inc.
platform: Degiro
portfolio: Aggressive
quantity: 10
current_price: 220.0
value_pln: 8800.0
currency: USD
asset_type: equity
---
# Apple
"""
        valid_cash = """---
ticker: EUR_CASH
name: Cash EUR
platform: Degiro
quantity: 1000
current_price: 1.0
value_pln: 4300.0
currency: EUR
asset_type: cash
---
# Cash
"""
        with open(os.path.join(assets_dir, "AAPL.md"), "w", encoding="utf-8") as f:
            f.write(valid_equity)
        with open(os.path.join(assets_dir, "EUR_CASH.md"), "w", encoding="utf-8") as f:
            f.write(valid_cash)

        issues, count = probe_assets(tmp_dir)
        assert count == 2
        errors = [i for i in issues if i.severity == "ERROR"]
        assert len(errors) == 0


def test_probe_assets_missing_fields_and_invalid_values():
    with tempfile.TemporaryDirectory() as tmp_dir:
        assets_dir = os.path.join(tmp_dir, "10_Finance", "Assets")
        os.makedirs(assets_dir, exist_ok=True)

        # Missing ticker, currency, negative quantity, invalid portfolio
        bad_note = """---
name: Bad Asset
platform: Degiro
portfolio: InvalidBucket
quantity: -5
current_price: 100.0
value_pln: -500.0
asset_type: equity
---
# Bad
"""
        with open(os.path.join(assets_dir, "bad.md"), "w", encoding="utf-8") as f:
            f.write(bad_note)

        issues, count = probe_assets(tmp_dir)
        assert count == 1
        errors = [i for i in issues if i.severity == "ERROR"]
        error_msgs = [e.message for e in errors]

        assert any("Missing or empty required field: 'ticker'" in m for m in error_msgs)
        assert any("Missing or invalid required field: 'currency'" in m for m in error_msgs)
        assert any("Negative 'value_pln'" in m for m in error_msgs)
        assert any("Negative position quantity" in m for m in error_msgs)
        assert any("Invalid portfolio bucket" in m for m in error_msgs)


def test_probe_assets_portfolio_silo_rules():
    with tempfile.TemporaryDirectory() as tmp_dir:
        assets_dir = os.path.join(tmp_dir, "10_Finance", "Assets")
        os.makedirs(assets_dir, exist_ok=True)

        # Invested asset with missing portfolio -> ERROR
        invested_no_port = """---
ticker: MSFT
platform: Exante
quantity: 5
current_price: 400.0
value_pln: 8000.0
currency: USD
asset_type: equity
---
"""
        # Cash asset with null portfolio -> ALLOWED (unallocated dry powder)
        cash_no_port = """---
ticker: USD_CASH
platform: Exante
quantity: 500
current_price: 1.0
value_pln: 2000.0
currency: USD
asset_type: cash
portfolio: null
---
"""
        with open(os.path.join(assets_dir, "MSFT.md"), "w", encoding="utf-8") as f:
            f.write(invested_no_port)
        with open(os.path.join(assets_dir, "USD_CASH.md"), "w", encoding="utf-8") as f:
            f.write(cash_no_port)

        issues, count = probe_assets(tmp_dir)
        assert count == 2
        errors = [i for i in issues if i.severity == "ERROR"]
        assert len(errors) == 1
        assert "Missing required 'portfolio' allocation" in errors[0].message
        assert errors[0].file_path.endswith("MSFT.md")


def test_probe_assets_ticker_collision():
    with tempfile.TemporaryDirectory() as tmp_dir:
        assets_dir = os.path.join(tmp_dir, "10_Finance", "Assets")
        os.makedirs(assets_dir, exist_ok=True)

        note1 = """---
ticker: NVDA
platform: Degiro
portfolio: Aggressive
quantity: 10
current_price: 120.0
value_pln: 4800.0
currency: USD
---
"""
        note2 = """---
ticker: NVDA
platform: Degiro
portfolio: Aggressive
quantity: 5
current_price: 120.0
value_pln: 2400.0
currency: USD
---
"""
        with open(os.path.join(assets_dir, "NVDA_1.md"), "w", encoding="utf-8") as f:
            f.write(note1)
        with open(os.path.join(assets_dir, "NVDA_2.md"), "w", encoding="utf-8") as f:
            f.write(note2)

        issues, _ = probe_assets(tmp_dir)
        errors = [i for i in issues if i.severity == "ERROR"]
        assert any("Ticker collision detected" in e.message for e in errors)


def test_probe_history_clean_and_corrupt():
    with tempfile.TemporaryDirectory() as tmp_dir:
        hist_dir = os.path.join(tmp_dir, "10_Finance", "History")
        os.makedirs(hist_dir, exist_ok=True)
        csv_path = os.path.join(hist_dir, "portfolio.csv")

        # 1. Clean history
        clean_content = """date,ticker,name,value_pln,current_price,pe_ratio,quantity,portfolio
2026-10-01,AAPL,Apple,4000,200,,20,Aggressive
2026-10-02,AAPL,Apple,4200,210,,20,Aggressive
"""
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write(clean_content)

        issues, count = probe_history(tmp_dir, fix=False)
        assert count == 2
        errors = [i for i in issues if i.severity == "ERROR"]
        assert len(errors) == 0

        # 2. History with non-monotonic dates, duplicate snapshot, invalid date format
        bad_content = """date,ticker,name,value_pln,current_price,pe_ratio,quantity,portfolio
2026-10-05,AAPL,Apple,4000,200,,20,Aggressive
2026-10-02,AAPL,Apple,4200,210,,20,Aggressive
2026-10-02,AAPL,Apple,4200,210,,20,Aggressive
bad-date,MSFT,Microsoft,1000,100,,10,Long term
"""
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write(bad_content)

        issues_bad, count_bad = probe_history(tmp_dir, fix=False)
        assert count_bad == 4
        err_msgs = [i.message for i in issues_bad if i.severity == "ERROR"]
        assert any("Non-chronological date sequence" in m for m in err_msgs)
        assert any("Duplicate snapshot" in m for m in err_msgs)
        assert any("Invalid date format" in m for m in err_msgs)


def test_probe_history_auto_fix():
    with tempfile.TemporaryDirectory() as tmp_dir:
        hist_dir = os.path.join(tmp_dir, "10_Finance", "History")
        os.makedirs(hist_dir, exist_ok=True)
        csv_path = os.path.join(hist_dir, "portfolio.csv")

        out_of_order_with_dups = """date,ticker,name,value_pln,current_price,pe_ratio,quantity,portfolio
2026-10-05,AAPL,Apple,4500,225,,20,Aggressive
2026-10-01,AAPL,Apple,4000,200,,20,Aggressive
2026-10-01,AAPL,Apple,4050,202,,20,Aggressive
"""
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write(out_of_order_with_dups)

        # Run with fix=True
        issues, _ = probe_history(tmp_dir, fix=True)
        assert any("Auto-fix applied" in i.message for i in issues if i.severity == "INFO")

        # Verify backup exists
        assert os.path.exists(csv_path + ".bak")

        # Re-probe fixed file
        re_issues, re_count = probe_history(tmp_dir, fix=False)
        re_errors = [i for i in re_issues if i.severity == "ERROR"]
        assert len(re_errors) == 0
        assert re_count == 2  # Deduplicated from 3 to 2 rows


def test_probe_raw_exports():
    with tempfile.TemporaryDirectory() as tmp_dir:
        raw_dir = os.path.join(tmp_dir, "00_Raw", "broker")
        os.makedirs(raw_dir, exist_ok=True)

        # 1. Valid CSV
        with open(os.path.join(raw_dir, "statement.csv"), "w", encoding="utf-8") as f:
            f.write("Col1,Col2\n1,2\n")

        # 2. Suspicious file extension
        with open(os.path.join(raw_dir, "malicious.exe"), "w", encoding="utf-8") as f:
            f.write("fake binary")

        # 3. Empty file (not .gitkeep)
        with open(os.path.join(raw_dir, "empty.csv"), "w", encoding="utf-8") as f:
            pass

        issues, count = probe_raw_exports(tmp_dir)
        assert count >= 3
        errors = [i for i in issues if i.severity == "ERROR"]
        warns = [i for i in issues if i.severity == "WARN"]

        assert any("Unsupported / suspicious file format" in e.message for e in errors)
        assert any("Zero-byte empty file" in w.message for w in warns)


def test_probe_environment():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Missing .env, only .env.example
        with open(os.path.join(tmp_dir, ".env.example"), "w", encoding="utf-8") as f:
            f.write("FINNHUB_API_KEY=your_api_key_here\n")

        issues_missing = probe_environment(tmp_dir)
        assert any(i.severity == "WARN" and "Missing '.env' file" in i.message for i in issues_missing)

        # Invalid syntax in .env
        with open(os.path.join(tmp_dir, ".env"), "w", encoding="utf-8") as f:
            f.write("INVALID_SYNTAX_LINE_WITHOUT_EQUALS\nFINNHUB_API_KEY=your_api_key_here\n")

        issues_syntax = probe_environment(tmp_dir)
        assert any(i.severity == "ERROR" and "Invalid syntax" in i.message for i in issues_syntax)
        assert any(i.severity == "WARN" and "placeholder value" in i.message for i in issues_syntax)


def test_run_sanity_check_master():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create minimal clean vault structure
        os.makedirs(os.path.join(tmp_dir, "10_Finance", "Assets"), exist_ok=True)
        os.makedirs(os.path.join(tmp_dir, "10_Finance", "History"), exist_ok=True)
        os.makedirs(os.path.join(tmp_dir, "00_Raw"), exist_ok=True)

        with open(os.path.join(tmp_dir, ".env"), "w", encoding="utf-8") as f:
            f.write("FINNHUB_API_KEY=real_key_12345\n")

        with open(os.path.join(tmp_dir, "10_Finance", "History", "portfolio.csv"), "w", encoding="utf-8") as f:
            f.write("date,ticker,value_pln\n2026-10-01,EDO,1000\n")

        report, exit_code = run_sanity_check(vault_path=tmp_dir, verbose=False)
        assert exit_code == 0
        assert report.is_clean is True
        assert report.error_count == 0
