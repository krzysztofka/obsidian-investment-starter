"""Pydantic configuration models for Vault Configuration (config.yaml)."""

import os
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConcurrencyConfig(BaseModel):
    """Configuration for concurrency and worker thread pool."""

    model_config = ConfigDict(extra="ignore")

    max_workers: int | Literal["auto"] = Field(
        default="auto", description="Max worker threads or 'auto' to use os.cpu_count()."
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
    rate_limits: dict[str, float] = Field(
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
        description="Rate limits in requests/sec per domain.",
    )


class BrokerRuleConfig(BaseModel):
    """Rule for portfolio splitting / allocation of specific asset prefixes."""

    model_config = ConfigDict(extra="ignore")

    prefix: str | None = None
    ticker: str | None = None
    portfolio: str
    max_amount: float | None = None


class PlatformConfig(BaseModel):
    """Configuration for individual platform/broker extension."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    default_mode: str = Field(default="csv", description="Default mode: 'api', 'csv', or 'xls'.")
    default_portfolio: str | None = Field(default=None, description="Default portfolio bucket.")
    rules: list[BrokerRuleConfig] = Field(default_factory=list, description="Allocation split rules.")


BrokerImportConfig = PlatformConfig


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


class AlertMacroYieldCurveConfig(BaseModel):
    """Macro inverted yield curve alert settings."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    inversion_threshold_bps: float = 0.0


class AlertsConfig(BaseModel):
    """Alert rules configuration."""

    model_config = ConfigDict(extra="ignore")

    overvalued: AlertOvervaluedConfig = Field(default_factory=AlertOvervaluedConfig)
    delisting_risk: AlertDelistingRiskConfig = Field(default_factory=AlertDelistingRiskConfig)
    allocation_drift: AlertAllocationDriftConfig = Field(default_factory=AlertAllocationDriftConfig)
    stop_loss: AlertStopLossConfig = Field(default_factory=AlertStopLossConfig)
    insider_selling: AlertInsiderSellingConfig = Field(default_factory=AlertInsiderSellingConfig)
    macro_yield_curve: AlertMacroYieldCurveConfig = Field(default_factory=AlertMacroYieldCurveConfig)


class EtfIssuerConfig(BaseModel):
    """ETF issuer discovery keyword mappings."""

    model_config = ConfigDict(extra="ignore")

    discovery_mapping: dict[str, str] = Field(
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
    thresholds: dict[str, float] = Field(default_factory=dict)
    mappings: dict[str, str] = Field(default_factory=dict)


class HistoryRetentionConfig(BaseModel):
    """Configuration for historical portfolio timeline retention and annual archival."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    retention_days: int = Field(default=730, ge=1, description="Days of daily history to retain in portfolio.csv.")
    archive_dir: str = Field(
        default="10_Finance/History/archive", description="Directory to store partitioned yearly archives."
    )
    preserve_boundary_baseline: bool = Field(
        default=True, description="Preserve baseline snapshot at cutoff boundary to prevent holding drops."
    )


class RawDataRetentionConfig(BaseModel):
    """Configuration for ephemeral raw broker export files retention and rotation."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    retention_days: int = Field(default=365, ge=1, description="Days to retain raw broker exports in 00_Raw/.")
    action: Literal["archive", "prune"] = Field(
        default="archive", description="Action for expired files: 'archive' or 'prune'."
    )
    archive_dir: str = Field(default="00_Raw/archive", description="Destination directory when action is 'archive'.")
    compress_zip: bool = Field(default=False, description="Whether to compress archived files into zip.")
    exclude_patterns: list[str] = Field(
        default_factory=lambda: [
            "sample_*",
            ".*",
            ".gitkeep",
            "Articles/*",
            "archive/*",
        ],
        description="Glob patterns of files/directories to exclude from rotation.",
    )


class RetentionConfig(BaseModel):
    """Configuration for data retention and archival policies."""

    model_config = ConfigDict(extra="ignore")

    history: HistoryRetentionConfig = Field(default_factory=HistoryRetentionConfig)
    raw_data: RawDataRetentionConfig = Field(default_factory=RawDataRetentionConfig)


class VaultConfig(BaseModel):
    """Root configuration model representing config.yaml."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    concurrency: ConcurrencyConfig = Field(default_factory=ConcurrencyConfig)
    resilience: ResilienceConfig = Field(default_factory=ResilienceConfig)
    platforms: dict[str, PlatformConfig] = Field(default_factory=dict)
    import_config: dict[str, PlatformConfig] = Field(default_factory=dict, alias="import")
    alerts: AlertsConfig = Field(default_factory=AlertsConfig)
    etf: EtfConfig = Field(default_factory=EtfConfig)
    dominant_sector: DominantSectorConfig = Field(default_factory=DominantSectorConfig)
    retention: RetentionConfig = Field(default_factory=RetentionConfig)

    @model_validator(mode="before")
    @classmethod
    def sync_platforms_and_import(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "platforms" in data and "import" not in data:
                data["import"] = data["platforms"]
            elif "import" in data and "platforms" not in data:
                data["platforms"] = data["import"]
        return data

    @classmethod
    def load(cls, file_path: str | None = None, base_dir: str | None = None) -> "VaultConfig":
        """Load and parse VaultConfig from a YAML file path or search candidate directories."""
        candidate_paths = []
        if file_path:
            candidate_paths.append(file_path)

        if base_dir is None:
            # Default vault root resolution
            current_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.abspath(os.path.join(current_dir, "../../.."))

        candidate_paths.extend(
            [
                os.path.join(base_dir, "config.yaml"),
                os.path.join(base_dir, "99_System", "config.yaml"),
            ]
        )

        for path in candidate_paths:
            if os.path.exists(path):
                try:
                    with open(path, encoding="utf-8") as f:
                        raw_data = yaml.safe_load(f) or {}
                    if isinstance(raw_data, dict):
                        return cls.model_validate(raw_data)
                except Exception:
                    pass

        return cls()


_vault_config_cache: VaultConfig | None = None


def load_vault_config(base_dir: str | None = None, force_refresh: bool = False) -> VaultConfig:
    """Retrieve cached or freshly loaded VaultConfig singleton."""
    global _vault_config_cache
    if _vault_config_cache is None or force_refresh:
        _vault_config_cache = VaultConfig.load(base_dir=base_dir)
    return _vault_config_cache
