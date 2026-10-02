"""Unit tests for PKO BP treasury bonds parsing and allocation."""

import os
import sys
import pytest

# Ensure scripts dir is on sys.path
SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "99_System", "Scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from platforms.pkobp import (
    format_maturity_date_yyyymmdd,
    load_pkobp_config,
    resolve_portfolio_allocation,
    parse_pkobp_sheet,
)


def test_format_maturity_date_yyyymmdd():
    assert format_maturity_date_yyyymmdd("2036-09-01") == "20360901"
    assert format_maturity_date_yyyymmdd("01.09.2036") == "20360901"
    assert format_maturity_date_yyyymmdd("20380826") == "20380826"
    assert format_maturity_date_yyyymmdd(None) is None
    assert format_maturity_date_yyyymmdd("") is None


def test_resolve_portfolio_allocation_rules():
    config = {
        "default_portfolio": "Long term",
        "rules": [
            {"ticker": "EDO0936", "portfolio": "Safety net", "max_amount": 90000},
            {"prefix": "ROD", "portfolio": "Safety net", "max_amount": 90000},
            {"prefix": "OTS", "portfolio": "Safety net"},
        ],
    }

    # 1. Fits within max_amount
    slices = resolve_portfolio_allocation(
        emission="ROD0838",
        total_qty=500,
        nominal_val=50000.0,
        current_val=50200.0,
        config=config,
        maturity_date="2038-08-26",
    )
    assert len(slices) == 1
    assert slices[0]["portfolio"] == "Safety net"
    assert slices[0]["quantity"] == 500
    assert slices[0]["ticker"] == "ROD0838_20380826"

    # 2. Exceeds max_amount -> split into Safety net + Long term overflow
    slices_split = resolve_portfolio_allocation(
        emission="EDO0936",
        total_qty=1500,
        nominal_val=150000.0,
        current_val=150600.0,
        config=config,
        maturity_date="2036-09-01",
    )
    assert len(slices_split) == 2
    assert slices_split[0]["portfolio"] == "Safety net"
    assert slices_split[0]["quantity"] == 900
    assert slices_split[1]["portfolio"] == "Long term"
    assert slices_split[1]["quantity"] == 600

    # 3. Default fallback
    slices_default = resolve_portfolio_allocation(
        emission="COI1228",
        total_qty=100,
        nominal_val=10000.0,
        current_val=10000.0,
        config=config,
        maturity_date="2028-12-01",
    )
    assert len(slices_default) == 1
    assert slices_default[0]["portfolio"] == "Long term"


def test_parse_sample_pkobp_sheet(tmp_path):
    sample_file = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "00_Raw", "pkobp", "sample_pkobp.xls")
    )
    if not os.path.exists(sample_file):
        import xlwt
        wb = xlwt.Workbook(encoding="utf-8")
        sheet = wb.add_sheet("Stan Rachunku Rejestrowego")
        headers = [
            "EMISJA",
            "DOSTĘPNA LICZBA OBLIGACJI",
            "ZABLOKOWANA LICZBA OBLIGACJI",
            "WARTOŚĆ NOMINALNA",
            "WARTOŚĆ AKTUALNA",
            "DATA WYKUPU",
        ]
        for c, h in enumerate(headers):
            sheet.write(0, c, h)
        rows = [
            ["EDO0936", 100.0, 0.0, 10000.0, 10050.0, "2036-09-01"],
            ["ROD0838", 150.0, 0.0, 15000.0, 15080.0, "2038-08-26"],
            ["OTS0127", 50.0, 0.0, 5000.0, 5000.0, "2027-01-01"],
        ]
        for r_idx, row in enumerate(rows, start=1):
            for c_idx, val in enumerate(row):
                sheet.write(r_idx, c_idx, val)
        sample_file = str(tmp_path / "test_pkobp.xls")
        wb.save(sample_file)

    positions = parse_pkobp_sheet(sample_file)
    assert len(positions) >= 3

    emissions = [p["emission"] for p in positions]
    assert "EDO0936" in emissions
    assert "ROD0838" in emissions
    assert "OTS0127" in emissions

    for p in positions:
        assert p["quantity"] > 0
        assert p["nominal_value"] > 0
        assert p["current_value"] > 0
        assert p["maturity_date"] != ""
