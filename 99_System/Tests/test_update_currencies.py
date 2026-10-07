"""Unit tests for currency valuation and update_currencies.py."""

import os
import tempfile
from unittest.mock import patch

from model.asset import Asset
from update_currencies import update_currencies


def test_update_currencies():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create USD asset
        asset_usd = Asset(
            ticker="US_STOCK",
            name="US Stock",
            platform="Exante",
            quantity=10,
            current_price=150.0,
            currency="USD",
            value_pln=0.0,
        )
        p1 = os.path.join(tmp_dir, "us_stock.md")
        asset_usd.save(p1)

        # Create PLN asset
        asset_pln = Asset(
            ticker="PL_BOND",
            name="Polish Bond",
            platform="PKOBP",
            quantity=100,
            current_price=100.0,
            currency="PLN",
            value_pln=0.0,
        )
        p2 = os.path.join(tmp_dir, "pl_bond.md")
        asset_pln.save(p2)

        # Mock get_fx_rate_to_pln so USD -> 4.0 PLN
        def mock_fx(curr):
            if curr.upper() == "USD":
                return 4.0
            return 1.0

        with patch("update_currencies.get_fx_rate_to_pln", side_effect=mock_fx):
            with patch(
                "update_currencies.calculate_value_pln",
                side_effect=lambda q, p, c: q * p * (4.0 if c == "USD" else 1.0),
            ):
                update_currencies(assets_dir=tmp_dir, show_progress=False)

        # Verify USD asset value_pln: 10 * 150 * 4.0 = 6000.0
        updated_usd = Asset.from_file(p1)
        assert updated_usd.value_pln == 6000.0

        # Verify PLN asset value_pln: 100 * 100 * 1.0 = 10000.0
        updated_pln = Asset.from_file(p2)
        assert updated_pln.value_pln == 10000.0
