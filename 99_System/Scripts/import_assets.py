import os
import sys
import argparse
from typing import Optional, Dict

# Ensure script directory is in sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

from platforms.degiro import import_degiro
from platforms.exante import import_exante, import_exante_api
from platforms.mbm import import_mbm, import_mbm_ike, import_mbm_ikze
from platforms.pkobp import import_pkobp
from platforms.common import load_import_config

SUPPORTED_PLATFORMS = {
    'degiro': ('Degiro', import_degiro),
    'exante': ('Exante', import_exante),
    'exante_api': ('Exante (API)', import_exante_api),
    'exante-api': ('Exante (API)', import_exante_api),
    'mbm': ('mBM', import_mbm),
    'mbm_ike': ('mBM (IKE)', import_mbm_ike),
    'mbm-ike': ('mBM (IKE)', import_mbm_ike),
    'ike': ('mBM (IKE)', import_mbm_ike),
    'mbm_ikze': ('mBM (IKZE)', import_mbm_ikze),
    'mbm-ikze': ('mBM (IKZE)', import_mbm_ikze),
    'ikze': ('mBM (IKZE)', import_mbm_ikze),
    'pkobp': ('PKOBP', import_pkobp),
    'pko': ('PKOBP', import_pkobp),
}


def detect_platform_from_path(file_path: str) -> str:
    """Recognize platform based on the file path.

    Checks directory names and file name in the path for supported platform names.
    Raises ValueError if the platform cannot be determined.
    """
    normalized = os.path.normpath(file_path).lower()

    # Check for PKO BP keywords
    if 'pkobp' in normalized or 'stanrachunku' in normalized or 'pko' in normalized:
        return 'PKOBP'

    # Check for mBM account-specific keywords first
    if 'ikze' in normalized:
        return 'mBM (IKZE)'
    if 'ike' in normalized:
        return 'mBM (IKE)'
    if 'mbm' in normalized:
        return 'mBM'

    # Check for known platform keywords in the path
    for key in ('degiro', 'exante'):
        display_name, _ = SUPPORTED_PLATFORMS[key]
        if key in normalized:
            return display_name


    supported_names = ", ".join(dict.fromkeys(name for name, _ in SUPPORTED_PLATFORMS.values()))
    raise ValueError(
        f"Could not recognize supported platform from file path '{file_path}'. "
        f"Supported platforms are: {supported_names}"
    )


