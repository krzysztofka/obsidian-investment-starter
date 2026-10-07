"""Unit tests for PKO BP retail treasury bonds platform extension."""

import os

from platforms.pko_bp_bonds import (
    PkoBpBondsPlatform,
    format_maturity_date_yyyymmdd,
    parse_pkobp_sheet,
    resolve_portfolio_allocation,
)


def test_format_maturity_date_yyyymmdd():
    """Verify maturity date formatting to standard YYYYMMDD string format."""
    assert format_maturity_date_yyyymmdd("2036-09-01") == "20360901"
    assert format_maturity_date_yyyymmdd("01.09.2036") == "20360901"
    assert format_maturity_date_yyyymmdd("20380826") == "20380826"
    assert format_maturity_date_yyyymmdd(None) is None
    assert format_maturity_date_yyyymmdd("") is None


def test_resolve_portfolio_allocation_rules():
    """Verify allocation of bond series according to config rules."""
    config = {
        "default_portfolio": "Long term",
        "rules": [
            {"portfolio": "Aggressive", "series": "OTS9999"},
            {"portfolio": "Safety net", "series": "EDO0936"},
            {"portfolio": "Safety net", "prefix": "OTS"},
            {"portfolio": "Safety net", "prefix": "ROR"},
        ],
    }

    # Direct series match
    slices = resolve_portfolio_allocation("EDO0936", 100, 10000, 10050, config)
    assert slices[0]["portfolio"] == "Safety net"

    # Overriding series match
    slices = resolve_portfolio_allocation("OTS9999", 50, 5000, 5000, config)
    assert slices[0]["portfolio"] == "Aggressive"

    # Prefix match
    slices = resolve_portfolio_allocation("OTS0127", 50, 5000, 5000, config)
    assert slices[0]["portfolio"] == "Safety net"
    slices = resolve_portfolio_allocation("ROR0526", 100, 10000, 10000, config)
    assert slices[0]["portfolio"] == "Safety net"

    # Fallback default portfolio
    slices = resolve_portfolio_allocation("ROD0838", 150, 15000, 15080, config)
    assert slices[0]["portfolio"] == "Long term"
    slices = resolve_portfolio_allocation("EDO1034", 100, 10000, 10000, config)
    assert slices[0]["portfolio"] == "Long term"


def test_pko_bp_sample_file_parsing(tmp_path):
    """Verify parsing PKO BP retail bonds Excel spreadsheet."""
    vault_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    bonds_dir = os.path.join(vault_root, "00_Raw", "pko_bp_bonds")
    bonds_files = (
        [
            os.path.join(bonds_dir, f)
            for f in os.listdir(bonds_dir)
            if f.lower().endswith((".xls", ".xlsx")) and not f.startswith("~")
        ]
        if os.path.exists(bonds_dir)
        else []
    )

    if bonds_files:
        rows = parse_pkobp_sheet(bonds_files[0])
        assert len(rows) > 0
        assert "emission" in rows[0]
        assert "quantity" in rows[0]
        assert "current_value" in rows[0]
    else:
        import xlwt

        mock_xls = str(tmp_path / "mock_bonds.xls")
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
        sheet.write(1, 0, "EDO0936")
        sheet.write(1, 1, 100.0)
        sheet.write(1, 2, 0.0)
        sheet.write(1, 3, 10000.0)
        sheet.write(1, 4, 10050.0)
        sheet.write(1, 5, "2036-09-01")
        wb.save(mock_xls)
        rows = parse_pkobp_sheet(mock_xls)
        assert len(rows) == 1
        assert rows[0]["emission"] == "EDO0936"
        assert rows[0]["quantity"] == 100.0


def test_pko_bp_platform_class():
    """Verify PkoBpBondsPlatform class attributes and interface methods."""
    platform = PkoBpBondsPlatform()
    assert platform.id == "pko_bp_bonds"
    assert platform.display_name == "PKO BP (Bonds)"
    assert platform.raw_folder == "pko_bp_bonds"
    assert "pkobp" in platform.aliases
    assert platform.can_handle_file("00_Raw/pko_bp_bonds/StanRachunku.xls")
    assert platform.can_handle_file("00_Raw/pkobp/StanRachunku.xls")
    assert not platform.can_handle_file("00_Raw/degiro/portfolio.csv")
