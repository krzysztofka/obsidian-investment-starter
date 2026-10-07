"""Unit tests for Exante platform extension."""

from platforms.common import parse_number
from platforms.exante import (
    ExantePlatform,
    find_exante_csv,
    find_section,
)


def test_exante_platform_class():
    """Verify ExantePlatform class metadata and path matching."""
    platform = ExantePlatform()
    assert platform.id == "exante"
    assert platform.display_name == "Exante"
    assert platform.raw_folder == "exante"
    assert "ex" in platform.aliases
    assert platform.can_handle_file("00_Raw/exante/statement.csv")
    assert platform.can_handle_file("00_Raw/Exante/statement.csv")
    assert not platform.can_handle_file("00_Raw/degiro/portfolio.csv")


def test_find_exante_csv(tmp_path):
    """Verify finding the most recent Exante CSV file."""
    # Create fake vault structure
    exante_dir = tmp_path / "00_Raw" / "exante"
    exante_dir.mkdir(parents=True)

    # Empty dir returns None
    assert find_exante_csv(str(tmp_path)) is None

    # Adds a file
    csv_file = exante_dir / "Account_2026-10-05.csv"
    csv_file.write_text("dummy", encoding="utf-8")
    assert find_exante_csv(str(tmp_path)) == str(csv_file)


def test_find_section_exante():
    """Verify parsing section blocks in Exante tab-separated export format."""
    sample_content = [
        "Cash Balances",
        "Instrument\tISO\tValue\tCurrency",
        "EUR Cash\tEUR\t1500.00\tEUR",
        "USD Cash\tUSD\t800.00\tUSD",
        "",
        "Stocks & ETFs",
        "Instrument\tName\tQTY\tAvg Price\tPrice\tCurrency\tISIN",
        "MSFT.NASDAQ\tMicrosoft Corporation\t10\t400.00\t420.50\tUSD\tUS5949181045",
        "V80A.XETRA\tVanguard LifeStrategy 80% Equity\t100\t40.00\t43.80\tEUR\tIE00BMVB5R75",
    ]

    cash_rows = find_section(sample_content, "cash", "balances")
    assert len(cash_rows) == 2
    assert cash_rows[0]["Instrument"] == "EUR Cash"
    assert parse_number(cash_rows[0]["Value"]) == 1500.0
    assert parse_number(cash_rows[1]["Value"]) == 800.0

    stock_rows = find_section(sample_content, "stocks")
    assert len(stock_rows) == 2
    assert stock_rows[0]["Instrument"] == "MSFT.NASDAQ"
    assert stock_rows[0]["ISIN"] == "US5949181045"
    assert parse_number(stock_rows[0]["QTY"]) == 10.0
    assert stock_rows[1]["Instrument"] == "V80A.XETRA"
    assert stock_rows[1]["ISIN"] == "IE00BMVB5R75"
