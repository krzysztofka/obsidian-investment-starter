"""mBank IKZE Platform Extension."""

import os
import sys

# Ensure scripts directory is in sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_scripts_dir = os.path.dirname(script_dir)
if parent_scripts_dir not in sys.path:
    sys.path.append(parent_scripts_dir)

from platforms.base import BasePlatform, PlatformRegistry
from platforms.mbank_common import import_mbank_account_positions


def import_mbm_ikze(
    csv_file_path: str | None = None,
    base_dir: str | None = None,
    max_workers: int | None = None,
    show_progress: bool = True,
) -> int:
    """Import positions from mBank IKZE CSV export."""
    return import_mbank_account_positions(
        csv_file_path=csv_file_path,
        account_type="ikze",
        raw_folder_name="mbank_ikze",
        base_dir=base_dir,
        max_workers=max_workers,
        show_progress=show_progress,
    )


# Function alias
import_mbank_ikze = import_mbm_ikze


@PlatformRegistry.register
class MbankIkzePlatform(BasePlatform):
    """mBank eMakler IKZE Account Extension."""

    id = "mbank_ikze"
    display_name = "mBank (IKZE)"
    raw_folder = "mbank_ikze"
    default_mode = "csv"
    aliases = ["ikze", "mbm_ikze", "mbm-ikze"]

    def can_handle_file(self, file_path: str) -> bool:
        norm = os.path.normpath(file_path).lower()
        if "mbank_ikze" in norm:
            return True
        if "ikze" in norm:
            return True
        return False

    def run_import(
        self,
        file_path: str | None = None,
        use_api: bool | None = None,
        account_id: str | None = None,
        max_workers: int | None = None,
        show_progress: bool = True,
    ) -> int:
        return import_mbank_ikze(
            csv_file_path=file_path,
            base_dir=self.base_dir,
            max_workers=max_workers,
            show_progress=show_progress,
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Import assets from mBank IKZE CSV export.")
    parser.add_argument("-f", "--file", dest="file", type=str, default=None, help="Path to mBank IKZE CSV file.")
    parser.add_argument("-w", "--workers", dest="max_workers", type=int, default=None, help="Number of worker threads.")
    parser.add_argument("positional_file", nargs="?", default=None, help="Optional mBank IKZE CSV file path.")

    args = parser.parse_args()
    target_file = args.file or args.positional_file
    import_mbank_ikze(csv_file_path=target_file, max_workers=args.max_workers)
