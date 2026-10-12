"""Unit tests for Vault Patch Engine and Sequential Migration System."""

import os
import sys
import tempfile

# Ensure scripts dir is on sys.path
SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from patch.patch_engine import (
    PatchEngine,
    build_patch_pipeline,
    discover_patches,
    get_vault_version,
)


def test_get_vault_version():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Default empty directory
        assert get_vault_version(tmp_dir) == "0.0.0"

        # Directory with run.py but no version file
        with open(os.path.join(tmp_dir, "run.py"), "w", encoding="utf-8") as f:
            f.write("# dummy")
        assert get_vault_version(tmp_dir) == "0.5.0"

        # Explicit .vault_version
        with open(os.path.join(tmp_dir, ".vault_version"), "w", encoding="utf-8") as f:
            f.write("0.6.0\n")
        assert get_vault_version(tmp_dir) == "0.6.0"


def test_discover_patches():
    patches = discover_patches()
    assert len(patches) >= 3
    p06 = next((p for p in patches if p["from_version"] == "0.5.0" and p["to_version"] == "0.6.0"), None)
    assert p06 is not None
    assert callable(p06["apply"])

    p07 = next((p for p in patches if p["from_version"] == "0.6.0" and p["to_version"] == "0.7.0"), None)
    assert p07 is not None
    assert callable(p07["apply"])

    p08 = next((p for p in patches if p["from_version"] == "0.7.0" and p["to_version"] == "0.8.0"), None)
    assert p08 is not None
    assert callable(p08["apply"])


def test_build_patch_pipeline():
    mock_patches = [
        {"from_version": "0.5.0", "to_version": "0.6.0", "description": "0.5 -> 0.6"},
        {"from_version": "0.6.0", "to_version": "0.7.0", "description": "0.6 -> 0.7"},
        {"from_version": "0.7.0", "to_version": "0.8.0", "description": "0.7 -> 0.8"},
    ]

    pipeline = build_patch_pipeline("0.5.0", "0.8.0", mock_patches)
    assert len(pipeline) == 3
    assert pipeline[0]["from_version"] == "0.5.0"
    assert pipeline[1]["from_version"] == "0.6.0"
    assert pipeline[2]["from_version"] == "0.7.0"

    # Already up-to-date
    assert build_patch_pipeline("0.8.0", "0.8.0", mock_patches) == []


def test_patch_application_and_private_data_preservation():
    vault_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    with tempfile.TemporaryDirectory() as mock_target:
        # Setup mock downstream vault with private user data and old v0.5 state
        os.makedirs(os.path.join(mock_target, "10_Finance", "Assets"), exist_ok=True)
        os.makedirs(os.path.join(mock_target, "00_Raw", "Degiro"), exist_ok=True)
        os.makedirs(os.path.join(mock_target, "20_Decisions"), exist_ok=True)
        os.makedirs(os.path.join(mock_target, "99_System", "Scripts"), exist_ok=True)

        # 1. Private files
        my_asset = os.path.join(mock_target, "10_Finance", "Assets", "my_private_stock.md")
        with open(my_asset, "w", encoding="utf-8") as f:
            f.write("---\nticker: PRIV\nportfolio: aggressive\n---\n# My Secret Stock\n")

        my_raw = os.path.join(mock_target, "00_Raw", "Degiro", "my_private_statement.csv")
        with open(my_raw, "w", encoding="utf-8") as f:
            f.write("Secret private CSV content\n")

        my_env = os.path.join(mock_target, ".env")
        with open(my_env, "w", encoding="utf-8") as f:
            f.write("FINNHUB_API_KEY=supersecret123\n")

        # 2. Legacy todo.md (should be removed from downstream vault)
        target_todo = os.path.join(mock_target, "todo.md")
        with open(target_todo, "w", encoding="utf-8") as f:
            f.write("# Legacy Backlog\n")

        # 3. Custom config.yaml (must be preserved!)
        custom_cfg = os.path.join(mock_target, "99_System", "config.yaml")
        with open(custom_cfg, "w", encoding="utf-8") as f:
            f.write("custom_user_setting: true\n")

        # 4. Old version marker
        with open(os.path.join(mock_target, ".vault_version"), "w", encoding="utf-8") as f:
            f.write("0.5.0\n")

        # 5. Legacy test clutter in downstream vault
        mock_tests_dir = os.path.join(mock_target, "99_System", "Tests")
        os.makedirs(mock_tests_dir, exist_ok=True)
        with open(os.path.join(mock_tests_dir, "test_mock.py"), "w", encoding="utf-8") as f:
            f.write("# mock test")

        mock_pytest_cache = os.path.join(mock_target, ".pytest_cache")
        os.makedirs(mock_pytest_cache, exist_ok=True)
        with open(os.path.join(mock_pytest_cache, "cache.json"), "w", encoding="utf-8") as f:
            f.write("{}")

        # Run patch
        engine = PatchEngine(source_vault=vault_root)
        success = engine.run_patch(target_vault=mock_target, dry_run=False)
        assert success is True

        # VERIFICATIONS:
        # A. Private data strictly preserved
        assert os.path.exists(my_asset)
        with open(my_asset, encoding="utf-8") as f:
            assert "My Secret Stock" in f.read()

        assert os.path.exists(my_raw)
        with open(my_raw, encoding="utf-8") as f:
            assert "Secret private CSV content" in f.read()

        assert os.path.exists(my_env)
        with open(my_env, encoding="utf-8") as f:
            assert "supersecret123" in f.read()

        # B. Custom config preserved
        assert os.path.exists(custom_cfg)
        with open(custom_cfg, encoding="utf-8") as f:
            assert "custom_user_setting: true" in f.read()

        # C. Downstream todo.md deleted
        assert not os.path.exists(target_todo)

        # D. System scripts updated
        assert os.path.exists(os.path.join(mock_target, "99_System", "Scripts", "patch", "patch_engine.py"))
        assert os.path.exists(os.path.join(mock_target, "00_Raw", "pkobp"))

        # E. Downstream test decoupling & cache cleanup verified
        assert not os.path.exists(mock_tests_dir)
        assert not os.path.exists(mock_pytest_cache)

        # F. Version upgraded to upstream starter version (0.8.0)
        assert get_vault_version(mock_target) == "0.8.0"


