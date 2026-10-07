"""Pydantic model for Investment Asset notes in 10_Finance/Assets."""

import os
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    portfolio: str | None = None  # 'Safety net', 'Long term', 'Aggressive'
    quantity: int | float = 0
    avg_price: int | float | None = None
    current_price: int | float = 0.0
    value_pln: int | float = 0.0
    currency: str = "USD"
    asset_type: str = "equity"  # 'equity', 'etf', 'cash'
    asset_allocation: dict[str, int | float] | None = None  # e.g. {'equity': 60, 'bonds': 40}

    # Classification & Ratings
    dominant_sector: str | None = None
    industry: str | None = None
    analyst_rating: str | list[str] | None = None
    morningstar_rating: str | int | float | None = None
    morningstar_risk: str | None = None
    last_updated: str | None = None
    tags: list[str] = Field(default_factory=list)

    # Extended metadata (Yahoo Finance & JustETF enrichments)
    sector: str | None = None
    country: str | None = None
    market_cap: str | float | int | None = None
    pe_ratio: float | int | str | None = None
    forward_pe: float | int | str | None = None
    dividend_yield: str | float | int | None = None
    beta: float | int | str | None = None
    fifty_two_week_high: float | int | str | None = None
    fifty_two_week_low: float | int | str | None = None
    drawdown_52w: str | float | int | None = None
    sma_50: float | int | str | None = None
    sma_200: float | int | str | None = None
    rsi_14: float | int | str | None = None
    yahoo_ticker: str | None = None
    stooq_ticker: str | None = None
    isin: str | None = None

    # Quantitative & Risk Metrics (OpenBB / Historical Price Analysis)
    volatility: str | float | int | None = None
    sharpe_ratio: float | int | str | None = None
    max_drawdown: str | float | int | None = None
    upside_potential: str | float | int | None = None

    # ETF specific metadata
    justetf_url: str | None = None
    issuer: str | None = None
    issuer_url: str | None = None
    ter: str | float | int | None = None
    fund_size: str | float | int | None = None
    distribution_policy: str | None = None
    replication: str | None = None
    fund_domicile: str | None = None
    top_holdings: list[str] | None = None
    source: str | None = "platform"  # Options: "platform", "manual"

    # Additional custom frontmatter fields not explicitly typed
    extra_properties: dict[str, Any] = Field(default_factory=dict)

    # Note markdown body (below YAML frontmatter)
    body: str = ""

    @field_validator("last_updated", mode="before")
    @classmethod
    def _coerce_date_str(cls, v: Any) -> str | None:
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

    def to_frontmatter_dict(self) -> dict[str, Any]:
        """Convert the Asset model into a frontmatter dictionary maintaining standard order."""
        ordered_fields = [
            # 1. Core Position
            "ticker",
            "name",
            "platform",
            "portfolio",
            "quantity",
            "avg_price",
            "current_price",
            "value_pln",
            "currency",
            "asset_type",
            "asset_allocation",
            # 2. Structure & Allocation
            "dominant_sector",
            "industry",
            "sector",
            "country",
            # 3. Valuation & Fundamentals
            "market_cap",
            "pe_ratio",
            "forward_pe",
            "dividend_yield",
            # 4. Technicals & Momentum
            "fifty_two_week_high",
            "fifty_two_week_low",
            "drawdown_52w",
            "sma_50",
            "sma_200",
            "rsi_14",
            "beta",
            # 5. Risk & Quantitative (OpenBB / Morningstar)
            "volatility",
            "sharpe_ratio",
            "max_drawdown",
            "upside_potential",
            "morningstar_rating",
            "morningstar_risk",
            "analyst_rating",
            # 6. ETF Specifics
            "isin",
            "yahoo_ticker",
            "stooq_ticker",
            "issuer",
            "issuer_url",
            "justetf_url",
            "ter",
            "fund_size",
            "distribution_policy",
            "replication",
            "fund_domicile",
            "top_holdings",
            # 7. Meta & Alerts
            "last_updated",
            "source",
            "tags",
        ]

        fm: dict[str, Any] = {}
        for key in ordered_fields:
            val = getattr(self, key, None)
            if key in ["tags", "top_holdings"]:
                if val:
                    fm[key] = list(val)
            elif val is not None:
                fm[key] = val
            elif key in ["avg_price", "morningstar_rating", "morningstar_risk"]:
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
    def from_frontmatter_dict(cls, data: dict[str, Any], body: str = "") -> "Asset":
        """Construct an Asset instance from frontmatter dictionary and markdown body."""
        known_fields = set(cls.model_fields.keys())

        kwargs: dict[str, Any] = {}
        extra: dict[str, Any] = {}

        for k, v in data.items():
            if k in known_fields:
                kwargs[k] = v
            else:
                extra[k] = v

        kwargs["extra_properties"] = extra
        kwargs["body"] = body

        # Ensure minimal required fields
        if "ticker" not in kwargs:
            kwargs["ticker"] = ""
        if "name" not in kwargs:
            kwargs["name"] = ""
        if "platform" not in kwargs:
            kwargs["platform"] = ""
        if "source" not in kwargs or not kwargs["source"]:
            kwargs["source"] = "platform"

        return cls(**kwargs)

    @classmethod
    def from_markdown(cls, content: str) -> "Asset":
        """Parse markdown file content containing YAML frontmatter into an Asset."""
        content = content.lstrip("\ufeff")
        lines = content.splitlines(keepends=True)
        if not lines or lines[0].strip() != "---":
            return cls(ticker="", name="", platform="", body=content)

        end_idx = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_idx = i
                break

        if end_idx == -1:
            return cls(ticker="", name="", platform="", body=content)

        fm_lines = "".join(lines[1:end_idx])
        body = "".join(lines[end_idx + 1 :])

        try:
            fm_dict = yaml.safe_load(fm_lines) or {}
        except Exception:
            fm_dict = {}

        return cls.from_frontmatter_dict(fm_dict, body=body)

    @classmethod
    def from_file(cls, file_path: str) -> "Asset":
        """Load an Asset instance directly from a markdown file path."""
        with open(file_path, encoding="utf-8") as f:
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
                elif any(
                    c in v
                    for c in [":", "#", "[", "]", "{", "}", ",", "&", "*", "?", "|", "-", "<", ">", "=", "!", "%", "@"]
                ):
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
                    if any(
                        c in item_str
                        for c in [
                            ":",
                            "#",
                            "[",
                            "]",
                            "{",
                            "}",
                            ",",
                            "&",
                            "*",
                            "?",
                            "|",
                            "-",
                            "<",
                            ">",
                            "=",
                            "!",
                            "%",
                            "@",
                        ]
                    ):
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
