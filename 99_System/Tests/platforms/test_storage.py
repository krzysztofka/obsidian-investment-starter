"""Unit tests for platforms.storage module."""

import os
import tempfile

from model.asset import Asset
from platforms.storage import (
    remove_missing_platform_assets,
    save_or_update_asset,
)


def test_save_or_update_asset():
    with tempfile.TemporaryDirectory() as tmp_dir:
        fpath = save_or_update_asset(
            vault_assets_dir=tmp_dir,
            platform="Degiro",
            ticker="TEST_TICKER",
            name="Test Asset",
            quantity=10,
            current_price=100.0,
            currency="USD",
            avg_price=95.0,
            source="platform",
            portfolio="Aggressive",
        )
        assert os.path.exists(fpath)
        asset = Asset.from_file(fpath)
        assert asset.ticker == "TEST_TICKER"
        assert asset.quantity == 10
        assert asset.current_price == 100.0

        # Update existing
        save_or_update_asset(
            vault_assets_dir=tmp_dir,
            platform="Degiro",
            ticker="TEST_TICKER",
            name="Test Asset",
            quantity=15,
            current_price=110.0,
            currency="USD",
            avg_price=95.0,
        )
        updated_asset = Asset.from_file(fpath)
        assert updated_asset.quantity == 15
        assert updated_asset.current_price == 110.0


def test_remove_missing_platform_assets():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create active platform asset
        p1 = save_or_update_asset(
            vault_assets_dir=tmp_dir,
            platform="Degiro",
            ticker="ACTIVE_1",
            name="Active One",
            quantity=5,
            current_price=10.0,
            currency="EUR",
            source="platform",
        )
        # Create missing platform asset
        p2 = save_or_update_asset(
            vault_assets_dir=tmp_dir,
            platform="Degiro",
            ticker="STALE_1",
            name="Stale One",
            quantity=5,
            current_price=10.0,
            currency="EUR",
            source="platform",
        )
        # Create manual asset (should NOT be removed)
        manual_asset = Asset(
            ticker="MANUAL_1",
            name="Manual Asset",
            platform="Degiro",
            quantity=1,
            current_price=100.0,
            currency="PLN",
            source="manual",
        )
        p3 = os.path.join(tmp_dir, "manual_1.md")
        manual_asset.save(p3)

        # Removal with active_paths = {p1}
        removed = remove_missing_platform_assets(
            vault_assets_dir=tmp_dir,
            platform="Degiro",
            active_asset_paths={p1},
            active_tickers={"ACTIVE_1"},
        )
        assert len(removed) == 1
        assert not os.path.exists(p2)
        assert os.path.exists(p1)
        assert os.path.exists(p3)

        # Safety check: empty active paths should not delete anything
        removed_empty = remove_missing_platform_assets(
            vault_assets_dir=tmp_dir,
            platform="Degiro",
            active_asset_paths=set(),
        )
        assert removed_empty == []
        assert os.path.exists(p1)
