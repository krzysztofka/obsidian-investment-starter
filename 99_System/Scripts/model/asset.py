"""Pydantic model for Investment Asset notes in 10_Finance/Assets."""

from typing import Optional, List, Dict, Any, Union
import os
import yaml
from pydantic import BaseModel, Field, ConfigDict, field_validator


class Asset(BaseModel):
    """Structure definition corresponding to asset_template.md and Obsidian asset notes.

    Represents an investment asset holding (Equity, ETF, or Cash) tracked within
    the 10_Finance/Assets vault directory.
    """
    model_config = ConfigDict(extra="allow", validate_assignment=True, populate_by_name=True)

    # Core required fields (matching asset_template.md schema)
    ticker: str = ""
    name: str = ""
    platform: str = ""
    portfolio: Optional[str] = None  # 'Safety net', 'Long term', 'Aggressive'
    quantity: Union[int, float] = 0
    avg_price: Optional[Union[int, float]] = None
    current_price: Union[int, float] = 0.0
    value_pln: Union[int, float] = 0.0
    currency: str = "USD"
    asset_type: str = "equity"  # 'equity', 'etf', 'cash'
    asset_allocation: Optional[Dict[str, Union[int, float]]] = None  # e.g. {'equity': 60, 'bonds': 40}

    # Classification & Ratings
    dominant_sector: Optional[str] = None
    industry: Optional[str] = None
    analyst_rating: Optional[Union[str, List[str]]] = None
    morningstar_rating: Optional[Union[str, int, float]] = None
    morningstar_risk: Optional[str] = None
    last_updated: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    # Extended metadata (Yahoo Finance & JustETF enrichments)
    sector: Optional[str] = None
    country: Optional[str] = None
    market_cap: Optional[Union[str, float, int]] = None
    pe_ratio: Optional[Union[float, int, str]] = None
    forward_pe: Optional[Union[float, int, str]] = None
    dividend_yield: Optional[Union[str, float, int]] = None
    beta: Optional[Union[float, int, str]] = None
    fifty_two_week_high: Optional[Union[float, int, str]] = None
    fifty_two_week_low: Optional[Union[float, int, str]] = None
    drawdown_52w: Optional[Union[str, float, int]] = None
    sma_50: Optional[Union[float, int, str]] = None
    sma_200: Optional[Union[float, int, str]] = None
    rsi_14: Optional[Union[float, int, str]] = None
    yahoo_ticker: Optional[str] = None
    stooq_ticker: Optional[str] = None
    isin: Optional[str] = None

    # Quantitative & Risk Metrics (OpenBB / Historical Price Analysis)
    volatility: Optional[Union[str, float, int]] = None
    sharpe_ratio: Optional[Union[float, int, str]] = None
    max_drawdown: Optional[Union[str, float, int]] = None
    upside_potential: Optional[Union[str, float, int]] = None

    # ETF specific metadata
    justetf_url: Optional[str] = None
    issuer: Optional[str] = None
    issuer_url: Optional[str] = None
    ter: Optional[Union[str, float, int]] = None
    fund_size: Optional[Union[str, float, int]] = None
    distribution_policy: Optional[str] = None
    replication: Optional[str] = None
    fund_domicile: Optional[str] = None
    top_holdings: Optional[List[str]] = None
    source: Optional[str] = "platform"  # Options: "platform", "manual"

    # Additional custom frontmatter fields not explicitly typed
    extra_properties: Dict[str, Any] = Field(default_factory=dict)

    # Note markdown body (below YAML frontmatter)
    body: str = ""

    @field_validator("last_updated", mode="before")
    @classmethod
    def _coerce_date_str(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        return str(v)

    @field_validator("tags", "top_holdings", mode="before")
    @classmethod
    def _coerce_list(cls, v: Any) -> Any:
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return list(v) if isinstance(v, (list, tuple, set)) else []

    def to_frontmatter_dict(self) -> Dict[str, Any]:
        """Convert the Asset model into a frontmatter dictionary maintaining standard order."""
        ordered_fields = [
            # 1. Core Position
            'ticker', 'name', 'platform', 'portfolio', 'quantity', 'avg_price',
            'current_price', 'value_pln', 'currency', 'asset_type', 'asset_allocation',
            # 2. Structure & Allocation
            'dominant_sector', 'industry', 'sector', 'country',
            # 3. Valuation & Fundamentals
            'market_cap', 'pe_ratio', 'forward_pe', 'dividend_yield',
            # 4. Technicals & Momentum
            'fifty_two_week_high', 'fifty_two_week_low', 'drawdown_52w',
            'sma_50', 'sma_200', 'rsi_14', 'beta',
            # 5. Risk & Quantitative (OpenBB / Morningstar)
            'volatility', 'sharpe_ratio', 'max_drawdown', 'upside_potential',
            'morningstar_rating', 'morningstar_risk', 'analyst_rating',
            # 6. ETF Specifics
            'isin', 'yahoo_ticker', 'stooq_ticker', 'issuer', 'issuer_url', 'justetf_url', 'ter',
            'fund_size', 'distribution_policy', 'replication', 'fund_domicile', 'top_holdings',
            # 7. Meta & Alerts
            'last_updated', 'source', 'tags'
        ]

        fm: Dict[str, Any] = {}
        for key in ordered_fields:
            val = getattr(self, key, None)
            if key in ['tags', 'top_holdings']:
                if val:
                    fm[key] = list(val)
            elif val is not None:
                fm[key] = val
            elif key in ['avg_price', 'morningstar_rating', 'morningstar_risk']:
                # Keep explicit null for template standard fields
                if getattr(self, key) is None:
                    fm[key] = None

        # Add any additional dynamic properties
        for k, v in self.extra_properties.items():
            if k not in fm:
                fm[k] = v

        # Also check model extra fields
        if self.model_extra:
            for k, v in self.model_extra.items():
                if k not in fm and k != "extra_properties":
                    fm[k] = v

        return fm

    @classmethod
    def from_frontmatter_dict(cls, data: Dict[str, Any], body: str = "") -> "Asset":
        """Construct an Asset instance from frontmatter dictionary and markdown body."""
        known_fields = set(cls.model_fields.keys())

        kwargs: Dict[str, Any] = {}
        extra: Dict[str, Any] = {}

        for k, v in data.items():
            if k in known_fields:
                kwargs[k] = v
            else:
                extra[k] = v

        kwargs['extra_properties'] = extra
        kwargs['body'] = body

        # Ensure minimal required fields
        if 'ticker' not in kwargs:
            kwargs['ticker'] = ''
        if 'name' not in kwargs:
            kwargs['name'] = ''
        if 'platform' not in kwargs:
            kwargs['platform'] = ''
        if 'source' not in kwargs or not kwargs['source']:
            kwargs['source'] = 'platform'

        return cls(**kwargs)

    @classmethod
    def from_markdown(cls, content: str) -> "Asset":
        """Parse markdown file content containing YAML frontmatter into an Asset."""
        content = content.lstrip('\ufeff')
        lines = content.splitlines(keepends=True)
        if not lines or lines[0].strip() != '---':
            return cls(ticker="", name="", platform="", body=content)

        end_idx = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                end_idx = i
                break

        if end_idx == -1:
            return cls(ticker="", name="", platform="", body=content)

        fm_lines = "".join(lines[1:end_idx])
        body = "".join(lines[end_idx + 1:])

        try:
            fm_dict = yaml.safe_load(fm_lines) or {}
        except Exception:
            fm_dict = {}

        return cls.from_frontmatter_dict(fm_dict, body=body)

    @classmethod
    def from_file(cls, file_path: str) -> "Asset":
        """Load an Asset instance directly from a markdown file path."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return cls.from_markdown(content)

    def to_markdown(self) -> str:
        """Render the Asset instance to full markdown note string."""
        fm_dict = self.to_frontmatter_dict()
        out = ["---\n"]
        for k, v in fm_dict.items():
            if v is None:
                out.append(f"{k}: null\n")
            elif isinstance(v, bool):
                out.append(f"{k}: {'true' if v else 'false'}\n")
            elif isinstance(v, (int, float)):
                out.append(f"{k}: {v}\n")
            elif isinstance(v, str):
                if v.startswith("[[") and v.endswith("]]"):
                    out.append(f'{k}: "{v}"\n')
                elif any(c in v for c in [':', '#', '[', ']', '{', '}', ',', '&', '*', '?', '|', '-', '<', '>', '=', '!', '%', '@']):
                    out.append(f'{k}: "{v}"\n')
                else:
                    out.append(f"{k}: {v}\n")
            elif isinstance(v, dict):
                if not v:
                    continue
                out.append(f"{k}:\n")
                for sub_k, sub_v in v.items():
                    out.append(f"  {sub_k}: {sub_v}\n")
            elif isinstance(v, (list, tuple)):
                if not v:
                    continue
                out.append(f"{k}:\n")
                for item in v:
                    item_str = str(item)
                    if any(c in item_str for c in [':', '#', '[', ']', '{', '}', ',', '&', '*', '?', '|', '-', '<', '>', '=', '!', '%', '@']):
                        out.append(f'  - "{item_str}"\n')
                    else:
                        out.append(f"  - {item_str}\n")
            else:
                out.append(f"{k}: {v}\n")
        out.append("---\n")

        body_content = self.body
        if not body_content:
            body_content = (
                f"\n# {self.name} ({self.ticker})\n\n"
                f"**Platform:** [[{self.platform}]]\n\n"
                f"## 📈 Technical & Market Price Chart\n"
                f"```dataviewjs\n"
                f'await dv.view("99_System/Views/stooq_chart", {{\n'
                f"    ticker: dv.current().stooq_ticker,\n"
                f'    defaultRange: "1Y"\n'
                f"}});\n"
                f"```\n\n"
                f"## Investment Thesis / Notes\n"
                f"Information about reasoning for buying and keeping this asset.\n"
            )

        out.append(body_content)
        return "".join(out)

    def save(self, file_path: str) -> None:
        """Save asset note to the specified file path."""
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())