def test_downstream_test_decoupling_and_cache_pruning():
    vault_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    from patch.patches.patch_0_7_to_0_8 import apply as apply_07_to_08

    with tempfile.TemporaryDirectory() as mock_downstream:
        # 1. Setup downstream vault at 0.7.0 with legacy test directories & caches
        os.makedirs(os.path.join(mock_downstream, "99_System", "Scripts"), exist_ok=True)
        os.makedirs(os.path.join(mock_downstream, "99_System", "Tests"), exist_ok=True)
        os.makedirs(os.path.join(mock_downstream, "99_System", ".pytest_cache"), exist_ok=True)
        os.makedirs(os.path.join(mock_downstream, "tests"), exist_ok=True)
        os.makedirs(os.path.join(mock_downstream, ".pytest_cache"), exist_ok=True)
        os.makedirs(os.path.join(mock_downstream, "htmlcov"), exist_ok=True)

        with open(os.path.join(mock_downstream, ".vault_version"), "w", encoding="utf-8") as f:
            f.write("0.7.0\n")

        with open(os.path.join(mock_downstream, "99_System", "Tests", "test_sample.py"), "w", encoding="utf-8") as f:
            f.write("# sample test")

        with open(os.path.join(mock_downstream, "todo.md"), "w", encoding="utf-8") as f:
            f.write("# Backlog")

        with open(os.path.join(mock_downstream, ".coverage"), "w", encoding="utf-8") as f:
            f.write("coverage data")

        # Test Dry Run first
        res_dry = apply_07_to_08(vault_root, mock_downstream, dry_run=True)
        assert res_dry is True
        # In dry run, files should still exist
        assert os.path.exists(os.path.join(mock_downstream, "99_System", "Tests"))
        assert os.path.exists(os.path.join(mock_downstream, ".pytest_cache"))
        assert get_vault_version(mock_downstream) == "0.7.0"

        # Apply Live Patch
        res_live = apply_07_to_08(vault_root, mock_downstream, dry_run=False)
        assert res_live is True

        # Assert tests, caches, and backlog are thoroughly pruned
        assert not os.path.exists(os.path.join(mock_downstream, "99_System", "Tests"))
        assert not os.path.exists(os.path.join(mock_downstream, "tests"))
        assert not os.path.exists(os.path.join(mock_downstream, ".pytest_cache"))
        assert not os.path.exists(os.path.join(mock_downstream, "99_System", ".pytest_cache"))
        assert not os.path.exists(os.path.join(mock_downstream, ".coverage"))
        assert not os.path.exists(os.path.join(mock_downstream, "htmlcov"))
        assert not os.path.exists(os.path.join(mock_downstream, "todo.md"))

        # Assert scripts were synced but Tests was NOT re-created
        assert os.path.exists(os.path.join(mock_downstream, "99_System", "Scripts", "health_check.py"))
        assert not os.path.exists(os.path.join(mock_downstream, "99_System", "Tests"))

        # Assert version updated to 0.8.0
        assert get_vault_version(mock_downstream) == "0.8.0"


def test_upstream_starter_tests_protected_when_target_is_same():
    """Ensure running patch when source == target does NOT delete upstream tests."""
    from patch.patches.patch_0_7_to_0_8 import apply as apply_07_to_08

    # We simulate this in a temporary folder representing upstream starter
    with tempfile.TemporaryDirectory() as mock_upstream:
        os.makedirs(os.path.join(mock_upstream, "99_System", "Tests"), exist_ok=True)
        os.makedirs(os.path.join(mock_upstream, "99_System", "Scripts"), exist_ok=True)
        test_file = os.path.join(mock_upstream, "99_System", "Tests", "test_upstream.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("# Upstream test suite")

        with open(os.path.join(mock_upstream, ".vault_version"), "w", encoding="utf-8") as f:
            f.write("0.7.0\n")

        # Run patch where source == target
        res = apply_07_to_08(mock_upstream, mock_upstream, dry_run=False)
        assert res is True

        # Upstream tests MUST remain intact!
        assert os.path.exists(test_file)
        assert os.path.exists(os.path.join(mock_upstream, "99_System", "Tests"))
