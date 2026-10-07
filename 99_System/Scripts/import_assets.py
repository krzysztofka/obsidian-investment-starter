"""Unified asset import dispatcher powered by PlatformRegistry."""

import argparse
import os
import sys

# Ensure script directory is in sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

# Ensure all platforms are loaded into registry
import platforms  # noqa: F401
from platforms.base import PlatformRegistry

# Backward-compatible map for external code
SUPPORTED_PLATFORMS = {
    "pko_bp_bonds": ("PKO BP (Bonds)", platforms.import_pko_bp_bonds),
    "pkobp": ("PKO BP (Bonds)", platforms.import_pkobp),
    "pko": ("PKO BP (Bonds)", platforms.import_pkobp),
    "mbank_ike": ("mBank (IKE)", platforms.import_mbank_ike),
    "ike": ("mBank (IKE)", platforms.import_mbank_ike),
    "mbm_ike": ("mBank (IKE)", platforms.import_mbm_ike),
    "mbank_ikze": ("mBank (IKZE)", platforms.import_mbank_ikze),
    "ikze": ("mBank (IKZE)", platforms.import_mbank_ikze),
    "mbm_ikze": ("mBank (IKZE)", platforms.import_mbm_ikze),
    "mbm": ("mBM", platforms.import_mbm),
    "degiro": ("Degiro", platforms.import_degiro),
    "exante": ("Exante", platforms.import_exante),
    "exante_api": ("Exante (API)", platforms.import_exante_api),
    "exante-api": ("Exante (API)", platforms.import_exante_api),
}


def detect_platform_from_path(file_path: str, base_dir: str | None = None) -> str:
    """Recognize platform name based on the file path using PlatformRegistry."""
    platform = PlatformRegistry.detect_platform_from_path(file_path, base_dir=base_dir)
    return platform.display_name


def import_assets(
    platform: str | None = None,
    file: str | None = None,
    base_dir: str | None = None,
    use_api: bool | None = None,
    account_id: str | None = None,
    max_workers: int | None = None,
    show_progress: bool = True,
) -> dict[str, int]:
    """Import positions from broker CSV/XLS exports or REST APIs into 10_Finance/Assets.
    All positions imported from platforms are assigned 'source: platform'.
    Existing platform assets for the imported platform are verified against the import data,
    and any assets no longer present are automatically removed.

    Parameters:
        platform: Optional platform name or alias (e.g. 'pko_bp_bonds', 'mbank_ike', 'mbank_ikze', 'degiro', 'exante').
                  If not provided and file is not provided, imports all ENABLED platforms from config.yaml.
        file: Optional export file path. Platform will be auto-detected from the file path.
        base_dir: Optional repository base directory path.
        use_api: If True, uses Exante REST API for Exante positions. If None, resolves from config.yaml.
        account_id: Optional Exante account ID for API import.
        max_workers: Optional number of concurrent worker threads.
        show_progress: Whether to display a real-time Rich progress bar during imports.

    Returns:
        Dict mapping platform name to count of imported assets.
    """
    if base_dir is None:
        base_dir = os.path.abspath(os.path.join(script_dir, "../.."))

    # 1. Target single file specified
    if file:
        if not os.path.exists(file):
            raise FileNotFoundError(f"File not found: {file}")

        matched_platform = PlatformRegistry.detect_platform_from_path(file, base_dir=base_dir)
        print(f"Platform recognized as '{matched_platform.display_name}' from file path: {file}")
        count = matched_platform.run_import(
            file_path=file,
            use_api=use_api,
            account_id=account_id,
            max_workers=max_workers,
            show_progress=show_progress,
        )
        return {matched_platform.display_name: count}

    # 2. Target specific platform specified
    if platform:
        p_obj = PlatformRegistry.get(platform, base_dir=base_dir)
        if not p_obj:
            # Handle legacy compound names like 'mbm'
            if platform.lower().strip() == "mbm":
                p_ike = PlatformRegistry.get("mbank_ike", base_dir=base_dir)
                p_ikze = PlatformRegistry.get("mbank_ikze", base_dir=base_dir)
                c_ike = (
                    p_ike.run_import(
                        use_api=use_api, account_id=account_id, max_workers=max_workers, show_progress=show_progress
                    )
                    if p_ike
                    else 0
                )
                c_ikze = (
                    p_ikze.run_import(
                        use_api=use_api, account_id=account_id, max_workers=max_workers, show_progress=show_progress
                    )
                    if p_ikze
                    else 0
                )
                return {"mBank (IKE)": c_ike, "mBank (IKZE)": c_ikze}

            supported_names = ", ".join(p.display_name for p in PlatformRegistry.get_all(base_dir=base_dir).values())
            raise ValueError(f"Unsupported platform: '{platform}'. Supported platforms are: {supported_names}")

        print(f"\n--- Importing platform: {p_obj.display_name} ---")
        count = p_obj.run_import(
            file_path=None,
            use_api=use_api,
            account_id=account_id,
            max_workers=max_workers,
            show_progress=show_progress,
        )
        return {p_obj.display_name: count}

    # 3. Import all ENABLED platforms from config.yaml
    enabled_platforms = PlatformRegistry.get_enabled(base_dir=base_dir)
    if not enabled_platforms:
        print("Notice: No platforms are currently enabled in config.yaml.")
        return {}

    results = {}
    for pid, p_obj in enabled_platforms.items():
        print(f"\n--- Importing platform: {p_obj.display_name} ---")
        count = p_obj.run_import(
            file_path=None,
            use_api=use_api,
            account_id=account_id,
            max_workers=max_workers,
            show_progress=show_progress,
        )
        results[p_obj.display_name] = count

    return results


