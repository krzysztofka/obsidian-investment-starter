import os
import sys
import glob
import argparse
from typing import List, Dict, Any, Optional

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure scripts directory is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.dirname(current_dir)
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

from model.asset import Asset
from alerts.context import AlertContext, load_config
from alerts.rules.base import BaseAlertRule
from alerts.rules.overvalued import OvervaluedRule
from alerts.rules.delisting_risk import DelistingRiskRule
from alerts.rules.allocation_drift import AllocationDriftRule
from alerts.rules.stop_loss import StopLossRule
from alerts.rules.insider_selling import InsiderSellingRule


class AlertEngine:
    """Orchestrator for evaluating portfolio alert rules and managing tags across assets."""

    def __init__(
        self,
        rules: Optional[List[BaseAlertRule]] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.config = config if config is not None else load_config()

        if rules is not None:
            self.rules = rules
        else:
            self.rules = self._get_default_rules()

    def _get_default_rules(self) -> List[BaseAlertRule]:
        """Instantiate enabled default alert rules based on configuration."""
        alerts_cfg = self.config.get("alerts", {})

        all_rules = [
            ("overvalued", OvervaluedRule()),
            ("delisting_risk", DelistingRiskRule()),
            ("allocation_drift", AllocationDriftRule()),
            ("stop_loss", StopLossRule()),
            ("insider_selling", InsiderSellingRule()),
        ]

        active_rules: List[BaseAlertRule] = []
        for key, rule_instance in all_rules:
            cfg = alerts_cfg.get(key, {})
            # If section exists and explicitly has enabled: false, skip it
            if isinstance(cfg, dict) and cfg.get("enabled") is False:
                continue
            active_rules.append(rule_instance)

        return active_rules

    def get_assets_directory(self, custom_path: Optional[str] = None) -> str:
        """Resolve absolute path to 10_Finance/Assets directory."""
        if custom_path:
            return os.path.abspath(custom_path)

        system_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
        vault_root = os.path.abspath(os.path.join(system_dir, ".."))
        return os.path.join(vault_root, "10_Finance", "Assets")

    def run(
        self,
        assets_dir: Optional[str] = None,
        save: bool = True,
        rule_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute alert evaluation across all assets in the specified directory."""
        target_dir = self.get_assets_directory(assets_dir)
        if not os.path.exists(target_dir):
            sys.stderr.write(f"Error: Assets directory not found at {target_dir}\n")
            return {"scanned": 0, "updated": 0, "alerts_by_type": {}, "details": []}

        md_files = glob.glob(os.path.join(target_dir, "*.md"))

        # 1. Load all assets to construct the portfolio context
        assets_with_paths: List[tuple] = []
        loaded_assets: List[Asset] = []

        for p in sorted(md_files):
            try:
                asset = Asset.from_file(p)
                assets_with_paths.append((p, asset))
                loaded_assets.append(asset)
            except Exception as e:
                sys.stderr.write(f"Warning: Failed to load asset from {p}: {e}\n")

        context = AlertContext(assets=loaded_assets, config=self.config)

        # Filter rules if requested
        eval_rules = self.rules
        if rule_filter:
            filt = rule_filter.strip().lower()
            eval_rules = [r for r in self.rules if filt in r.name.lower() or filt in r.tag.lower()]

        # 2. Evaluate rules per asset
        updated_count = 0
        details = []
        alerts_by_type: Dict[str, int] = {r.name: 0 for r in eval_rules}

        for path, asset in assets_with_paths:
            asset_modified = False
            tags_before = list(asset.tags) if asset.tags else []

            for rule in eval_rules:
                changed = rule.apply(asset, context)
                if changed:
                    asset_modified = True

                # Count active alerts for reporting
                tag_clean = rule.tag.lstrip("#")
                has_tag = (rule.tag in (asset.tags or [])) or (tag_clean in (asset.tags or []))
                if has_tag:
                    alerts_by_type[rule.name] = alerts_by_type.get(rule.name, 0) + 1

            if asset_modified:
                updated_count += 1
                tags_after = list(asset.tags) if asset.tags else []
                details.append({
                    "file": os.path.basename(path),
                    "ticker": asset.ticker,
                    "name": asset.name,
                    "before": tags_before,
                    "after": tags_after,
                })
                if save:
                    asset.save(path)

        return {
            "scanned": len(loaded_assets),
            "updated": updated_count,
            "total_portfolio_value": context.total_portfolio_value,
            "alerts_by_type": alerts_by_type,
            "details": details,
        }


def main():
    parser = argparse.ArgumentParser(
        description="Portfolio Alert Engine: scan assets and evaluate risk/valuation rules."
    )
    parser.add_argument(
        "--dir",
        dest="assets_dir",
        default=None,
        help="Custom path to 10_Finance/Assets directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate rules and print report without modifying files on disk.",
    )
    parser.add_argument(
        "--rule",
        dest="rule_filter",
        default=None,
        help="Filter and run only rules matching this name or tag substring.",
    )

    args = parser.parse_args()

    engine = AlertEngine()
    print("==================================================")
    print("🔍 Running Portfolio Alert Engine")
    print("==================================================")
    print(f"Loaded {len(engine.rules)} active rules: {', '.join(r.name for r in engine.rules)}")
    if args.dry_run:
        print("Mode: DRY-RUN (no files will be saved)")
    print("")

    res = engine.run(
        assets_dir=args.assets_dir,
        save=not args.dry_run,
        rule_filter=args.rule_filter,
    )

    print(f"Total Assets Scanned: {res['scanned']}")
    print(f"Total Portfolio Value: {res['total_portfolio_value']:,.2f} PLN")
    print(f"Files Modified: {res['updated']}")
    print("")
    print("--- Active Alerts Summary ---")
    for r_name, count in sorted(res["alerts_by_type"].items()):
        badge = "⚠️ " if count > 0 else "✅ "
        print(f"  {badge}{r_name}: {count}")

    if res["details"]:
        print("")
        print("--- Detailed Tag Updates ---")
        for item in res["details"]:
            print(f"  • {item['file']} ({item['name']}):")
            print(f"      Before: {item['before']}")
            print(f"      After : {item['after']}")
    print("==================================================")


if __name__ == "__main__":
    main()
