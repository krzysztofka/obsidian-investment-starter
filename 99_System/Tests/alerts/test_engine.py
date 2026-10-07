"""Unit tests for AlertEngine orchestrator and tag manager."""

import os
import tempfile

from alerts.engine import AlertEngine
from model.asset import Asset


def test_alert_engine_default_rules():
    engine = AlertEngine()
    assert len(engine.rules) >= 5
    rule_names = [r.name for r in engine.rules]
    assert "Overvalued" in rule_names
    assert "Delisting Risk" in rule_names
    assert "Allocation Drift" in rule_names
    assert "Stop Loss" in rule_names


def test_alert_engine_run_and_tag_updating():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create an overvalued asset
        asset1 = Asset(
            ticker="OVER",
            name="Overvalued Stock",
            platform="Degiro",
            asset_type="equity",
            current_price=100.0,
            value_pln=10000.0,
            pe_ratio=55.0,
            tags=[],
        )
        p1 = os.path.join(tmp_dir, "asset1.md")
        asset1.save(p1)

        # Create an un-flagged normal asset
        asset2 = Asset(
            ticker="NORM",
            name="Normal Stock",
            platform="Degiro",
            asset_type="equity",
            current_price=50.0,
            value_pln=5000.0,
            pe_ratio=15.0,
            tags=[],
        )
        p2 = os.path.join(tmp_dir, "asset2.md")
        asset2.save(p2)

        config = {
            "alerts": {
                "overvalued": {"enabled": True, "max_pe_ratio": 40.0},
                "delisting_risk": {"enabled": False},
                "allocation_drift": {"enabled": False},
                "stop_loss": {"enabled": False},
                "insider_selling": {"enabled": False},
                "macro_yield_curve": {"enabled": False},
            }
        }

        engine = AlertEngine(config=config)
        res = engine.run(assets_dir=tmp_dir, save=True)

        assert res["scanned"] == 2
        assert res["updated"] >= 1

        # Check that asset1 received #alert/overvalued tag
        updated1 = Asset.from_file(p1)
        assert "#alert/overvalued" in updated1.tags

        # Check that asset2 did not receive the tag
        updated2 = Asset.from_file(p2)
        assert "#alert/overvalued" not in updated2.tags

        # Now update asset1 P/E to normal and rerun: the tag should be cleared
        updated1.pe_ratio = 20.0
        updated1.save(p1)

        engine.run(assets_dir=tmp_dir, save=True)
        cleared1 = Asset.from_file(p1)
        assert "#alert/overvalued" not in cleared1.tags


def test_alert_engine_rule_filter():
    with tempfile.TemporaryDirectory() as tmp_dir:
        asset = Asset(
            ticker="TEST",
            name="Test Stock",
            platform="Degiro",
            asset_type="equity",
            pe_ratio=60.0,
        )
        p = os.path.join(tmp_dir, "test.md")
        asset.save(p)

        engine = AlertEngine()
        # Running with a non-matching rule filter should not evaluate overvalued rule
        res = engine.run(assets_dir=tmp_dir, save=False, rule_filter="stop_loss")
        assert res["scanned"] == 1
