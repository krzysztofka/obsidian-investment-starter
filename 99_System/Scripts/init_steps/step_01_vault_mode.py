"""Step 1: Vault Mode (Clean vs Demo), Directory Scaffolding, and Core Files."""

import os
import shutil

from init_steps.base import BaseInitStep, InitContext, InitStepRegistry

CORE_DIRECTORIES = [
    "00_Raw/Articles",
    "00_Raw/archive",
    "10_Finance/Assets",
    "10_Finance/ETF_Holdings",
    "10_Finance/History",
    "10_Finance/History/archive",
    "10_Finance/Watchlist",
    "20_Decisions",
    "99_System/Scripts",
    "99_System/Templates",
    "99_System/Views",
    "99_System/docs",
]


def prompt_clean_mode() -> bool:
    """Interactive prompt asking whether to wipe sample demo data for a clean personal vault."""
    print("\nSelect initial vault data mode:")
    print("  [1] Clean Vault (Wipe sample demo assets, mock exports & dummy history) [Default]")
    print("  [2] Demo Vault  (Keep sample portfolio assets & test data to explore dashboards)")
    try:
        choice = input("\nEnter choice [1-2, or Enter for Clean]: ").strip()
    except (EOFError, KeyboardInterrupt):
        return True
    return choice != "2"


def purge_sample_data(target_dir: str) -> dict[str, int]:
    """Purge sample demo assets, raw demo files, and mock history from vault."""
    counts = {"assets": 0, "etf_holdings": 0, "raw_files": 0, "decisions": 0}

    # 1. Purge sample assets in 10_Finance/Assets/
    assets_dir = os.path.join(target_dir, "10_Finance", "Assets")
    if os.path.exists(assets_dir):
        for fname in os.listdir(assets_dir):
            fpath = os.path.join(assets_dir, fname)
            if os.path.isfile(fpath) and fname.endswith(".md"):
                try:
                    os.remove(fpath)
                    counts["assets"] += 1
                except Exception:
                    pass
        gitkeep = os.path.join(assets_dir, ".gitkeep")
        if not os.path.exists(gitkeep):
            try:
                with open(gitkeep, "w", encoding="utf-8") as f:
                    f.write("")
            except Exception:
                pass

    # 2. Purge sample ETF holdings in 10_Finance/ETF_Holdings/ (keep Holdings_Overview.md)
    holdings_dir = os.path.join(target_dir, "10_Finance", "ETF_Holdings")
    if os.path.exists(holdings_dir):
        for fname in os.listdir(holdings_dir):
            if fname == "Holdings_Overview.md":
                continue
            fpath = os.path.join(holdings_dir, fname)
            if os.path.isfile(fpath) and fname.endswith(".md"):
                try:
                    os.remove(fpath)
                    counts["etf_holdings"] += 1
                except Exception:
                    pass
        gitkeep = os.path.join(holdings_dir, ".gitkeep")
        if not os.path.exists(gitkeep):
            try:
                with open(gitkeep, "w", encoding="utf-8") as f:
                    f.write("")
            except Exception:
                pass

    # 3. Purge sample raw files in 00_Raw/**/sample_*.*
    raw_dir = os.path.join(target_dir, "00_Raw")
    if os.path.exists(raw_dir):
        for root, _, files in os.walk(raw_dir):
            for fname in files:
                if fname.lower().startswith("sample_"):
                    fpath = os.path.join(root, fname)
                    try:
                        os.remove(fpath)
                        counts["raw_files"] += 1
                    except Exception:
                        pass
            if os.path.isdir(root) and not os.listdir(root):
                try:
                    with open(os.path.join(root, ".gitkeep"), "w", encoding="utf-8") as f:
                        f.write("")
                except Exception:
                    pass

    # 4. Purge sample decisions in 20_Decisions/
    dec_dir = os.path.join(target_dir, "20_Decisions")
    if os.path.exists(dec_dir):
        for root, _, files in os.walk(dec_dir):
            for fname in files:
                if fname.endswith(".md"):
                    fpath = os.path.join(root, fname)
                    try:
                        os.remove(fpath)
                        counts["decisions"] += 1
                    except Exception:
                        pass
        dec_2026 = os.path.join(dec_dir, "2026")
        os.makedirs(dec_2026, exist_ok=True)
        gitkeep = os.path.join(dec_2026, ".gitkeep")
        if not os.path.exists(gitkeep):
            try:
                with open(gitkeep, "w", encoding="utf-8") as f:
                    f.write("")
            except Exception:
                pass

    # 5. Reset 10_Finance/History/portfolio.csv
    hist_dir = os.path.join(target_dir, "10_Finance", "History")
    os.makedirs(hist_dir, exist_ok=True)
    csv_path = os.path.join(hist_dir, "portfolio.csv")
    canonical_header = "date,ticker,name,value_base,current_price,pe_ratio,quantity,portfolio\n"
    try:
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write(canonical_header)
    except Exception:
        pass

    return counts


