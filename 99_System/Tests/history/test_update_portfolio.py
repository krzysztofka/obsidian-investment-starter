"""Unit tests for portfolio history timeline update and synchronization."""

import csv
import os
import tempfile

from history.update_portfolio import format_val, update_portfolio_history
from model.asset import Asset


def test_format_val():
    assert format_val(None) == ""
    assert format_val("null") == ""
    assert format_val(100.0) == "100"
    assert format_val(123.45) == "123.45"
    assert format_val("Aggressive") == "Aggressive"


def test_update_portfolio_history():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # 1. Setup mock vault structure
        assets_dir = os.path.join(tmp_dir, "10_Finance", "Assets")
        history_dir = os.path.join(tmp_dir, "10_Finance", "History")
        decisions_dir = os.path.join(tmp_dir, "20_Decisions", "2026")
        os.makedirs(assets_dir, exist_ok=True)
        os.makedirs(history_dir, exist_ok=True)
        os.makedirs(decisions_dir, exist_ok=True)

        # 2. Write existing historical CSV with an earlier date
        csv_path = os.path.join(history_dir, "portfolio.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["date", "ticker", "name", "value_pln", "current_price", "pe_ratio", "quantity", "portfolio"]
            )
            writer.writerow(["2026-08-01", "MSFT", "Microsoft", "10000", "400", "35", "10", "Aggressive"])
            writer.writerow(["2026-08-01", "AAPL", "Apple", "5000", "150", "30", "15", "Aggressive"])

        # 3. Create current asset in 10_Finance/Assets
        current_asset = Asset(
            ticker="MSFT",
            name="Microsoft Corporation",
            platform="Exante",
            portfolio="Aggressive",
            quantity=10,
            current_price=420.0,
            value_pln=16000.0,
            pe_ratio=34.0,
            last_updated="2026-10-06",
        )
        current_asset.save(os.path.join(assets_dir, "microsoft.md"))

        # 4. Run update_portfolio_history
        result_path = update_portfolio_history(base_dir=tmp_dir)
        assert os.path.exists(result_path)

        # 5. Verify contents
        with open(result_path, encoding="utf-8") as f:
            reader = list(csv.DictReader(f))

        # Should contain 3 rows: 2 from 2026-08-01, 1 from 2026-10-06
        assert len(reader) == 3

        # Chronological sort verification
        dates = [r["date"] for r in reader]
        assert dates == ["2026-08-01", "2026-08-01", "2026-10-06"]

        # Alphabetical ticker sorting within same date
        tickers_aug = [r["ticker"] for r in reader if r["date"] == "2026-08-01"]
        assert tickers_aug == ["AAPL", "MSFT"]

        # Latest snapshot
        latest = [r for r in reader if r["date"] == "2026-10-06"][0]
        assert latest["ticker"] == "MSFT"
        assert latest["value_pln"] == "16000"
        assert latest["portfolio"] == "Aggressive"
