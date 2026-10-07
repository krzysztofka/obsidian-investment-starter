import os
import sys
from typing import Any

current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.dirname(current_dir)
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

from model.asset import Asset
from model.config import load_vault_config


def load_config() -> dict[str, Any]:
    """Load configuration from config.yaml via canonical load_vault_config."""
    system_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
    vault_root = os.path.abspath(os.path.join(system_dir, ".."))
    cfg = load_vault_config(base_dir=vault_root)
    return cfg.model_dump(by_alias=True)


class AlertContext:
    """Contextual metadata passed to alert rules during portfolio evaluation."""

    def __init__(
        self,
        assets: list[Asset] | None = None,
        config: dict[str, Any] | None = None,
    ):
        self.config: dict[str, Any] = config if config is not None else load_config()
        self.assets: list[Asset] = assets or []

        # Precompute portfolio values
        self.total_portfolio_value: float = 0.0
        self.portfolio_values: dict[str, float] = {
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
