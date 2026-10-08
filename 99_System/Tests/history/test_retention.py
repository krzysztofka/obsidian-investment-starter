"""Unit tests for Data Retention & History Archival Engine."""

import csv
import os
import tempfile
from datetime import datetime, timedelta

from history.retention import (
    PORTFOLIO_FIELDS,
    archive_portfolio_history,
    compute_file_sha256,
    extract_date_from_filename,
    is_path_excluded,
    rotate_raw_data,
    run_retention_pipeline,
)


def test_extract_date_from_filename():
    assert extract_date_from_filename("export_2024-05-15.csv") == datetime(2024, 5, 15)
    assert extract_date_from_filename("degiro_2023_11_20.csv") == datetime(2023, 11, 20)
    assert extract_date_from_filename("StanRachunkuRejestrowego_20240101.xls") == datetime(2024, 1, 1)
    assert extract_date_from_filename("20240810_ike.csv") == datetime(2024, 8, 10)
    assert extract_date_from_filename("portfolio.csv") is None
    assert extract_date_from_filename("sample_degiro.csv") is None
    assert extract_date_from_filename("invalid_20249999.csv") is None


def test_is_path_excluded():
    exclude_patterns = ["sample_*", ".*", ".gitkeep", "Articles/*", "archive/*"]

    assert is_path_excluded("sample_pkobp.xls", exclude_patterns)
    assert is_path_excluded("degiro/sample_degiro.csv", exclude_patterns)
    assert is_path_excluded(".gitkeep", exclude_patterns)
    assert is_path_excluded("degiro/.gitkeep", exclude_patterns)
    assert is_path_excluded("Articles/research.pdf", exclude_patterns)
    assert is_path_excluded("archive/degiro/old.csv", exclude_patterns)
    assert not is_path_excluded("degiro/trades_20240101.csv", exclude_patterns)
    assert not is_path_excluded("mbank_ike/2024-02-01_ike.csv", exclude_patterns)


def test_compute_file_sha256():
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as f:
        f.write("Hello World")
        path = f.name
    try:
        h1 = compute_file_sha256(path)
        assert len(h1) == 64
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as f2:
            f2.write("Hello World")
            path2 = f2.name
        try:
            assert compute_file_sha256(path2) == h1
        finally:
            os.remove(path2)
    finally:
        os.remove(path)


def test_archive_portfolio_history_basic_and_baseline():
    with tempfile.TemporaryDirectory() as tmp_dir:
        history_dir = os.path.join(tmp_dir, "10_Finance", "History")
        os.makedirs(history_dir, exist_ok=True)
        portfolio_file = os.path.join(history_dir, "portfolio.csv")

        # Today is reference. Let's create dates:
        # - Old: 800 days ago (Year 2024)
        # - Old: 750 days ago (Year 2024)
        # - Recent: 30 days ago
        d_800 = (datetime.now() - timedelta(days=800)).strftime("%Y-%m-%d")
        d_750 = (datetime.now() - timedelta(days=750)).strftime("%Y-%m-%d")
        d_30 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        rows = [
            {
                "date": d_800,
                "ticker": "MSFT",
                "name": "Microsoft",
                "value_pln": "10000",
                "current_price": "400",
                "pe_ratio": "35",
                "quantity": "10",
                "portfolio": "Aggressive",
            },
            {
                "date": d_800,
                "ticker": "SOLD_ASSET",
                "name": "Sold Inc",
                "value_pln": "5000",
                "current_price": "100",
                "pe_ratio": "",
                "quantity": "50",
                "portfolio": "Aggressive",
            },
            {
                "date": d_750,
                "ticker": "SOLD_ASSET",
                "name": "Sold Inc",
                "value_pln": "0",
                "current_price": "120",
                "pe_ratio": "",
                "quantity": "0",
                "portfolio": "Aggressive",
            },
            {
                "date": d_30,
                "ticker": "AAPL",
                "name": "Apple",
                "value_pln": "15000",
                "current_price": "200",
                "pe_ratio": "30",
                "quantity": "20",
                "portfolio": "Aggressive",
            },
        ]

        with open(portfolio_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=PORTFOLIO_FIELDS)
            writer.writeheader()
            writer.writerows(rows)

        # Run archival with 730 days threshold (2 years)
        res = archive_portfolio_history(base_dir=tmp_dir, retention_days=730, dry_run=False, preserve_baseline=True)

        assert res["status"] == "archived"
        assert res["archived_count"] == 3  # MSFT, SOLD_ASSET x2

        # Verify annual archive was created
        cutoff_date = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")
        year_800 = d_800[:4]
        archive_file = os.path.join(tmp_dir, "10_Finance", "History", "archive", f"history-archive-{year_800}.csv")
        assert os.path.exists(archive_file)

        with open(archive_file, encoding="utf-8") as f:
            archived_reader = list(csv.DictReader(f))
        assert len(archived_reader) == 3

        # Verify active portfolio.csv contents
        with open(portfolio_file, encoding="utf-8") as f:
            retained_reader = list(csv.DictReader(f))

        # Expected in retained:
        # 1. AAPL from d_30
        # 2. Baseline for MSFT at cutoff_date (active holding before cutoff carried forward)
        # 3. SOLD_ASSET should NOT be synthesized as baseline because its latest state before cutoff had quantity=0
        retained_tickers = [r["ticker"] for r in retained_reader]
        assert "AAPL" in retained_tickers
        assert "MSFT" in retained_tickers
        assert "SOLD_ASSET" not in retained_tickers

        msft_row = next(r for r in retained_reader if r["ticker"] == "MSFT")
        assert msft_row["date"] == cutoff_date
        assert msft_row["quantity"] == "10"
        assert msft_row["value_pln"] == "10000"


