import os
import sys
import re
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, Union, Set, List

# Ensure script root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.dirname(current_dir)
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

from model.asset import Asset
from integrations.multi_source_asset_enricher import MultiSourceAssetEnricher

_asset_enricher = MultiSourceAssetEnricher()


def parse_number(val: Any) -> Union[int, float]:
    """Parse a string or number into int or float, handling European decimal/thousand separators."""
    if val is None:
        return 0.0
    val_str = str(val).strip().replace('\xa0', '').replace(' ', '')
    if not val_str:
        return 0.0
    if ',' in val_str and '.' in val_str:
        if val_str.find(',') < val_str.find('.'):
            val_str = val_str.replace(',', '')
        else:
            val_str = val_str.replace('.', '').replace(',', '.')
    elif ',' in val_str:
        val_str = val_str.replace(',', '.')
    try:
        f = float(val_str)
        return int(f) if f.is_integer() else f
    except ValueError:
        return 0.0


def sanitize_filename(name: str) -> str:
    """Sanitize a string for safe use as a filename across operating systems."""
    for char in '<>:"/\\|?*':
        name = name.replace(char, '_')
    return name.strip()


def ensure_utf8_file(file_path: str) -> str:
    """Detect encoding of a file, convert it in-place to clean UTF-8 if needed, and return file text."""
    with open(file_path, "rb") as f:
        raw_bytes = f.read()

    # If file starts with UTF-8 BOM, decode and re-save as clean UTF-8
    if raw_bytes.startswith(b'\xef\xbb\xbf'):
        text = raw_bytes.decode('utf-8-sig')
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
        return text

    # Try strict UTF-8
    try:
        text = raw_bytes.decode('utf-8')
        return text
    except UnicodeDecodeError:
        pass

    # Try legacy Polish / European encodings
    detected_encoding = None
    text = None
    for enc in ['cp1250', 'windows-1250', 'iso-8859-2', 'latin2', 'cp1252', 'latin1']:
        try:
            text = raw_bytes.decode(enc)
            detected_encoding = enc
            break
        except Exception:
            continue

    if text is None:
        raise ValueError(f"Could not decode {file_path} with supported encodings.")

    # Convert and fix file on disk in-place as UTF-8
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"Detected {detected_encoding} encoding for {os.path.basename(file_path)} — converted and saved in-place as UTF-8.")
    return text


def determine_asset_type(name: str) -> str:
    """Determine asset type ('equity', 'etf', 'cash') based on asset name keywords."""
    name_upper = name.upper()
    if 'CASH' in name_upper:
        return 'cash'
    etf_keywords = ['ETF', 'UCITS', 'VANGUARD', 'VANECK', 'ISHARES', 'VNGRD', 'INDEX', 'SCTR']
    if any(kw in name_upper for kw in etf_keywords):
        return 'etf'
    return 'equity'


DEFAULT_ISSUER_DISCOVERY_MAPPING: Dict[str, str] = {
    'ishares': 'iShares',
    'vanguard': 'Vanguard',
    'vngrd': 'Vanguard',
    'vaneck': 'VanEck',
    'spdr': 'SPDR',
    'state street': 'SPDR',
    'invesco': 'Invesco',
    'xtrackers': 'Xtrackers',
    'x-trackers': 'Xtrackers',
    'dws': 'Xtrackers',
    'amundi': 'Amundi',
    'lyxor': 'Amundi',
    'hsbc': 'HSBC',
    'wisdomtree': 'WisdomTree',
    'global x': 'Global X',
    'globalx': 'Global X',
    'schwab': 'Schwab',
    'first trust': 'First Trust',
    'beta etf': 'Beta ETF',
    'franklin': 'Franklin Templeton',
    'jpmorgan': 'JPMorgan',
    'jpm ': 'JPMorgan',
}

_issuer_mapping_cache: Optional[Dict[str, str]] = None


