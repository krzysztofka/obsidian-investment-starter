"""Vault Patch Engine.

Discovers and executes sequential version patches to upgrade a downstream vault
from an upstream starter while protecting personal investment data and custom configurations.
"""

import importlib.util
import os
import sys
from typing import Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_SOURCE_VAULT = os.path.abspath(os.path.join(SCRIPTS_ROOT, "../.."))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def get_vault_version(vault_path: str) -> str:
    """Read vault version from .vault_version or infer from codebase."""
    version_file = os.path.join(vault_path, ".vault_version")
    if os.path.exists(version_file):
        try:
            with open(version_file, encoding="utf-8") as f:
                ver = f.read().strip()
                if ver:
                    return ver
        except Exception:
            pass

    # Fallback inference: if vault has 99_System or run.py, it's at least v0.5.0
    if os.path.exists(os.path.join(vault_path, "run.py")) or os.path.exists(os.path.join(vault_path, "99_System")):
        return "0.5.0"

    return "0.0.0"


def discover_patches() -> list[dict[str, Any]]:
    """Discover available patch modules in patches/ directory."""
    patches_dir = os.path.join(SCRIPT_DIR, "patches")
    if not os.path.exists(patches_dir):
        return []

    patches = []
    for fname in sorted(os.listdir(patches_dir)):
        if fname.startswith("patch_") and fname.endswith(".py"):
            mod_path = os.path.join(patches_dir, fname)
            mod_name = f"patch.patches.{fname[:-3]}"
            try:
                spec = importlib.util.spec_from_file_location(mod_name, mod_path)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    from_v = getattr(mod, "FROM_VERSION", None)
                    to_v = getattr(mod, "TO_VERSION", None)
                    desc = getattr(mod, "DESCRIPTION", "")
                    apply_fn = getattr(mod, "apply", None)
                    if from_v and to_v and callable(apply_fn):
                        patches.append(
                            {
                                "from_version": from_v,
                                "to_version": to_v,
                                "description": desc,
                                "apply": apply_fn,
                                "file": fname,
                            }
                        )
            except Exception as e:
                print(f"Warning: could not load patch {fname}: {e}")

    return patches


def build_patch_pipeline(
    current_version: str,
    target_version: str,
    available_patches: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build a linear chain of patches from current_version to target_version."""
    pipeline = []
    curr = current_version

    while curr != target_version:
        matched = None
        for p in available_patches:
            if p["from_version"] == curr:
                matched = p
                break

        if not matched:
            break

        pipeline.append(matched)
        curr = matched["to_version"]

    return pipeline


class PatchEngine:
    """Manages vault migrations and version patching."""

    def __init__(self, source_vault: str | None = None):
        self.source_vault = os.path.abspath(source_vault or DEFAULT_SOURCE_VAULT)
        self.source_version = get_vault_version(self.source_vault)
        self.patches = discover_patches()

    def list_patches(self):
        """Display all registered patches."""
        print(f"📋 Registered Patches (Starter Source: {self.source_vault} | Current: v{self.source_version}):")
        if not self.patches:
            print("   No patches registered.")
            return

        for p in self.patches:
            print(f"   • {p['from_version']} -> {p['to_version']}: {p['description']} ({p['file']})")

    def run_patch(
        self,
        target_vault: str,
        dry_run: bool = False,
        force: bool = False,
    ) -> bool:
        """Run sequential patches against target_vault."""
        target_vault = os.path.abspath(target_vault)
        if not os.path.exists(target_vault):
            print(f"Error: Target vault directory does not exist: {target_vault}")
            return False

        target_version = get_vault_version(target_vault)
        starter_version = self.source_version

        print("=" * 72)
        print("🔧 VAULT PATCH & MIGRATION ENGINE")
        print("=" * 72)
        print(f"📁 Upstream Starter : {self.source_vault} (v{starter_version})")
        print(f"🎯 Target Vault     : {target_vault} (v{target_version})")
        print(f"⚡ Mode             : {'[DRY-RUN]' if dry_run else '[LIVE UPDATE]'}")
        print("=" * 72)

        if target_version == starter_version and not force:
            print(f"\n✅ Target vault is already at latest version (v{target_version}).")
            print("   No updates required. Use --force to re-apply latest patch.")
            return True

        pipeline = build_patch_pipeline(target_version, starter_version, self.patches)

        if not pipeline:
            if force and self.patches:
                print("\n⚡ Force mode active: selecting most recent patch.")
                pipeline = [self.patches[-1]]
            else:
                print(f"\n⚠️  No valid patch chain found from v{target_version} to v{starter_version}.")
                return False

        print(f"\n🚀 Found {len(pipeline)} patch(es) to apply:")
        for idx, p in enumerate(pipeline, 1):
            print(f"   [{idx}/{len(pipeline)}] {p['from_version']} -> {p['to_version']}: {p['description']}")

        for idx, p in enumerate(pipeline, 1):
            success = p["apply"](self.source_vault, target_vault, dry_run=dry_run)
            if not success:
                print(f"\n❌ Patch {p['from_version']} -> {p['to_version']} failed.")
                return False

        print("\n" + "=" * 72)
        if dry_run:
            print(f"✨ [DRY-RUN] All {len(pipeline)} patch step(s) simulated successfully.")
        else:
            final_version = get_vault_version(target_vault)
            print(f"✨ All {len(pipeline)} patch(es) applied successfully! Vault upgraded to v{final_version}.")
        print("=" * 72)
        return True


def run_patch(
    target_vault: str | None = None,
    source_vault: str | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> bool:
    """Convenience function to run the patch engine."""
    engine = PatchEngine(source_vault=source_vault)
    target = target_vault or engine.source_vault
    return engine.run_patch(target_vault=target, dry_run=dry_run, force=force)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Vault Patch & Migration Engine.")
    parser.add_argument(
        "-t",
        "--target",
        dest="target",
        type=str,
        default=None,
        help="Target vault path to upgrade. Defaults to current vault.",
    )
    parser.add_argument(
        "-s",
        "--source",
        dest="source",
        type=str,
        default=None,
        help="Upstream starter vault path. Defaults to this repository.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate patch execution without modifying any files.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-applying patch even if version matches.",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List available patches and exit.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="Display current vault version and exit.",
    )

    args = parser.parse_args()

    engine = PatchEngine(source_vault=args.source)

    if args.version:
        target = args.target or engine.source_vault
        print(f"Vault Version: v{get_vault_version(target)} ({target})")
        sys.exit(0)

    if args.list:
        engine.list_patches()
        sys.exit(0)

    target_path = args.target or engine.source_vault
    ok = engine.run_patch(target_vault=target_path, dry_run=args.dry_run, force=args.force)
    sys.exit(0 if ok else 1)