def main():
    parser = argparse.ArgumentParser(description="Import assets from enabled broker platform extensions or REST APIs.")
    parser.add_argument(
        "-p",
        "--platform",
        dest="platform",
        type=str,
        default=None,
        help="Broker platform to import (e.g., 'pko_bp_bonds', 'mbank_ike', 'mbank_ikze', 'degiro', 'exante'). If omitted, imports all enabled platforms.",
    )
    parser.add_argument(
        "-f",
        "--file",
        dest="file",
        type=str,
        default=None,
        help="Path to CSV/XLS export file. Platform will be recognized from file path (platform arg will be discarded).",
    )
    parser.add_argument(
        "-a",
        "--api",
        dest="use_api",
        action="store_true",
        default=None,
        help="Fetch positions from Exante REST API (overrides config.yaml default_mode).",
    )
    parser.add_argument(
        "--csv",
        dest="use_csv",
        action="store_true",
        default=False,
        help="Force CSV import mode for Exante (overrides config.yaml default_mode).",
    )
    parser.add_argument(
        "--account",
        dest="account_id",
        type=str,
        default=None,
        help="Exante account ID for API import (optional, auto-detected if omitted).",
    )
    parser.add_argument(
        "-w",
        "--workers",
        dest="max_workers",
        type=int,
        default=None,
        help="Number of concurrent worker threads to use.",
    )
    parser.add_argument(
        "--no-progress",
        dest="no_progress",
        action="store_true",
        default=False,
        help="Disable interactive rich progress bars.",
    )
    parser.add_argument(
        "--list-platforms", action="store_true", help="List available platform extensions and their enabled status."
    )
    parser.add_argument(
        "positional_arg",
        nargs="?",
        default=None,
        help="Optional positional argument: can be a file path or platform name.",
    )

    args = parser.parse_args()

    if args.list_platforms:
        print("\nRegistered Platform Extensions:")
        print(f"{'ID':<16} {'Display Name':<20} {'Raw Folder':<16} {'Enabled':<10}")
        print("-" * 65)
        for item in PlatformRegistry.list_platforms():
            status = "✓ Yes" if item["enabled"] else "✗ No"
            print(f"{item['id']:<16} {item['display_name']:<20} {item['raw_folder']:<16} {status:<10}")
        print()
        return

    platform = args.platform
    file = args.file
    use_api = False if args.use_csv else (True if args.use_api else None)

    if args.positional_arg:
        pos = args.positional_arg
        if os.path.exists(pos) or os.path.sep in pos or "/" in pos or pos.lower().endswith((".csv", ".xls", ".xlsx")):
            if not file:
                file = pos
        elif not platform:
            platform = pos

    try:
        import_assets(
            platform=platform,
            file=file,
            use_api=use_api,
            account_id=args.account_id,
            max_workers=args.max_workers,
            show_progress=not args.no_progress,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
