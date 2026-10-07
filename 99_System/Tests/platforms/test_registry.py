"""Unit tests for PlatformRegistry and platform lifecycle management."""

import os
import tempfile

import platforms  # noqa: F401
from platforms.base import PlatformRegistry


def test_platform_registry_registered_platforms():
    """Verify that all platform extensions are registered in the registry."""
    all_platforms = PlatformRegistry.get_all()
    expected_ids = {"pko_bp_bonds", "mbank_ike", "mbank_ikze", "degiro", "exante"}
    assert expected_ids.issubset(set(all_platforms.keys()))


def test_platform_registry_aliases():
    """Verify that platform aliases resolve to the correct platform extension."""
    assert PlatformRegistry.get("pkobp").id == "pko_bp_bonds"
    assert PlatformRegistry.get("pko").id == "pko_bp_bonds"
    assert PlatformRegistry.get("ike").id == "mbank_ike"
    assert PlatformRegistry.get("ikze").id == "mbank_ikze"
    assert PlatformRegistry.get("deg").id == "degiro"
    assert PlatformRegistry.get("ex").id == "exante"


def test_platform_path_detection():
    """Verify that file paths are accurately mapped to platform extensions."""
    # Standard raw folder paths
    pko = PlatformRegistry.detect_platform_from_path("00_Raw/pko_bp_bonds/export.xls")
    assert pko.id == "pko_bp_bonds"

    ike = PlatformRegistry.detect_platform_from_path("00_Raw/mbank_ike/export.csv")
    assert ike.id == "mbank_ike"

    ikze = PlatformRegistry.detect_platform_from_path("00_Raw/mbank_ikze/export.csv")
    assert ikze.id == "mbank_ikze"

    degiro = PlatformRegistry.detect_platform_from_path("00_Raw/degiro/portfolio.csv")
    assert degiro.id == "degiro"

    exante = PlatformRegistry.detect_platform_from_path("00_Raw/exante/statement.csv")
    assert exante.id == "exante"

    # Legacy keywords detection
    assert PlatformRegistry.detect_platform_from_path("00_Raw/pkobp/StanRachunku.xls").id == "pko_bp_bonds"
    assert PlatformRegistry.detect_platform_from_path("00_Raw/mBM/ikze-2026.csv").id == "mbank_ikze"
    assert PlatformRegistry.detect_platform_from_path("00_Raw/mBM/ike-2026.csv").id == "mbank_ike"


def test_platform_enable_disable_in_config():
    """Verify programmatic enabling and disabling of platforms in config.yaml."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        sys_dir = os.path.join(tmp_dir, "99_System")
        os.makedirs(sys_dir, exist_ok=True)
        cfg_file = os.path.join(sys_dir, "config.yaml")

        with open(cfg_file, "w", encoding="utf-8") as f:
            f.write("platforms:\n  degiro:\n    enabled: true\n  exante:\n    enabled: true\n")

        # Disable degiro
        assert PlatformRegistry.set_platform_enabled("degiro", False, base_dir=tmp_dir) is True
        enabled = PlatformRegistry.get_enabled(base_dir=tmp_dir)
        assert "degiro" not in enabled
        assert "exante" in enabled

        # Re-enable degiro
        assert PlatformRegistry.set_platform_enabled("degiro", True, base_dir=tmp_dir) is True
        enabled_after = PlatformRegistry.get_enabled(base_dir=tmp_dir)
        assert "degiro" in enabled_after