def load_issuer_discovery_mapping(base_dir: Optional[str] = None) -> Dict[str, str]:
    """Load etf.issuer.discovery_mapping from config.yaml with built-in fallbacks."""
    global _issuer_mapping_cache
    if _issuer_mapping_cache is not None:
        return _issuer_mapping_cache

    if base_dir is None:
        base_dir = os.path.abspath(os.path.join(scripts_dir, "../.."))

    candidate_paths = [
        os.path.join(base_dir, "99_System", "config.yaml"),
        os.path.join(base_dir, "config.yaml"),
    ]

    import yaml
    for path in candidate_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                if isinstance(cfg, dict):
                    etf_cfg = cfg.get('etf', {})
                    if isinstance(etf_cfg, dict):
                        iss_cfg = etf_cfg.get('issuer', {})
                        if isinstance(iss_cfg, dict):
                            mapping = iss_cfg.get('discovery_mapping')
                            if isinstance(mapping, dict) and mapping:
                                _issuer_mapping_cache = {str(k).lower(): str(v) for k, v in mapping.items()}
                                return _issuer_mapping_cache
            except Exception:
                pass

    _issuer_mapping_cache = DEFAULT_ISSUER_DISCOVERY_MAPPING
    return _issuer_mapping_cache


def load_import_config(base_dir: Optional[str] = None) -> Dict[str, Any]:
    """Load broker import configuration from config.yaml (e.g. default_mode: 'api' or 'csv')."""
    if base_dir is None:
        base_dir = os.path.abspath(os.path.join(scripts_dir, "../.."))

    candidate_paths = [
        os.path.join(base_dir, "99_System", "config.yaml"),
        os.path.join(base_dir, "config.yaml"),
    ]

    import yaml
    for path in candidate_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                if isinstance(cfg, dict) and "import" in cfg and isinstance(cfg["import"], dict):
                    return cfg["import"]
            except Exception:
                pass

    return {
        "exante": {"default_mode": "api"},
        "degiro": {"default_mode": "csv"},
    }


def determine_issuer(name: str, mapping: Optional[Dict[str, str]] = None) -> Optional[str]:
    """Determine ETF issuer from asset name keywords using discovery_mapping from config.yaml."""
    if not name:
        return None
    if mapping is None:
        mapping = load_issuer_discovery_mapping()

    name_lower = name.lower()
    for keyword, issuer_name in mapping.items():
        if keyword in name_lower:
            return issuer_name
    return None


def determine_portfolio(name: str, asset_type: str, dominant_sector: Optional[str] = None) -> Optional[str]:
    """Determine sub-portfolio ('Safety net', 'Long term', 'Aggressive') based on asset attributes."""
    if asset_type == 'cash':
        return None  # Uninvested broker cash is unallocated dry powder (portfolio: null)
    if asset_type == 'equity':
        return 'Aggressive'
    if asset_type == 'etf':
        sec = (dominant_sector or '').lower()
        name_lower = name.lower()
        if 'bond' in name_lower or 'treasury' in name_lower or sec in ['sovereign', 'bonds', 'real estate', 'diversified']:
            return 'Long term'
        return 'Aggressive'
    return 'Long term'