def import_assets(
    platform: Optional[str] = None,
    file: Optional[str] = None,
    base_dir: Optional[str] = None,
    use_api: Optional[bool] = None,
    account_id: Optional[str] = None,
    max_workers: Optional[int] = None,
    show_progress: bool = True,
) -> Dict[str, int]:
    """Import positions from broker CSV exports or REST APIs into 10_Finance/Assets.
    All positions imported from broker platforms (Degiro, Exante, mBM) are assigned 'source: platform'.
    Existing platform assets for the imported platform are verified against the import file / API data,
    and any assets no longer present in the file are automatically removed.

    Parameters:
        platform: Optional platform name (e.g. 'degiro', 'exante', 'mbm', 'ike', 'ikze').
                  If unsupported, raises ValueError.
                  If not provided and file is not provided, imports all supported platforms.
        file: Optional CSV file path. Platform will be recognized from the file path,
              and the platform parameter will be discarded in that case.
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

    # If file is provided, recognize platform from file path and discard platform argument
    if file:
        if not os.path.exists(file):
            raise FileNotFoundError(f"File not found: {file}")

        detected_platform_name = detect_platform_from_path(file)
        platform_key = detected_platform_name.lower()
        if platform_key in SUPPORTED_PLATFORMS:
            display_name, handler = SUPPORTED_PLATFORMS[platform_key]
        else:
            # Fallback for compound display names
            if 'ikze' in platform_key:
                display_name, handler = 'mBM (IKZE)', import_mbm_ikze
            elif 'ike' in platform_key:
                display_name, handler = 'mBM (IKE)', import_mbm_ike
            else:
                display_name, handler = 'mBM', import_mbm

        print(f"Platform recognized as '{display_name}' from file path: {file}")
        if 'exante' in platform_key and 'api' not in platform_key:
            count = handler(csv_file_path=file, base_dir=base_dir, use_api=False, max_workers=max_workers, show_progress=show_progress)
        elif 'exante' in platform_key:
            count = handler(csv_file_path=file, base_dir=base_dir, max_workers=max_workers, show_progress=show_progress)
        elif 'pkobp' in platform_key:
            count = handler(file_path=file, base_dir=base_dir, max_workers=max_workers, show_progress=show_progress)
        else:
            count = handler(csv_file_path=file, base_dir=base_dir, max_workers=max_workers, show_progress=show_progress)
        return {display_name: count}

    # Resolve default import mode from config.yaml if not explicitly specified
    if use_api is None:
        cfg = load_import_config(base_dir)
        use_api = cfg.get("exante", {}).get("default_mode", "api").lower() == "api"

    # If platform is provided
    if platform:
        platform_key = platform.strip().lower()
        if platform_key not in SUPPORTED_PLATFORMS:
            supported_names = ", ".join(dict.fromkeys(name for name, _ in SUPPORTED_PLATFORMS.values()))
            raise ValueError(f"Unsupported platform: '{platform}'. Supported platforms are: {supported_names}")

        display_name, handler = SUPPORTED_PLATFORMS[platform_key]
        if platform_key in ('exante_api', 'exante-api') or (platform_key == 'exante' and use_api):
            print(f"\n--- Importing platform via API: {display_name} ---")
            count = import_exante_api(account_id=account_id, base_dir=base_dir, max_workers=max_workers, show_progress=show_progress)
            return {'Exante': count}
        else:
            if platform_key == 'exante':
                count = handler(csv_file_path=None, base_dir=base_dir, use_api=False, max_workers=max_workers, show_progress=show_progress)
            elif platform_key in ('pkobp', 'pko'):
                count = handler(file_path=None, base_dir=base_dir, max_workers=max_workers, show_progress=show_progress)
            else:
                count = handler(csv_file_path=None, base_dir=base_dir, max_workers=max_workers, show_progress=show_progress)
            return {display_name: count}

    # If neither platform nor file is provided, import for all platforms
    results = {}
    for key in ('degiro', 'exante', 'mbm', 'pkobp'):
        display_name, handler = SUPPORTED_PLATFORMS[key]
        print(f"\n--- Importing platform: {display_name} ---")
        if key == 'exante' and use_api:
            results[display_name] = import_exante_api(account_id=account_id, base_dir=base_dir, max_workers=max_workers, show_progress=show_progress)
        elif key == 'exante':
            results[display_name] = handler(csv_file_path=None, base_dir=base_dir, use_api=False, max_workers=max_workers, show_progress=show_progress)
        elif key == 'pkobp':
            results[display_name] = handler(file_path=None, base_dir=base_dir, max_workers=max_workers, show_progress=show_progress)
        else:
            results[display_name] = handler(csv_file_path=None, base_dir=base_dir, max_workers=max_workers, show_progress=show_progress)

    return results



def main():
    parser = argparse.ArgumentParser(description="Import assets from Degiro, Exante, and mBM (IKE & IKZE) CSV exports or Exante REST API.")
    parser.add_argument(
        "-p", "--platform",
        dest="platform",
        type=str,
        default=None,
        help="Broker platform to import (e.g., 'degiro', 'exante', 'mbm', 'ike', 'ikze', 'pkobp'). If omitted, imports all platforms."
    )
    parser.add_argument(
        "-f", "--file",
        dest="file",
        type=str,
        default=None,
        help="Path to CSV export file. Platform will be recognized from file path (platform arg will be discarded)."
    )
    parser.add_argument(
        "-a", "--api",
        dest="use_api",
        action="store_true",
        default=None,
        help="Fetch positions from Exante REST API (overrides config.yaml default_mode)."
    )
    parser.add_argument(
        "--csv",
        dest="use_csv",
        action="store_true",
        default=False,
        help="Force CSV import mode for Exante (overrides config.yaml default_mode)."
    )
    parser.add_argument(
        "--account",
        dest="account_id",
        type=str,
        default=None,
        help="Exante account ID for API import (optional, auto-detected if omitted)."
    )
    parser.add_argument(
        "-w", "--workers",
        dest="max_workers",
        type=int,
        default=None,
        help="Number of concurrent worker threads to use (defaults to CPU hardware threads count)."
    )
    parser.add_argument(
        "--no-progress",
        dest="no_progress",
        action="store_true",
        default=False,
        help="Disable interactive rich progress bars."
    )
    parser.add_argument(
        "positional_arg",
        nargs="?",
        default=None,
        help="Optional positional argument: can be a file path or platform name."
    )

    args = parser.parse_args()

    platform = args.platform
    file = args.file
    use_api = False if args.use_csv else (True if args.use_api else None)

    if args.positional_arg:
        pos = args.positional_arg
        if os.path.exists(pos) or os.path.sep in pos or '/' in pos or pos.lower().endswith(('.csv', '.xls', '.xlsx')):
            if not file:
                file = pos
        elif not platform and pos.lower() in SUPPORTED_PLATFORMS:
            platform = pos
        elif not platform and not file:
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


if __name__ == '__main__':
    main()