def _copy_tree_filtered(src: str, dst: str, ignore_patterns: list[str] | None = None) -> None:
    """Recursively copy directory tree ignoring specified file/folder patterns."""
    if ignore_patterns is None:
        ignore_patterns = ["__pycache__", ".pytest_cache", ".git", ".DS_Store", "*.pyc", "*.log"]

    def _ignore(directory: str, files: list[str]) -> set[str]:
        ignored = set()
        for f in files:
            for pattern in ignore_patterns:
                if pattern.startswith("*") and f.endswith(pattern[1:]):
                    ignored.add(f)
                elif f == pattern:
                    ignored.add(f)
        return ignored

    os.makedirs(dst, exist_ok=True)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if any(item == p or (p.startswith("*") and item.endswith(p[1:])) for p in ignore_patterns):
            continue
        if os.path.isdir(s):
            shutil.copytree(s, d, ignore=_ignore, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)


def scaffold_target_vault(
    source_vault: str,
    target_vault: str,
    clean: bool = True,
    force: bool = False,
    interactive: bool = True,
) -> bool:
    """Scaffold a full downstream vault skeleton from the upstream starter."""
    source_vault = os.path.abspath(source_vault)
    target_vault = os.path.abspath(target_vault)

    if source_vault == target_vault:
        return True

    if os.path.exists(target_vault):
        items = [it for it in os.listdir(target_vault) if it not in (".git", ".DS_Store", "Thumbs.db", "desktop.ini")]
        if items and not force:
            if interactive:
                print(f"\n⚠️  Target directory '{target_vault}' already contains {len(items)} files/folders.")
                try:
                    ans = input("Continue and merge/overwrite system files? [y/N]: ").strip().lower()
                    if ans not in ("y", "yes"):
                        print("Aborted.")
                        return False
                except (EOFError, KeyboardInterrupt):
                    return False
            else:
                import sys

                print(
                    f"Error: Target directory '{target_vault}' is not empty. Use --force to proceed.", file=sys.stderr
                )
                return False

    os.makedirs(target_vault, exist_ok=True)

    # 1. System directory (99_System/) - strictly excluding Tests/ and cache
    sys_dirs = ["Scripts", "Templates", "Views", "docs"]
    for sd in sys_dirs:
        src_sd = os.path.join(source_vault, "99_System", sd)
        dst_sd = os.path.join(target_vault, "99_System", sd)
        if os.path.exists(src_sd):
            _copy_tree_filtered(
                src_sd,
                dst_sd,
                ignore_patterns=["__pycache__", ".pytest_cache", "*.pyc", "*.log", "runner.log", "Tests"],
            )

    # 2. .obsidian configuration & plugins
    src_obs = os.path.join(source_vault, ".obsidian")
    dst_obs = os.path.join(target_vault, ".obsidian")
    if os.path.exists(src_obs):
        _copy_tree_filtered(
            src_obs,
            dst_obs,
            ignore_patterns=["workspace*", "cache", "starred.json", "graph.json", ".trash"],
        )

    # 3. Root markdown dashboards
    dashboards = [
        "Overview.md",
        "Welcome.md",
        "Health.md",
        "Alerts.md",
        "Portfolio_performance.md",
        "Safety_portfolio.md",
        "Long_term_portfolio.md",
        "Aggressive_portfolio.md",
    ]
    for db in dashboards:
        src_f = os.path.join(source_vault, db)
        dst_f = os.path.join(target_vault, db)
        if os.path.exists(src_f):
            shutil.copy2(src_f, dst_f)

    # 4. 10_Finance static notes & watchlists
    src_macro = os.path.join(source_vault, "10_Finance", "Macro.md")
    dst_macro = os.path.join(target_vault, "10_Finance", "Macro.md")
    if os.path.exists(src_macro):
        os.makedirs(os.path.dirname(dst_macro), exist_ok=True)
        shutil.copy2(src_macro, dst_macro)

    src_wl = os.path.join(source_vault, "10_Finance", "Watchlist")
    dst_wl = os.path.join(target_vault, "10_Finance", "Watchlist")
    if os.path.exists(src_wl):
        _copy_tree_filtered(src_wl, dst_wl)

    # 5. Root runners, configs & manifests
    root_system_files = [
        "run.py",
        "patch.py",
        "init.py",
        "pyproject.toml",
        ".vault_version",
        ".env.example",
    ]
    for rf in root_system_files:
        src_f = os.path.join(source_vault, rf)
        dst_f = os.path.join(target_vault, rf)
        if os.path.exists(src_f):
            shutil.copy2(src_f, dst_f)

    for cfg_f in ["config.yaml", ".gitignore"]:
        src_f = os.path.join(source_vault, cfg_f)
        dst_f = os.path.join(target_vault, cfg_f)
        if os.path.exists(src_f) and not os.path.exists(dst_f):
            shutil.copy2(src_f, dst_f)

    # 6. Sample data or pristine directories
    if not clean:
        for fld in ["10_Finance/Assets", "10_Finance/ETF_Holdings", "00_Raw", "20_Decisions"]:
            s = os.path.join(source_vault, fld)
            d = os.path.join(target_vault, fld)
            if os.path.exists(s):
                _copy_tree_filtered(s, d)
        src_csv = os.path.join(source_vault, "10_Finance", "History", "portfolio.csv")
        dst_csv = os.path.join(target_vault, "10_Finance", "History", "portfolio.csv")
        if os.path.exists(src_csv):
            os.makedirs(os.path.dirname(dst_csv), exist_ok=True)
            shutil.copy2(src_csv, dst_csv)
    else:
        src_ho = os.path.join(source_vault, "10_Finance", "ETF_Holdings", "Holdings_Overview.md")
        dst_ho = os.path.join(target_vault, "10_Finance", "ETF_Holdings", "Holdings_Overview.md")
        if os.path.exists(src_ho):
            os.makedirs(os.path.dirname(dst_ho), exist_ok=True)
            shutil.copy2(src_ho, dst_ho)
        dst_csv = os.path.join(target_vault, "10_Finance", "History", "portfolio.csv")
        os.makedirs(os.path.dirname(dst_csv), exist_ok=True)
        with open(dst_csv, "w", encoding="utf-8") as f:
            f.write("date,ticker,name,value_base,current_price,pe_ratio,quantity,portfolio\n")

    return True