def load_template(base_dir: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """Load the asset template and return frontmatter dictionary and body markdown."""
    template_path = os.path.join(base_dir, "99_System", "Templates", "asset_template.md")
    if not os.path.exists(template_path):
        default_body = (
            "\n# {name} ({ticker})\n\n"
            "**Platform:** [[{platform}]]\n\n"
            "## 📈 Technical & Market Price Chart\n"
            "```dataviewjs\n"
            'await dv.view("99_System/Views/stooq_chart", {\n'
            "    ticker: dv.current().stooq_ticker,\n"
            '    defaultRange: "1Y"\n'
            "});\n"
            "```\n\n"
            "## Investment Thesis / Notes\n"
            "Information about reasoning for buying and keeping this asset.\n"
        )
        return None, default_body
    template_asset = Asset.from_file(template_path)
    return template_asset.to_frontmatter_dict(), template_asset.body


def render_template_body(body_template: str, name: str, ticker: str, platform: str) -> str:
    """Replace template title and platform placeholders in the body with actual values."""
    body = body_template
    body = re.sub(r'^# .+$', f'# {name} ({ticker})', body, count=1, flags=re.MULTILINE)
    body = re.sub(r'\[\[\w+\]\]', f'[[{platform}]]', body, count=1)
    return body


def _inject_justetf_link(body: str, platform: str, justetf_url: Optional[str]) -> str:
    """Inject JustETF profile link below the platform line if not already present."""
    if not justetf_url or justetf_url in body:
        return body
    platform_pattern = rf'(\*\*Platform:\*\* \[\[{re.escape(platform)}\]\])'
    justetf_line = f"\n**JustETF Profile:** [{justetf_url}]({justetf_url})"
    return re.sub(platform_pattern, r'\1' + justetf_line, body, count=1)


def _inject_issuer_link(body: str, platform: str, issuer_url: Optional[str]) -> str:
    """Inject or update Issuer Profile link below JustETF profile or platform line."""
    if not issuer_url:
        return body
    if "**Issuer Profile:**" in body:
        return re.sub(
            r'\*\*Issuer Profile:\*\* \[.*?\]\(.*?\)',
            f'**Issuer Profile:** [{issuer_url}]({issuer_url})',
            body,
            count=1,
        )
    if "**JustETF Profile:**" in body:
        justetf_pattern = r'(\*\*JustETF Profile:\*\* \[.*?\]\(.*?\))'
        issuer_line = f"\n**Issuer Profile:** [{issuer_url}]({issuer_url})"
        return re.sub(justetf_pattern, r'\1' + issuer_line, body, count=1)
    platform_pattern = rf'(\*\*Platform:\*\* \[\[{re.escape(platform)}\]\])'
    issuer_line = f"\n**Issuer Profile:** [{issuer_url}]({issuer_url})"
    return re.sub(platform_pattern, r'\1' + issuer_line, body, count=1)


def save_or_update_asset(
    vault_assets_dir: str,
    platform: str,
    ticker: str,
    name: str,
    quantity: Union[int, float],
    current_price: Union[int, float],
    currency: str,
    avg_price: Optional[Union[int, float]] = None,
    isin: Optional[str] = None,
    current_date: Optional[str] = None,
    template_fm: Optional[Dict[str, Any]] = None,
    template_body: Optional[str] = None,
    source: str = "platform",
    portfolio: Optional[str] = None,
    tags: Optional[List[str]] = None,
    yahoo_ticker: Optional[str] = None,
    asset_allocation: Optional[Dict[str, Any]] = None,
    asset_type: Optional[str] = None,
) -> str:
    """Enrich financial data, create or update asset note in 10_Finance/Assets, and return file path."""
    if not current_date:
        current_date = datetime.now().strftime("%Y-%m-%d")

    safe_ticker = sanitize_filename(ticker)
    file_path = os.path.join(vault_assets_dir, f"{safe_ticker}.md")

    # Check for existing note by ticker or name
    if not os.path.exists(file_path):
        alt_name_path = os.path.join(vault_assets_dir, f"{sanitize_filename(name)}.md")
        if os.path.exists(alt_name_path):
            file_path = alt_name_path

    if not os.path.exists(file_path):
        # Create new asset model
        if not asset_type:
            asset_type = determine_asset_type(name)
        issuer = determine_issuer(name) if asset_type == 'etf' else None

        default_alloc = asset_allocation
        if default_alloc is None:
            if asset_type == 'cash':
                default_alloc = {'cash': 100}
            elif asset_type in ('equity', 'etf'):
                default_alloc = {'equity': 100}

        asset = Asset(
            ticker=ticker,
            name=name,
            platform=platform,
            portfolio=portfolio,
            quantity=quantity,
            avg_price=avg_price,
            current_price=current_price,
            currency=currency,
            asset_type=asset_type,
            asset_allocation=default_alloc,
            issuer=issuer,
            isin=isin,
            yahoo_ticker=yahoo_ticker,
            tags=list(tags) if tags else [],
            last_updated=current_date,
            source=source,
        )
        if template_fm:
            canonical_keys = set(asset.to_frontmatter_dict().keys())
            for k, v in template_fm.items():
                if k not in canonical_keys and v is not None:
                    asset.extra_properties[k] = v

        enriched = _asset_enricher.enrich(asset)
        if portfolio:
            enriched.portfolio = portfolio
        elif not enriched.portfolio:
            enriched.portfolio = determine_portfolio(enriched.name, enriched.asset_type, enriched.dominant_sector)

        if tags:
            for t in tags:
                if t not in enriched.tags:
                    enriched.tags.append(t)

        if template_body:
            body = render_template_body(template_body, name, ticker, platform)
        else:
            body = (
                f"\n# {name} ({ticker})\n\n"
                f"**Platform:** [[{platform}]]\n\n"
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

        enriched.body = _inject_justetf_link(body, platform, enriched.justetf_url)
        enriched.body = _inject_issuer_link(enriched.body, platform, enriched.issuer_url)
        enriched.save(file_path)
        print(f"Created: {os.path.basename(file_path)}")
    else:
        # Update existing asset
        asset = Asset.from_file(file_path)
        asset.platform = platform
        asset.quantity = quantity
        if avg_price is not None:
            asset.avg_price = avg_price
        asset.current_price = current_price
        asset.currency = currency or asset.currency
        asset.last_updated = current_date
        if isin and not asset.isin:
            asset.isin = isin
        if yahoo_ticker and not asset.yahoo_ticker:
            asset.yahoo_ticker = yahoo_ticker
        if not asset.issuer and asset.asset_type == 'etf':
            asset.issuer = determine_issuer(asset.name)
        if portfolio and not asset.portfolio:
            asset.portfolio = portfolio
        if asset_allocation and not asset.asset_allocation:
            asset.asset_allocation = asset_allocation
        if tags:
            for t in tags:
                if t not in asset.tags:
                    asset.tags.append(t)
        asset.source = source
        if 'source' in asset.extra_properties:
            del asset.extra_properties['source']

        # Update body platform link if platform changed
        if asset.body:
            asset.body = re.sub(r'\*\*Platform:\*\* \[\[.*?\]\]', f'**Platform:** [[{platform}]]', asset.body)

        enriched = _asset_enricher.enrich(asset)
        if portfolio and not enriched.portfolio:
            enriched.portfolio = portfolio
        elif not enriched.portfolio:
            enriched.portfolio = determine_portfolio(enriched.name, enriched.asset_type, enriched.dominant_sector)
        enriched.body = _inject_justetf_link(enriched.body, platform, enriched.justetf_url)
        enriched.body = _inject_issuer_link(enriched.body, platform, enriched.issuer_url)
        enriched.save(file_path)
        print(f"Updated: {os.path.basename(file_path)}")

    return file_path


def remove_missing_platform_assets(
    vault_assets_dir: str,
    platform: str,
    active_asset_paths: Set[str],
    active_tickers: Optional[Set[str]] = None,
) -> List[str]:
    """Verify all existing platform assets in vault_assets_dir against active_asset_paths/active_tickers.

    Any existing asset whose platform matches (case-insensitive) and whose source is 'platform'
    (or not explicitly 'manual'), but is not present in active_asset_paths and active_tickers,
    will be removed from 10_Finance/Assets.

    Safety checks:
    - If active_asset_paths is empty, no deletions are performed to prevent accidental wipeouts
      caused by empty or unparseable export files.
    - Assets with source == 'manual' are protected and never removed.
    """
    if not active_asset_paths:
        print(f"Warning: No valid assets found in import for {platform}. Skipping removal of missing assets for safety.")
        return []

    normalized_active_paths = {os.path.normpath(os.path.abspath(p)) for p in active_asset_paths}
    normalized_active_tickers = {t.strip().lower() for t in active_tickers} if active_tickers else set()
    removed_assets: List[str] = []

    if not os.path.exists(vault_assets_dir):
        return []

    target_plat = platform.strip().lower()

    for fname in sorted(os.listdir(vault_assets_dir)):
        if not fname.endswith('.md'):
            continue
        file_path = os.path.join(vault_assets_dir, fname)
        norm_path = os.path.normpath(os.path.abspath(file_path))
        if norm_path in normalized_active_paths:
            continue

        try:
            asset = Asset.from_file(file_path)
            asset_plat = (asset.platform or '').strip().lower()

            if asset_plat == target_plat:
                # Manual assets must never be removed by broker platform imports
                asset_source = (asset.source or '').strip().lower()
                if asset_source == 'manual':
                    continue

                # Check if ticker was imported under another filename
                if asset.ticker and asset.ticker.strip().lower() in normalized_active_tickers:
                    continue

                os.remove(file_path)
                removed_assets.append(fname)
                print(f"Removed missing platform asset: {fname} ({asset.name or asset.ticker})")
        except Exception as e:
            print(f"Warning: could not evaluate {fname} for removal: {e}")

    if removed_assets:
        print(f"Total removed {platform} assets missing from import: {len(removed_assets)}")
    return removed_assets
