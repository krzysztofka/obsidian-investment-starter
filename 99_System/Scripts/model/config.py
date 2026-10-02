"""Pydantic configuration models for Vault Configuration (config.yaml)."""

from typing import Dict, List, Optional, Union, Literal, Any
import os
import yaml
from pydantic import BaseModel, Field, ConfigDict


class ConcurrencyConfig(BaseModel):
    """Configuration for concurrency and worker thread pool."""
    model_config = ConfigDict(extra="ignore")

    max_workers: Union[int, Literal["auto"]] = Field(
        default="auto",
        description="Max worker threads or 'auto' to use os.cpu_count()."
    )

    def resolve_worker_count(self) -> int:
        """Resolve actual number of worker threads."""
        if isinstance(self.max_workers, int) and self.max_workers > 0:
            return self.max_workers
        if isinstance(self.max_workers, str) and self.max_workers.isdigit() and int(self.max_workers) > 0:
            return int(self.max_workers)
        cpu_count = os.cpu_count() or 4
        return max(1, cpu_count)


class ResilienceConfig(BaseModel):
    """Configuration for network resilience, rate limiting, and backoff."""
    model_config = ConfigDict(extra="ignore")

    max_retries: int = Field(default=3, ge=0, description="Max retry attempts for transient errors.")
    base_delay_seconds: float = Field(default=0.5, ge=0.0, description="Initial backoff delay in seconds.")
    max_delay_seconds: float = Field(default=10.0, ge=0.0, description="Maximum ceiling backoff delay.")
    jitter: bool = Field(default=True, description="Enable randomized full jitter.")
    rate_limits: Dict[str, float] = Field(
        default_factory=lambda: {
            "finnhub.io": 10.0,
            "query1.finance.yahoo.com": 15.0,
            "query2.finance.yahoo.com": 15.0,
            "justetf.com": 5.0,
            "stooq.com": 8.0,
            "stooq.pl": 8.0,
            "ishares.com": 6.0,
            "vanguard.com": 6.0,
            "vanguard.co.uk": 6.0,
            "vaneck.com": 6.0,
            "api.nbp.pl": 10.0,
        },
        description="Rate limits in requests/sec per domain."
    )


class BrokerRuleConfig(BaseModel):
    """Rule for portfolio splitting / allocation of specific asset prefixes."""
    model_config = ConfigDict(extra="ignore")

    prefix: str
    portfolio: str
    max_amount: Optional[float] = None


class BrokerImportConfig(BaseModel):
    """Configuration for individual broker position import."""
    model_config = ConfigDict(extra="ignore")

    default_mode: str = Field(default="csv", description="Default mode: 'api', 'csv', or 'xls'.")
    default_portfolio: Optional[str] = Field(default=None, description="Default portfolio bucket.")
    rules: List[BrokerRuleConfig] = Field(default_factory=list, description="Allocation split rules.")


class AlertOvervaluedConfig(BaseModel):
    """Overvalued P/E alert settings."""
    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    max_pe_ratio: float = 40.0


class AlertDelistingRiskConfig(BaseModel):
    """Delisting risk AUM alert settings."""
    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    min_aum_million: float = 50.0


class AlertAllocationDriftConfig(BaseModel):
    """Single position weight limit alert settings."""
    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    max_portfolio_weight_pct: float = 15.0


class AlertStopLossConfig(BaseModel):
    """Stop-loss breach alert settings."""
    model_config = ConfigDict(extra="ignore")

    enabled: bool = True


class AlertInsiderSellingConfig(BaseModel):
    """Insider selling alert settings."""
    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    lookback_days: int = 90


class AlertsConfig(BaseModel):
    """Alert rules configuration."""
    model_config = ConfigDict(extra="ignore")

    overvalued: AlertOvervaluedConfig = Field(default_factory=AlertOvervaluedConfig)
    delisting_risk: AlertDelistingRiskConfig = Field(default_factory=AlertDelistingRiskConfig)
    allocation_drift: AlertAllocationDriftConfig = Field(default_factory=AlertAllocationDriftConfig)
    stop_loss: AlertStopLossConfig = Field(default_factory=AlertStopLossConfig)
    insider_selling: AlertInsiderSellingConfig = Field(default_factory=AlertInsiderSellingConfig)


class EtfIssuerConfig(BaseModel):
    """ETF issuer discovery keyword mappings."""
    model_config = ConfigDict(extra="ignore")

    discovery_mapping: Dict[str, str] = Field(
        default_factory=lambda: {
            "ishares": "iShares",
            "vanguard": "Vanguard",
            "vngrd": "Vanguard",
            "vaneck": "VanEck",
            "spdr": "SPDR",
            "state street": "SPDR",
            "invesco": "Invesco",
            "xtrackers": "Xtrackers",
            "x-trackers": "Xtrackers",
            "dws": "Xtrackers",
            "amundi": "Amundi",
            "lyxor": "Amundi",
            "hsbc": "HSBC",
            "wisdomtree": "WisdomTree",
            "global x": "Global X",
            "globalx": "Global X",
            "schwab": "Schwab",
            "first trust": "First Trust",
            "beta etf": "Beta ETF",
            "franklin": "Franklin Templeton",
            "jpmorgan": "JPMorgan",
            "jpm ": "JPMorgan",
        }
    )


class EtfConfig(BaseModel):
    """ETF extraction and decomposition settings."""
    model_config = ConfigDict(extra="ignore")

    max_top_holdings: int = 10
    issuer: EtfIssuerConfig = Field(default_factory=EtfIssuerConfig)


class DominantSectorConfig(BaseModel):
    """Dominant sector classification thresholds and taxonomy mappings."""
    model_config = ConfigDict(extra="ignore")

    default_threshold: float = 50.0
    diversified_label: str = "Diversified"
    thresholds: Dict[str, float] = Field(default_factory=dict)
    mappings: Dict[str, str] = Field(default_factory=dict)


class VaultConfig(BaseModel):
    """Root configuration model representing config.yaml."""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    concurrency: ConcurrencyConfig = Field(default_factory=ConcurrencyConfig)
    resilience: ResilienceConfig = Field(default_factory=ResilienceConfig)
    import_config: Dict[str, BrokerImportConfig] = Field(default_factory=dict, alias="import")
    alerts: AlertsConfig = Field(default_factory=AlertsConfig)
    etf: EtfConfig = Field(default_factory=EtfConfig)
    dominant_sector: DominantSectorConfig = Field(default_factory=DominantSectorConfig)

    @classmethod
    def load(cls, file_path: Optional[str] = None, base_dir: Optional[str] = None) -> "VaultConfig":
        """Load and parse VaultConfig from a YAML file path or search candidate directories."""
        candidate_paths = []
        if file_path:
            candidate_paths.append(file_path)

        if base_dir is None:
            # Default vault root resolution
            current_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.abspath(os.path.join(current_dir, "../../.."))

        candidate_paths.extend([
            os.path.join(base_dir, "99_System", "config.yaml"),
            os.path.join(base_dir, "config.yaml"),
        ])

        for path in candidate_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        raw_data = yaml.safe_load(f) or {}
                    if isinstance(raw_data, dict):
                        return cls.model_validate(raw_data)
                except Exception as e:
                    pass

        return cls()


_vault_config_cache: Optional[VaultConfig] = None


def load_vault_config(base_dir: Optional[str] = None, force_refresh: bool = False) -> VaultConfig:
    """Retrieve cached or freshly loaded VaultConfig singleton."""
    global _vault_config_cache
    if _vault_config_cache is None or force_refresh:
        _vault_config_cache = VaultConfig.load(base_dir=base_dir)
    return _vault_config_cache
