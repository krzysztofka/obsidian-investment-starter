"""Unit tests for Degiro platform extension."""

import csv

from platforms.common import parse_number
from platforms.degiro import (
    DegiroPlatform,
    find_degiro_csv,
)


def test_degiro_platform_class():
    """Verify DegiroPlatform class metadata and path matching."""
    platform = DegiroPlatform()
    assert platform.id == "degiro"
    assert platform.display_name == "Degiro"
    assert platform.raw_folder == "degiro"
    assert "deg" in platform.aliases
    assert platform.can_handle_file("00_Raw/degiro/portfolio.csv")
    assert platform.can_handle_file("00_Raw/Degiro/portfolio.csv")
    assert not platform.can_handle_file("00_Raw/exante/statement.csv")


def test_find_degiro_csv(tmp_path):
    """Verify finding the most relevant Degiro CSV file in candidate directories."""
    degiro_dir = tmp_path / "degiro"
    degiro_dir.mkdir()

    # Empty dir returns None
    assert find_degiro_csv(str(degiro_dir)) is None

    # Adds a file
    csv_file = degiro_dir / "Portfolio_2026-10-05.csv"
    csv_file.write_text("dummy", encoding="utf-8")
    assert find_degiro_csv(str(degiro_dir)) == str(csv_file)


def test_degiro_csv_structure_parsing(tmp_path):
    """Verify parsing Degiro CSV export format."""
    mock_csv = tmp_path / "sample_degiro.csv"
    content = """Produkt,Symbol/ISIN,Suma,Kurs,Lokalna wartość,,Wartość w EUR
CASH & CASH FUND & FTX CASH (EUR),,,,EUR,"2500,00","2500,00"
MICROSOFT CORPORATION,US5949181045,10,"420,50",EUR,"4205,00","4205,00"
VANGUARD LIFESTRATEGY 80% EQUITY...,IE00BMVB5R75,100,"43,80",EUR,"4380,00","4380,00"
"""
    mock_csv.write_text(content, encoding="utf-8-sig")

    with open(str(mock_csv), encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 3
    # Cash row
    assert "CASH" in rows[0]["Produkt"]
    # Stock row
    assert rows[1]["Symbol/ISIN"] == "US5949181045"
    assert parse_number(rows[1]["Suma"]) == 10.0
    assert parse_number(rows[1]["Kurs"]) == 420.5
    # ETF row
    assert rows[2]["Symbol/ISIN"] == "IE00BMVB5R75"
    assert parse_number(rows[2]["Suma"]) == 100.0
