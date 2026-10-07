"""Unit tests for mBank eMakler (IKE & IKZE) platform extensions."""

import os

from platforms.mbank_common import (
    detect_account_type_from_path,
    parse_mbm_file_content,
    resolve_instrument_identifiers,
)
from platforms.mbank_ike import MbankIkePlatform
from platforms.mbank_ikze import MbankIkzePlatform


def test_mbank_platform_classes():
    """Verify MbankIkePlatform and MbankIkzePlatform metadata and interface."""
    ike = MbankIkePlatform()
    assert ike.id == "mbank_ike"
    assert ike.display_name == "mBank (IKE)"
    assert ike.raw_folder == "mbank_ike"
    assert "ike" in ike.aliases
    assert ike.can_handle_file("00_Raw/mbank_ike/ike-2026.csv")
    assert ike.can_handle_file("00_Raw/mBM/ike-2026.csv")
    assert not ike.can_handle_file("00_Raw/mbank_ikze/ikze-2026.csv")

    ikze = MbankIkzePlatform()
    assert ikze.id == "mbank_ikze"
    assert ikze.display_name == "mBank (IKZE)"
    assert ikze.raw_folder == "mbank_ikze"
    assert "ikze" in ikze.aliases
    assert ikze.can_handle_file("00_Raw/mbank_ikze/ikze-2026.csv")
    assert ikze.can_handle_file("00_Raw/mBM/ikze-2026.csv")
    assert not ikze.can_handle_file("00_Raw/mbank_ike/ike-2026.csv")


def test_detect_account_type_from_path():
    """Verify account type detection from file path strings."""
    assert detect_account_type_from_path("00_Raw/mbank_ike/sample_ike.csv") == "ike"
    assert detect_account_type_from_path("00_Raw/mbank_ikze/sample_ikze.csv") == "ikze"
    assert detect_account_type_from_path("00_Raw/mBM/ike-2026-09-16.csv") == "ike"
    assert detect_account_type_from_path("00_Raw/mBM/ikze-2026-09-16.csv") == "ikze"


def test_mbank_identifier_resolution():
    """Verify resolution of tickers, ISINs, and asset allocation from paper names."""
    # Known ETF mapping
    v80a = resolve_instrument_identifiers("V80A GR ETF", "DEU-XETRA", "ikze")
    assert v80a["isin"] == "IE00BMVB5R75"
    assert v80a["yahoo_ticker"] == "V80A.DE"
    assert v80a["asset_type"] == "etf"
    assert v80a["asset_allocation"]["equity"] == 80
    assert v80a["asset_allocation"]["bonds"] == 20

    # Generic stock resolution with suffix
    kghm = resolve_instrument_identifiers("KGHM", "WSE", "ike")
    assert kghm["yahoo_ticker"] == "KGHM.WA"
    assert kghm["asset_type"] == "equity"


def test_mbank_sample_files_parsing(tmp_path):
    """Verify parsing mBank eMakler CSV export structure."""
    vault_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

    # IKE
    ike_dir = os.path.join(vault_root, "00_Raw", "mbank_ike")
    ike_files = (
        [os.path.join(ike_dir, f) for f in os.listdir(ike_dir) if f.lower().endswith(".csv")]
        if os.path.exists(ike_dir)
        else []
    )
    if ike_files:
        d_ike, acc_ike, rows_ike = parse_mbm_file_content(ike_files[0])
        assert len(rows_ike) > 0
    else:
        mock_ike = tmp_path / "mock_ike.csv"
        mock_ike.write_text(
            "#Data;2026-10-05\n#Nr rachunku;1234\nPapier;Giełda;Liczba;Kurs;Waluta\nVWCE;DEU-XETRA;10;120.5;EUR\n",
            encoding="utf-8",
        )
        d_ike, acc_ike, rows_ike = parse_mbm_file_content(str(mock_ike))
        assert len(rows_ike) == 1

    # IKZE
    ikze_dir = os.path.join(vault_root, "00_Raw", "mbank_ikze")
    ikze_files = (
        [os.path.join(ikze_dir, f) for f in os.listdir(ikze_dir) if f.lower().endswith(".csv")]
        if os.path.exists(ikze_dir)
        else []
    )
    if ikze_files:
        d_ikze, acc_ikze, rows_ikze = parse_mbm_file_content(ikze_files[0])
        assert len(rows_ikze) > 0
    else:
        mock_ikze = tmp_path / "mock_ikze.csv"
        mock_ikze.write_text(
            "#Data;2026-10-05\n#Nr rachunku;5678\nPapier;Giełda;Liczba;Kurs;Waluta\nV80A;DEU-XETRA;20;35.2;EUR\n",
            encoding="utf-8",
        )
        d_ikze, acc_ikze, rows_ikze = parse_mbm_file_content(str(mock_ikze))
        assert len(rows_ikze) == 1
