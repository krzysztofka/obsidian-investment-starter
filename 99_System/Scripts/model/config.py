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


DEFAULT_ETF_ISSUER_MAPPINGS: dict[str, str] = {
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

DEFAULT_SECTOR_THRESHOLDS: dict[str, float] = {
    "Healthcare": 80.0,
    "Health Care": 80.0,
    "Military": 50.0,
    "Finance": 50.0,
    "Financials": 50.0,
    "Technology": 50.0,
    "Real Estate": 50.0,
}

DEFAULT_SECTOR_MAPPINGS: dict[str, str] = {
    # Finance mappings
    "financial_services": "Finance",
    "financials": "Finance",
    "financial services": "Finance",
    "finance": "Finance",
    "insurance - property & casualty": "Finance",
    "insurance - life": "Finance",
    "insurance - specialty": "Finance",
    "insurance": "Finance",
    "banking": "Finance",
    "banks": "Finance",
    # Healthcare mappings
    "healthcare": "Healthcare",
    "health care": "Healthcare",
    "health_care": "Healthcare",
    "pharmaceuticals": "Healthcare",
    "biotechnology": "Healthcare",
    # Military / Defense mappings
    "military": "Military",
    "defense": "Military",
    "aerospace & defense": "Military",
    "aerospace and defense": "Military",
    # Technology mappings
    "technology": "Technology",
    "information technology": "Technology",
    "tech": "Technology",
    "software - infrastructure": "Technology",
    "software - application": "Technology",
    "semiconductors": "Technology",
    # Real Estate mappings
    "realestate": "Real Estate",
    "real estate": "Real Estate",
    "reit": "Real Estate",
    "reits": "Real Estate",
    # Consumer mappings
    "consumer_cyclical": "Consumer Cyclical",
    "consumer discretionary": "Consumer Cyclical",
    "consumer_defensive": "Consumer Defensive",
    "consumer staples": "Consumer Defensive",
    "consumer non-cyclicals": "Consumer Defensive",
    "consumer non-cyclical": "Consumer Defensive",
    # Industrial mappings
    "industrials": "Industrials",
    "industrial": "Industrials",
    "business services": "Industrials",
    # Energy & Utilities mappings
    "energy": "Energy",
    "oil & gas": "Energy",
    "utilities": "Utilities",
    # Materials mappings
    "basic_materials": "Basic Materials",
    "basic materials": "Basic Materials",
    "materials": "Basic Materials",
    # Communication mappings
    "communication_services": "Communication Services",
    "communication services": "Communication Services",
    "telecommunications": "Communication Services",
}


class EtfIssuerConfig(BaseModel):
    """ETF issuer discovery keyword mappings."""

    model_config = ConfigDict(extra="ignore")

    discovery_mapping: dict[str, str] = Field(default_factory=lambda: dict(DEFAULT_ETF_ISSUER_MAPPINGS))

    @model_validator(mode="before")
    @classmethod
    def merge_discovery_defaults(cls, data: Any) -> Any:
        if isinstance(data, dict):
            user_mapping = data.get("discovery_mapping")
            merged = dict(DEFAULT_ETF_ISSUER_MAPPINGS)
            if isinstance(user_mapping, dict):
                merged.update(user_mapping)
            data["discovery_mapping"] = merged
        return data


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
    thresholds: dict[str, float] = Field(default_factory=lambda: dict(DEFAULT_SECTOR_THRESHOLDS))
    mappings: dict[str, str] = Field(default_factory=lambda: dict(DEFAULT_SECTOR_MAPPINGS))

    @model_validator(mode="before")
    @classmethod
    def merge_defaults(cls, data: Any) -> Any:
        if isinstance(data, dict):
            user_thresholds = data.get("thresholds")
            merged_thresholds = dict(DEFAULT_SECTOR_THRESHOLDS)
            if isinstance(user_thresholds, dict):
                merged_thresholds.update(user_thresholds)
            data["thresholds"] = merged_thresholds

            user_mappings = data.get("mappings")
            merged_mappings = dict(DEFAULT_SECTOR_MAPPINGS)
            if isinstance(user_mappings, dict):
                merged_mappings.update(user_mappings)
            data["mappings"] = merged_mappings
        return data


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


class ModelPortfolioTargetItem(BaseModel):
    """Target allocation item within a model portfolio layer."""

    model_config = ConfigDict(extra="ignore")

    target: str = Field(description="Name of target (e.g., 'Equities', 'Bonds', 'Cash', or sector/ticker).")
    weight_pct: float = Field(ge=0.0, le=100.0, description="Target weight in percent (0 to 100).")
    tolerance_band_pct: float | None = Field(
        default=None, ge=0.0, description="Optional override for tolerance corridor (e.g. ±5.0%)."
    )
    min_trade_amount: float | None = Field(
        default=None, ge=0.0, description="Optional override for minimum trade amount in base currency."
    )


class ModelPortfolioLayers(BaseModel):
    """Independent target allocation layers within a model portfolio."""

    model_config = ConfigDict(extra="ignore")

    asset_classes: list[ModelPortfolioTargetItem] = Field(
        default_factory=list, description="Broad asset class targets (e.g. Equities, Bonds, Cash)."
    )
    sectors: list[ModelPortfolioTargetItem] = Field(
        default_factory=list, description="Dominant sector targets (e.g. Technology, Military)."
    )
    assets: list[ModelPortfolioTargetItem] = Field(
        default_factory=list, description="Specific ticker / asset targets (e.g. VWCE, V80A)."
    )

    @model_validator(mode="after")
    def validate_layer_sums(self) -> "ModelPortfolioLayers":
        """Verify each configured layer with targets has 0 < sum <= 100.0% and no duplicate targets."""
        for layer_name in ("asset_classes", "sectors", "assets"):
            items: list[ModelPortfolioTargetItem] = getattr(self, layer_name)
            if items:
                seen_targets: set[str] = set()
                for item in items:
                    norm_target = item.target.strip().lower()
                    if norm_target in seen_targets:
                        raise ValueError(f"Duplicate target '{item.target}' in model portfolio layer '{layer_name}'.")
                    seen_targets.add(norm_target)

                total_weight = sum(item.weight_pct for item in items)
                if total_weight <= 0.0:
                    raise ValueError(
                        f"Model portfolio layer '{layer_name}' target weights must be greater than 0% (got {total_weight:.2f}%)."
                    )
                if total_weight > 100.0 + 0.1:
                    raise ValueError(
                        f"Model portfolio layer '{layer_name}' target weights cannot exceed 100.0% (got {total_weight:.2f}%)."
                    )
        return self


class ModelPortfolioConfig(BaseModel):
    """Configuration for an individual model portfolio bucket."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(description="Display or canonical portfolio name (e.g. 'Safety net').")
    rebalance_strategy: Literal["inflow_first", "full_rebalance"] = Field(
        default="inflow_first", description="Rebalancing strategy preference ('inflow_first' or 'full_rebalance')."
    )
    tolerance_band_pct: float = Field(
        default=5.0, ge=0.0, description="Default tolerance band corridor in percentage points (e.g. ±5%)."
    )
    min_trade_amount: float = Field(
        default=500.0, ge=0.0, description="Minimum trade threshold in base currency to avoid micro-transactions."
    )
    primary_layer: Literal["asset_classes", "sectors", "assets"] = Field(
        default="asset_classes", description="Primary target layer used to generate actionable rebalance deltas."
    )
    layers: ModelPortfolioLayers = Field(default_factory=ModelPortfolioLayers)

    def get_tolerance_band(self, item: ModelPortfolioTargetItem) -> float:
        """Get effective tolerance band for an item, falling back to portfolio default."""
        return item.tolerance_band_pct if item.tolerance_band_pct is not None else self.tolerance_band_pct

    def get_min_trade_amount(self, item: ModelPortfolioTargetItem) -> float:
        """Get effective minimum trade amount for an item, falling back to portfolio default."""
        return item.min_trade_amount if item.min_trade_amount is not None else self.min_trade_amount


class UserProfileConfig(BaseModel):
    """Investor profile, risk preferences, and rebalancing rules of engagement."""

    model_config = ConfigDict(extra="ignore")

    risk_tolerance: Literal["conservative", "moderate", "aggressive"] = Field(
        default="moderate", description="Overall investor risk tolerance ('conservative', 'moderate', or 'aggressive')."
    )
    max_single_stock_pct: float = Field(
        default=15.0, ge=1.0, le=100.0, description="Maximum allocation percentage for any single equity holding."
    )
    tax_sensitive: bool = Field(
        default=True, description="Prioritize cash-flow DCA over taxable sales to minimize capital gains tax drag."
    )
    allow_profit_harvesting: bool = Field(
        default=True,
        description="Allow AI to suggest moving trimmed profits from Aggressive to Long Term foundation.",
    )
    tax_advantaged_priority: list[str] = Field(
        default_factory=lambda: ["mbank_ike", "mbank_ikze"],
        description="Platform IDs prioritized for tax-free growth.",
    )


DEFAULT_CURRENCY_SYMBOLS: dict[str, tuple[str, Literal["prefix", "suffix"]]] = {
    "PLN": ("zł", "suffix"),
    "EUR": ("€", "suffix"),
    "USD": ("$", "prefix"),
    "GBP": ("£", "prefix"),
    "CHF": ("CHF", "suffix"),
    "CAD": ("$", "prefix"),
    "AUD": ("$", "prefix"),
    "JPY": ("¥", "prefix"),
    "NOK": ("kr", "suffix"),
    "SEK": ("kr", "suffix"),
}


class LocalizationConfig(BaseModel):
    """Configuration for base currency, symbol formatting, and localization."""

    model_config = ConfigDict(extra="ignore")

    base_currency: str = Field(default="PLN", description="Base portfolio reference currency (ISO-4217).")
    currency_symbol: str = Field(default="zł", description="Display symbol for base currency (e.g. 'zł', '€', '$').")
    symbol_position: Literal["prefix", "suffix"] = Field(
        default="suffix", description="Position of the currency symbol relative to amount ('prefix' or 'suffix')."
    )
    supported_currencies: list[str] = Field(
        default_factory=lambda: ["PLN", "EUR", "USD", "GBP", "CHF"],
        description="List of suggested currencies for CLI prompts and quick selection.",
    )


class VaultConfig(BaseModel):
    """Root configuration model representing config.yaml."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    localization: LocalizationConfig = Field(default_factory=LocalizationConfig)
    user_profile: UserProfileConfig = Field(default_factory=UserProfileConfig)
    concurrency: ConcurrencyConfig = Field(default_factory=ConcurrencyConfig)
    resilience: ResilienceConfig = Field(default_factory=ResilienceConfig)
    platforms: dict[str, PlatformConfig] = Field(default_factory=dict)
    import_config: dict[str, PlatformConfig] = Field(default_factory=dict, alias="import")
    alerts: AlertsConfig = Field(default_factory=AlertsConfig)
    etf: EtfConfig = Field(default_factory=EtfConfig)
    dominant_sector: DominantSectorConfig = Field(default_factory=DominantSectorConfig)
    retention: RetentionConfig = Field(default_factory=RetentionConfig)
    model_portfolios: dict[str, ModelPortfolioConfig] = Field(default_factory=dict)

    def get_model_portfolio(self, portfolio_name: str | None) -> ModelPortfolioConfig | None:
        """Retrieve model portfolio config matching given portfolio name (case-insensitive / normalized)."""
        if not portfolio_name or not self.model_portfolios:
            return None

        def _norm(s: str) -> str:
            return s.lower().replace(" ", "").replace("_", "").replace("-", "")

        target_norm = _norm(portfolio_name)

        # 1. Direct match by dictionary key
        for key, cfg in self.model_portfolios.items():
            if _norm(key) == target_norm:
                return cfg

        # 2. Match by cfg.name
        for cfg in self.model_portfolios.values():
            if _norm(cfg.name) == target_norm:
                return cfg

        return None

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
