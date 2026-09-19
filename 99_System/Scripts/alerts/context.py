import os
import sys
from typing import Dict, Any, List, Optional
import yaml

current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.dirname(current_dir)
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

from model.asset import Asset


def load_config() -> Dict[str, Any]:
    """Load configuration from config.yaml searching standard vault locations."""
    system_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
    vault_root = os.path.abspath(os.path.join(system_dir, ".."))

    candidate_paths = [
        os.path.join(vault_root, "config.yaml"),
        os.path.join(system_dir, "config.yaml"),
    ]

    for p in candidate_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    content = yaml.safe_load(f)
                    if isinstance(content, dict):
                        return content
            except Exception as e:
                sys.stderr.write(f"Warning: Failed to parse config from {p}: {e}\n")

    return {}


class AlertContext:
    """Contextual metadata passed to alert rules during portfolio evaluation."""

    def __init__(
        self,
        assets: Optional[List[Asset]] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.config: Dict[str, Any] = config if config is not None else load_config()
        self.assets: List[Asset] = assets or []

        # Precompute portfolio values
        self.total_portfolio_value: float = 0.0
        self.portfolio_values: Dict[str, float] = {
            "safety net": 0.0,
            "long term": 0.0,
            "aggressive": 0.0,
        }

        for a in self.assets:
            val = float(a.value_pln or 0.0)
            self.total_portfolio_value += val

            port = str(a.portfolio or "").strip().lower()
            if port in ("safety net", "safety", "safety_net"):
                self.portfolio_values["safety net"] += val
            elif port in ("long term", "long_term"):
                self.portfolio_values["long term"] += val
            elif port in ("aggressive",):
                self.portfolio_values["aggressive"] += val

    def get_alert_config(self, rule_key: str, default: Any = None) -> Any:
        """Retrieve rule-specific configuration block from config['alerts']."""
        alerts_cfg = self.config.get("alerts", {})
        if not isinstance(alerts_cfg, dict):
            return default
        return alerts_cfg.get(rule_key, default)