def ensure_core_vault_files(source_vault: str, target_dir: str) -> None:
    """Ensure core directories, .vault_version, .env, .gitignore, and config.yaml exist."""
    for rel_d in CORE_DIRECTORIES:
        dpath = os.path.join(target_dir, rel_d)
        os.makedirs(dpath, exist_ok=True)
        gitkeep = os.path.join(dpath, ".gitkeep")
        if not os.path.exists(gitkeep) and not os.listdir(dpath):
            with open(gitkeep, "w", encoding="utf-8") as f:
                f.write("")

    # .vault_version
    starter_version_file = os.path.join(source_vault, ".vault_version")
    starter_version = "0.10.0"
    if os.path.exists(starter_version_file):
        try:
            with open(starter_version_file, encoding="utf-8") as f:
                starter_version = f.read().strip() or "0.10.0"
        except Exception:
            pass
    target_version_file = os.path.join(target_dir, ".vault_version")
    with open(target_version_file, "w", encoding="utf-8") as f:
        f.write(f"{starter_version}\n")

    # .env
    env_target = os.path.join(target_dir, ".env")
    env_example = os.path.join(source_vault, ".env.example")
    if not os.path.exists(env_target):
        if os.path.exists(env_example):
            shutil.copy2(env_example, env_target)
        else:
            with open(env_target, "w", encoding="utf-8") as f:
                f.write("# Environment Configuration\nFINNHUB_API_KEY=\nEXANTE_API_KEY=\nEXANTE_API_SECRET=\n")

    # .gitignore
    gitignore_target = os.path.join(target_dir, ".gitignore")
    gitignore_source = os.path.join(source_vault, ".gitignore")
    if not os.path.exists(gitignore_target) and os.path.exists(gitignore_source):
        shutil.copy2(gitignore_source, gitignore_target)

    # config.yaml
    config_target = os.path.join(target_dir, "config.yaml")
    config_source = os.path.join(source_vault, "config.yaml")
    if not os.path.exists(config_target) and os.path.exists(config_source):
        shutil.copy2(config_source, config_target)


@InitStepRegistry.register
class VaultModeStep(BaseInitStep):
    """Step 1: Vault data mode selection (Clean vs Demo) and core file scaffolding."""

    step_id = "vault_mode"
    step_number = 1
    title = "Configuring vault data mode (Clean vs Demo) & scaffolding core files"
    description = "Select Clean vs Demo mode and initialize core directories, .env, and config.yaml."
    aliases = ["mode", "clean", "demo", "basic", "vault-mode"]

    def run(self, ctx: InitContext) -> bool:
        self.print_header(single_step=ctx.single_step_mode)

        if ctx.clean is None:
            ctx.clean = prompt_clean_mode() if ctx.interactive else False

        if ctx.target_dir != ctx.source_vault:
            print("   Scaffolding target vault files from starter template...")
            ok = scaffold_target_vault(
                source_vault=ctx.source_vault,
                target_vault=ctx.target_dir,
                clean=bool(ctx.clean),
                force=ctx.force,
                interactive=ctx.interactive,
            )
            if not ok:
                return False
            print("   ✓ Complete vault skeleton, dashboards, and runtime engine scaffolded.")

        ensure_core_vault_files(ctx.source_vault, ctx.target_dir)

        if ctx.target_dir == ctx.source_vault:
            if ctx.clean:
                res = purge_sample_data(ctx.target_dir)
                print(
                    f"   ✓ Clean Vault: Purged {res['assets']} sample asset(s), "
                    f"{res['raw_files']} demo file(s), and reset portfolio history."
                )
            else:
                print("   ✓ Demo Vault: Sample portfolio assets and demonstration history preserved.")
        else:
            mode_label = "Clean Vault" if ctx.clean else "Demo Vault"
            print(f"   ✓ Initialized target as {mode_label} with core configuration files.")

        return True
