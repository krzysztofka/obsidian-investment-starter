"""Interactive Vault Scaffolding & Initial Setup Engine.

Guides the user step-by-step through configuring a new personal investment vault
bootstrapped from the starter repository.
"""

import os
import sys
import shutil
from typing import Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_ROOT = SCRIPT_DIR
VAULT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def init_vault(
    target_vault: Optional[str] = None,
    interactive: bool = True,
) -> bool:
    """Initialize or configure a vault step-by-step."""
    target_dir = os.path.abspath(target_vault or VAULT_ROOT)

    print("=" * 72)
    print("🚀  INVESTMENT SECOND BRAIN — VAULT INITIALIZER")
    print("=" * 72)
    print(f"📁 Target Vault Directory: {target_dir}")
    print("=" * 72)
    print()

    # 1. Directory Structure Scaffolding
    print("Step 1: Creating vault directory structure...")
    dirs_to_create = [
        "00_Raw/Degiro",
        "00_Raw/Exante",
        "00_Raw/mBM",
        "00_Raw/pkobp",
        "00_Raw/Articles",
        "10_Finance/Assets",
        "10_Finance/ETF_Holdings",
        "10_Finance/History",
        "10_Finance/Watchlist",
        "20_Decisions",
        "99_System/Scripts",
        "99_System/Templates",
        "99_System/Views",
        "99_System/docs",
    ]
    for rel_d in dirs_to_create:
        dpath = os.path.join(target_dir, rel_d)
        os.makedirs(dpath, exist_ok=True)
        # Keep empty directories in git
        gitkeep = os.path.join(dpath, ".gitkeep")
        if not os.path.exists(gitkeep) and not os.listdir(dpath):
            with open(gitkeep, "w", encoding="utf-8") as f:
                f.write("")
    print("   ✓ All core directories verified.")

    # 2. Set .vault_version
    print("\nStep 2: Initializing vault version...")
    starter_version_file = os.path.join(VAULT_ROOT, ".vault_version")
    starter_version = "0.6.0"
    if os.path.exists(starter_version_file):
        try:
            with open(starter_version_file, "r", encoding="utf-8") as f:
                starter_version = f.read().strip() or "0.6.0"
        except Exception:
            pass

    target_version_file = os.path.join(target_dir, ".vault_version")
    with open(target_version_file, "w", encoding="utf-8") as f:
        f.write(f"{starter_version}\n")
    print(f"   ✓ Vault version set to v{starter_version}")

    # 3. Environment variables configuration (.env)
    print("\nStep 3: Environment configuration (.env)...")
    env_target = os.path.join(target_dir, ".env")
    env_example = os.path.join(VAULT_ROOT, ".env.example")

    if not os.path.exists(env_target):
        if os.path.exists(env_example):
            shutil.copy2(env_example, env_target)
            print("   ✓ Copied .env.example -> .env")
        else:
            with open(env_target, "w", encoding="utf-8") as f:
                f.write("# Environment Configuration\nFINNHUB_API_KEY=\nEXANTE_API_KEY=\nEXANTE_API_SECRET=\n")
            print("   ✓ Created initial .env file")
    else:
        print("   ✓ Existing .env preserved.")

    # 4. Gitignore configuration
    print("\nStep 4: Ensuring .gitignore configuration...")
    gitignore_target = os.path.join(target_dir, ".gitignore")
    gitignore_source = os.path.join(VAULT_ROOT, ".gitignore")
    if not os.path.exists(gitignore_target) and os.path.exists(gitignore_source):
        shutil.copy2(gitignore_source, gitignore_target)
        print("   ✓ Initialized .gitignore")
    else:
        print("   ✓ .gitignore present.")

    # 5. Core Configuration (config.yaml)
    print("\nStep 5: Verifying config.yaml...")
    config_target = os.path.join(target_dir, "config.yaml")
    config_source = os.path.join(VAULT_ROOT, "config.yaml")
    if not os.path.exists(config_target) and os.path.exists(config_source):
        shutil.copy2(config_source, config_target)
        print("   ✓ Initialized config.yaml")
    else:
        print("   ✓ config.yaml present.")

    # 6. Python Environment Diagnostics
    print("\nStep 6: Checking Python dependencies...")
    required_packages = [
        ("requests", "requests"),
        ("yaml", "PyYAML"),
        ("pydantic", "pydantic"),
        ("yfinance", "yfinance"),
        ("bs4", "beautifulsoup4"),
        ("rich", "rich"),
        ("xlrd", "xlrd"),
    ]
    missing = []
    for mod_name, pkg_name in required_packages:
        try:
            __import__(mod_name)
        except ImportError:
            missing.append(pkg_name)

    if missing:
        print(f"   ⚠️ Missing Python packages: {', '.join(missing)}")
        print("   Install them using:")
        print(f"   pip install {' '.join(missing)}")
    else:
        print("   ✓ All required core packages are installed.")

    print("\n" + "=" * 72)
    print("✨ Vault initialization completed successfully!")
    print("=" * 72)
    print("Next steps:")
    print("  1. Add broker exports to 00_Raw/ (Degiro, Exante, mBM, pkobp).")
    print("  2. Configure your API keys in .env (Finnhub, Exante).")
    print("  3. Run 'python run.py --all' to execute your first import & analytics.")
    print("=" * 72)
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Initialize new investment vault from starter.")
    parser.add_argument(
        "-t", "--target",
        dest="target",
        type=str,
        default=None,
        help="Target directory to initialize. Defaults to current directory.",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run without prompting.",
    )
    args = parser.parse_args()

    success = init_vault(target_vault=args.target, interactive=not args.non_interactive)
    sys.exit(0 if success else 1)
