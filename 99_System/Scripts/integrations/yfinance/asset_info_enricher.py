import copy
import os
import sys

# Ensure scripts dir is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
integrations_dir = os.path.dirname(current_dir)
scripts_dir = os.path.dirname(integrations_dir)
for p in (scripts_dir, integrations_dir):
    if p not in sys.path:
        sys.path.append(p)

from model.asset import Asset

from integrations.base import BaseAssetInfoEnricher
from integrations.sector_classifier import determine_dominant_sector, fetch_etf_holdings_data
from integrations.yfinance.service import (
    apply_overvalued_tag,
    calculate_value_pln,
    fetch_yfinance_analyst_rating,
    fetch_yfinance_data,
)


class YFinanceAssetInfoEnricher(BaseAssetInfoEnricher):
    """Asset info enricher for Yahoo Finance.

    Provides market capitalization, P/E ratios, dividend yields, country,
    sector / industry classifications, analyst ratings, and live FX rates.
    """

    @property
    def name(self) -> str:
        return "YFinance"

    def can_enrich(self, asset: Asset) -> bool:
        """YFinance supports equities and ETFs (cash holdings do not require quote lookups)."""
        return asset.asset_type != "cash"

    def enrich(self, asset: Asset) -> Asset | None:
        """Fetch metadata from Yahoo Finance and return a new cloned and enriched Asset."""
        print(f"Fetching Yahoo Finance info for {asset.name} ({asset.ticker})...")
        data = fetch_yfinance_data(isin=asset.isin or asset.ticker, name=asset.name, ticker=asset.ticker)

        cloned = copy.deepcopy(asset)

        if not data:
            value_pln = calculate_value_pln(cloned.quantity, cloned.current_price, cloned.currency)
            if value_pln is not None:
                cloned.value_pln = value_pln
            return cloned

        value_pln = calculate_value_pln(cloned.quantity, cloned.current_price, cloned.currency)
        if value_pln is not None:
            cloned.value_pln = value_pln

        yahoo_ticker = data.get("yahoo_ticker")
        if yahoo_ticker:
            cloned.yahoo_ticker = yahoo_ticker

        if data.get("sector"):
            cloned.sector = data["sector"]
        if data.get("industry"):
            cloned.industry = data["industry"]
        if data.get("country"):
            cloned.country = data["country"]
        if data.get("market_cap"):
            cloned.market_cap = data["market_cap"]
        if data.get("pe_ratio") is not None:
            cloned.pe_ratio = data["pe_ratio"]
        if data.get("forward_pe") is not None:
            cloned.forward_pe = data["forward_pe"]
        if data.get("dividend_yield"):
            cloned.dividend_yield = data["dividend_yield"]
        if data.get("beta") is not None:
            cloned.beta = data["beta"]
        if data.get("fifty_two_week_high") is not None:
            cloned.fifty_two_week_high = data["fifty_two_week_high"]
        if data.get("fifty_two_week_low") is not None:
            cloned.fifty_two_week_low = data["fifty_two_week_low"]
        if data.get("drawdown_52w"):
            cloned.drawdown_52w = data["drawdown_52w"]
        if data.get("sma_50") is not None:
            cloned.sma_50 = data["sma_50"]
        if data.get("sma_200") is not None:
            cloned.sma_200 = data["sma_200"]
        if data.get("rsi_14") is not None:
            cloned.rsi_14 = data["rsi_14"]
        if data.get("morningstar_rating") is not None:
            cloned.morningstar_rating = data["morningstar_rating"]
        if data.get("morningstar_risk") is not None:
            cloned.morningstar_risk = data["morningstar_risk"]

        # Analyst rating from Yahoo
        if yahoo_ticker:
            rating = fetch_yfinance_analyst_rating(yahoo_ticker)
            if rating:
                cloned.analyst_rating = rating

        # Tags (overvalued alert)
        tags_list = list(cloned.tags) if cloned.tags else []
        if "tags" in data:
            for t in data["tags"]:
                if t not in tags_list:
                    tags_list.append(t)
        cloned.tags = apply_overvalued_tag(tags_list, cloned.pe_ratio)

        # Sector classification
        if cloned.asset_type == "etf":
            holdings, _ = fetch_etf_holdings_data(cloned.isin, ticker=cloned.ticker, name=cloned.name)
            if holdings:
                dom_sec = determine_dominant_sector(holdings)
                if dom_sec:
                    cloned.dominant_sector = dom_sec
        else:
            raw_sec = data.get("sector") or data.get("industry")
            if raw_sec:
                dom_sec = determine_dominant_sector({raw_sec: 100.0})
                if dom_sec:
                    cloned.dominant_sector = dom_sec
                    if not cloned.industry:
                        cloned.industry = dom_sec

        return cloned
