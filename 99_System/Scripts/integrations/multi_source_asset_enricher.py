import os
import sys
import copy
from typing import Optional, List, Dict

# Ensure scripts dir is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.dirname(current_dir)
for p in (scripts_dir, current_dir):
    if p not in sys.path:
        sys.path.append(p)

from model.asset import Asset
from integrations.base import BaseAssetInfoEnricher
from integrations.justetf.asset_info_enricher import JustETFAssetInfoEnricher
from integrations.ishares.asset_info_enricher import ISharesAssetInfoEnricher
from integrations.yfinance.asset_info_enricher import YFinanceAssetInfoEnricher
from integrations.finnhub.asset_info_enricher import FinnhubAssetInfoEnricher
from integrations.openbb.asset_info_enricher import OpenBBAssetInfoEnricher
from integrations.vanguard.asset_info_enricher import VanguardAssetInfoEnricher
from integrations.vaneck.asset_info_enricher import VanEckAssetInfoEnricher
from integrations.exante.asset_info_enricher import ExanteAssetInfoEnricher
from integrations.stooq.asset_info_enricher import StooqAssetInfoEnricher
from integrations.yfinance.service import (
    calculate_value_pln,
    apply_overvalued_tag,
)
from integrations.justetf.service import (
    apply_delisting_risk_tag,
)
from integrations.sector_classifier import determine_dominant_sector