def test_archive_portfolio_history_dry_run():
    with tempfile.TemporaryDirectory() as tmp_dir:
        history_dir = os.path.join(tmp_dir, "10_Finance", "History")
        os.makedirs(history_dir, exist_ok=True)
        portfolio_file = os.path.join(history_dir, "portfolio.csv")

        d_800 = (datetime.now() - timedelta(days=800)).strftime("%Y-%m-%d")
        rows = [
            {
                "date": d_800,
                "ticker": "MSFT",
                "name": "Microsoft",
                "value_pln": "10000",
                "current_price": "400",
                "pe_ratio": "35",
                "quantity": "10",
                "portfolio": "Aggressive",
            },
        ]

        with open(portfolio_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=PORTFOLIO_FIELDS)
            writer.writeheader()
            writer.writerows(rows)

        res = archive_portfolio_history(base_dir=tmp_dir, retention_days=730, dry_run=True)
        assert res["status"] == "archived"
        assert res["dry_run"] is True

        # Archive directory should NOT be created on disk in dry-run
        archive_dir = os.path.join(tmp_dir, "10_Finance", "History", "archive")
        assert not os.path.exists(archive_dir)

        # portfolio.csv should still have original contents
        with open(portfolio_file, encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
        assert len(reader) == 1
        assert reader[0]["date"] == d_800


def test_archive_portfolio_history_idempotent():
    with tempfile.TemporaryDirectory() as tmp_dir:
        history_dir = os.path.join(tmp_dir, "10_Finance", "History")
        os.makedirs(history_dir, exist_ok=True)
        portfolio_file = os.path.join(history_dir, "portfolio.csv")

        d_800 = (datetime.now() - timedelta(days=800)).strftime("%Y-%m-%d")
        d_30 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        rows = [
            {
                "date": d_800,
                "ticker": "MSFT",
                "name": "Microsoft",
                "value_pln": "10000",
                "current_price": "400",
                "pe_ratio": "35",
                "quantity": "10",
                "portfolio": "Aggressive",
            },
            {
                "date": d_30,
                "ticker": "MSFT",
                "name": "Microsoft",
                "value_pln": "11000",
                "current_price": "420",
                "pe_ratio": "36",
                "quantity": "10",
                "portfolio": "Aggressive",
            },
        ]

        with open(portfolio_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=PORTFOLIO_FIELDS)
            writer.writeheader()
            writer.writerows(rows)

        # First run archives d_800
        res1 = archive_portfolio_history(base_dir=tmp_dir, retention_days=730, dry_run=False)
        assert res1["status"] == "archived"

        # Second run: nothing older than cutoff remains
        res2 = archive_portfolio_history(base_dir=tmp_dir, retention_days=730, dry_run=False)
        assert res2["status"] == "up_to_date"
        assert res2["archived_count"] == 0


def test_rotate_raw_data_archive_and_collision():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create raw folders
        degiro_dir = os.path.join(tmp_dir, "00_Raw", "degiro")
        os.makedirs(degiro_dir, exist_ok=True)

        # 1. Sample file (should be ignored)
        sample_file = os.path.join(degiro_dir, "sample_degiro.csv")
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write("sample content")

        # 2. Expired file by filename: 400 days ago
        d_400 = (datetime.now() - timedelta(days=400)).strftime("%Y%m%d")
        expired_file = os.path.join(degiro_dir, f"export_{d_400}.csv")
        with open(expired_file, "w", encoding="utf-8") as f:
            f.write("trade1,trade2,100")

        # 3. Recent file by filename: 10 days ago
        d_10 = (datetime.now() - timedelta(days=10)).strftime("%Y%m%d")
        recent_file = os.path.join(degiro_dir, f"export_{d_10}.csv")
        with open(recent_file, "w", encoding="utf-8") as f:
            f.write("trade3,trade4,200")

        # Run rotation (action: archive)
        res = rotate_raw_data(base_dir=tmp_dir, retention_days=365, action="archive", dry_run=False)

        assert res["status"] == "ok"
        assert res["scanned_files"] == 2  # sample_degiro is excluded, so 2 files scanned
        assert res["rotated_count"] == 1

        # Check that expired file moved to 00_Raw/archive/degiro/
        dest_archive = os.path.join(tmp_dir, "00_Raw", "archive", "degiro", f"export_{d_400}.csv")
        assert os.path.exists(dest_archive)
        assert not os.path.exists(expired_file)

        # Check sample file and recent file still exist in original location
        assert os.path.exists(sample_file)
        assert os.path.exists(recent_file)

        # Test collision handling:
        # A) Identical content collision -> deduplicate
        with open(expired_file, "w", encoding="utf-8") as f:
            f.write("trade1,trade2,100")  # Same content as dest_archive

        res_dup = rotate_raw_data(base_dir=tmp_dir, retention_days=365, action="archive", dry_run=False)
        assert res_dup["rotated_count"] == 1
        assert res_dup["rotated_files"][0]["collision"] == "identical_deduplicated"
        assert not os.path.exists(expired_file)

        # B) Different content collision -> rename with timestamp suffix
        with open(expired_file, "w", encoding="utf-8") as f:
            f.write("different,content,999")

        res_diff = rotate_raw_data(base_dir=tmp_dir, retention_days=365, action="archive", dry_run=False)
        assert res_diff["rotated_count"] == 1
        assert res_diff["rotated_files"][0]["collision"] == "renamed_with_timestamp"
        assert not os.path.exists(expired_file)

        # Archive directory should now have 2 files for that export
        archived_files = os.listdir(os.path.join(tmp_dir, "00_Raw", "archive", "degiro"))
        assert len(archived_files) == 2


def test_rotate_raw_data_prune():
    with tempfile.TemporaryDirectory() as tmp_dir:
        exante_dir = os.path.join(tmp_dir, "00_Raw", "exante")
        os.makedirs(exante_dir, exist_ok=True)

        d_400 = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
        expired_file = os.path.join(exante_dir, f"exante_{d_400}.csv")
        with open(expired_file, "w", encoding="utf-8") as f:
            f.write("exante data")

        res = rotate_raw_data(base_dir=tmp_dir, retention_days=365, action="prune", dry_run=False)
        assert res["status"] == "ok"
        assert res["rotated_count"] == 1
        assert not os.path.exists(expired_file)


def test_run_retention_pipeline():
    with tempfile.TemporaryDirectory() as tmp_dir:
        history_dir = os.path.join(tmp_dir, "10_Finance", "History")
        raw_dir = os.path.join(tmp_dir, "00_Raw", "degiro")
        os.makedirs(history_dir, exist_ok=True)
        os.makedirs(raw_dir, exist_ok=True)

        portfolio_file = os.path.join(history_dir, "portfolio.csv")
        with open(portfolio_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=PORTFOLIO_FIELDS)
            writer.writeheader()
            writer.writerow(
                {
                    "date": "2024-01-01",
                    "ticker": "MSFT",
                    "name": "MSFT",
                    "value_pln": "1000",
                    "current_price": "100",
                    "pe_ratio": "",
                    "quantity": "10",
                    "portfolio": "Aggressive",
                }
            )

        raw_file = os.path.join(raw_dir, "export_20240101.csv")
        with open(raw_file, "w", encoding="utf-8") as f:
            f.write("old data")

        results = run_retention_pipeline(base_dir=tmp_dir, dry_run=False)
        assert "history" in results
        assert "raw_data" in results
        assert results["history"]["status"] == "archived"
        assert results["raw_data"]["rotated_count"] == 1