class MultiSourceAssetEnricher(BaseAssetInfoEnricher):
    """Multi-source asset info enricher that queries multiple integrations in priority order.

    Default priority hierarchy:
        Exante > JustETF > IShares > Vanguard > VanEck > YFinance > Stooq > OpenBB > Finnhub

    Merging Rules:
        - Always produces and returns a cloned Asset object (non-mutating).
        - Non-empty values from higher priority integrations take precedence.
        - Null / empty fields are populated by subsequent integrations providing data.
        - Alerts / tags are joined across all integration sources.
        - Analyst ratings from multiple sources are aggregated with source labels (e.g. ['YFinance: Strong Buy', 'Finnhub: Buy']).
        - Total value in PLN is updated via live FX exchange rates.
    """

    def __init__(self, enrichers: Optional[List[BaseAssetInfoEnricher]] = None):
        if enrichers is not None:
            self.enrichers = enrichers
        else:
            # Default priority: Exante > JustETF > IShares > Vanguard > VanEck > YFinance > Stooq > OpenBB > Finnhub
            self.enrichers = [
                ExanteAssetInfoEnricher(),
                JustETFAssetInfoEnricher(),
                ISharesAssetInfoEnricher(),
                VanguardAssetInfoEnricher(),
                VanEckAssetInfoEnricher(),
                YFinanceAssetInfoEnricher(),
                StooqAssetInfoEnricher(),
                OpenBBAssetInfoEnricher(),
                FinnhubAssetInfoEnricher(),
            ]

    @property
    def name(self) -> str:
        return f"MultiSourceEnricher({', '.join(e.name for e in self.enrichers)})"

    def enrich(self, asset: Asset) -> Asset:
        """Enrich the asset by querying integrations in priority order and returning a cloned result."""
        # Always clone the input asset
        merged = copy.deepcopy(asset)

        # Handle Cash holdings
        if merged.asset_type == 'cash' or (merged.ticker and merged.ticker.startswith(f"{merged.platform.upper()}_CASH")):
            merged.asset_type = 'cash'
            merged.dominant_sector = 'Cash'
            merged.industry = 'Cash'
            merged.sector = None
            merged.country = None
            merged.market_cap = None
            merged.pe_ratio = None
            merged.forward_pe = None
            merged.dividend_yield = None
            merged.fifty_two_week_high = None
            merged.fifty_two_week_low = None
            merged.drawdown_52w = None
            merged.sma_50 = None
            merged.sma_200 = None
            merged.rsi_14 = None
            merged.beta = None
            merged.analyst_rating = None
            merged.yahoo_ticker = None
            merged.stooq_ticker = None
            merged.issuer = None
            merged.issuer_url = None
            merged.justetf_url = None
            merged.ter = None
            merged.fund_size = None
            merged.distribution_policy = None
            merged.replication = None
            merged.fund_domicile = None
            merged.top_holdings = None
            merged.extra_properties = {}
            merged.tags = [t for t in (merged.tags or []) if not (str(t).startswith('#alert') or str(t).startswith('alert/'))]
            if merged.platform and merged.platform.lower() in ('degiro', 'exante'):
                merged.portfolio = None
            merged.value_pln = calculate_value_pln(merged.quantity, merged.current_price, merged.currency) or merged.value_pln
            return merged

        # Handle Bond holdings (e.g. Polish treasury retail bonds)
        if merged.asset_type == 'bond' or (merged.platform and merged.platform.upper() == 'PKOBP'):
            merged.asset_type = 'bond'
            merged.dominant_sector = 'Sovereign'
            merged.industry = 'Sovereign'
            merged.sector = 'Sovereign'
            if not merged.stooq_ticker:
                merged.stooq_ticker = '10ply.b'
            if not merged.asset_allocation:
                merged.asset_allocation = {'bonds': 100}
            merged.tags = [t for t in (merged.tags or []) if not (str(t).startswith('#alert') or str(t).startswith('alert/'))]
            merged.value_pln = calculate_value_pln(merged.quantity, merged.current_price, merged.currency) or (merged.quantity * merged.current_price)
            return merged

        scalar_fields = [
            'justetf_url', 'issuer', 'issuer_url', 'ter', 'fund_size', 'distribution_policy', 'replication',
            'fund_domicile', 'yahoo_ticker', 'stooq_ticker', 'isin', 'country', 'market_cap',
            'pe_ratio', 'forward_pe', 'dividend_yield', 'beta',
            'fifty_two_week_high', 'fifty_two_week_low', 'drawdown_52w',
            'sma_50', 'sma_200', 'rsi_14',
            'volatility', 'sharpe_ratio', 'max_drawdown', 'upside_potential',
            'morningstar_rating', 'morningstar_risk', 'sector', 'industry', 'dominant_sector'
        ]

        # Accumulators: initialize tags with only non-alert tags from the existing asset.
        # Active alert tags will be populated dynamically from new enriched data.
        non_alert_tags = [t for t in (merged.tags or []) if not (str(t).startswith('#alert') or str(t).startswith('alert/'))]
        collected_tags: List[str] = list(non_alert_tags)
        collected_ratings: Dict[str, str] = {}  # source_name -> rating
        populated_fields = set()

        # Existing rating on asset (if any)
        initial_rating = None
        if merged.analyst_rating:
            if isinstance(merged.analyst_rating, list):
                for r in merged.analyst_rating:
                    if ':' in str(r):
                        src, val = str(r).split(':', 1)
                        if src.strip() != 'Initial':
                            collected_ratings[src.strip()] = val.strip()
                    else:
                        initial_rating = str(r).strip()
            elif isinstance(merged.analyst_rating, str):
                if ':' in merged.analyst_rating:
                    src, val = merged.analyst_rating.split(':', 1)
                    if src.strip() != 'Initial':
                        collected_ratings[src.strip()] = val.strip()
                else:
                    initial_rating = merged.analyst_rating.strip()

        # Query enrichers in priority order
        for enricher in self.enrichers:
            if not enricher.can_enrich(merged):
                continue

            try:
                enrich_target = copy.deepcopy(merged)
                enrich_target.analyst_rating = None
                enriched = enricher.enrich(enrich_target)
            except Exception as e:
                sys.stderr.write(f"Enricher {enricher.name} failed for {merged.ticker}: {e}\n")
                enriched = None

            if not enriched:
                continue

            # Merge scalar fields: highest priority enricher providing non-empty data wins
            for field in scalar_fields:
                if field not in populated_fields:
                    new_val = getattr(enriched, field, None)
                    if new_val is not None and new_val != "":
                        setattr(merged, field, new_val)
                        populated_fields.add(field)

            # Merge tags
            if enriched.tags:
                for t in enriched.tags:
                    if t and t not in collected_tags:
                        collected_tags.append(t)

            # Merge analyst ratings with source labeling
            if enriched.analyst_rating:
                r_val = enriched.analyst_rating
                if isinstance(r_val, str) and r_val.strip():
                    collected_ratings[enricher.name] = r_val.strip()
                elif isinstance(r_val, list):
                    for item in r_val:
                        if ':' in str(item):
                            s, v = str(item).split(':', 1)
                            collected_ratings[s.strip()] = v.strip()
                        else:
                            collected_ratings[enricher.name] = str(item).strip()

        # Finalize analyst ratings
        if collected_ratings:
            if len(collected_ratings) > 1:
                merged.analyst_rating = [f"{src}: {val}" for src, val in collected_ratings.items()]
            else:
                single_src, single_val = next(iter(collected_ratings.items()))
                merged.analyst_rating = f"{single_src}: {single_val}"
        elif initial_rating:
            merged.analyst_rating = initial_rating
        else:
            merged.analyst_rating = None

        # Re-evaluate / synchronize alert tags
        collected_tags = apply_overvalued_tag(collected_tags, merged.pe_ratio)
        collected_tags = apply_delisting_risk_tag(collected_tags, merged.fund_size)
        merged.tags = collected_tags

        # Ensure dominant sector fallback if available
        if not merged.dominant_sector and (merged.sector or merged.industry):
            raw = merged.sector or merged.industry
            merged.dominant_sector = determine_dominant_sector({raw: 100.0})
            if not merged.industry:
                merged.industry = merged.dominant_sector

        # Recalculate value in PLN using live FX rates
        new_val_pln = calculate_value_pln(merged.quantity, merged.current_price, merged.currency)
        if new_val_pln is not None:
            merged.value_pln = new_val_pln

        return merged
