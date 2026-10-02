import os
import sys
import re
import unicodedata
import threading
import concurrent.futures
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, Union, Set, List, Sequence

# Configure UTF-8 encoding for stdout/stderr on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure script root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.dirname(current_dir)
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

from model.asset import Asset
from model.config import load_vault_config
from integrations.multi_source_asset_enricher import MultiSourceAssetEnricher
from ui_progress import create_progress

_asset_enricher = MultiSourceAssetEnricher()
_concurrency_lock = threading.Lock()


def get_in(obj: Any, path: Union[str, Sequence[Any]], default: Any = None) -> Any:
    """Safely traverse a nested dict/list hierarchy by path (e.g. 'etf.issuer.discovery_mapping' or ['etf', 'issuer'])."""
    if obj is None:
        return default
    keys = path.split('.') if isinstance(path, str) else path
    cur = obj
    for key in keys:
        if isinstance(cur, dict):
            cur = cur.get(key)
        elif isinstance(cur, (list, tuple)) and isinstance(key, int):
            try:
                cur = cur[key]
            except (IndexError, TypeError):
                return default
        else:
            return default
        if cur is None:
            return default
    return cur


def get_max_workers(configured_workers: Optional[int] = None, base_dir: Optional[str] = None) -> int:
    """Determine the number of worker threads to use for parallel execution.

    1. If configured_workers is provided and > 0, returns it.
    2. Otherwise, checks config.yaml for concurrency.max_workers.
    3. If set to 'auto', <= 0, or omitted: detects and returns os.cpu_count() or 4.
    """
    if configured_workers is not None and int(configured_workers) > 0:
        return int(configured_workers)

    vault_cfg = load_vault_config(base_dir=base_dir)
    return vault_cfg.concurrency.resolve_worker_count()


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


KNOWN_ETF_NAMES: Dict[str, str] = {
    'IE000YYE6WK5': 'VanEck Defense UCITS ETF',
    'IE00B43HR379': 'iShares S&P 500 Health Care Sector UCITS ETF',
    'IE00B8GKDB10': 'Vanguard FTSE All-World High Dividend Yield UCITS ETF',
    'IE00BK5BQT80': 'Vanguard FTSE All-World UCITS ETF',
    'IE00BMVB5P51': 'Vanguard LifeStrategy 60% Equity UCITS ETF',
    'IE00BMVB5R75': 'Vanguard LifeStrategy 80% Equity UCITS ETF',
    'NL0011683594': 'VanEck Morningstar Developed Markets Dividend Leaders UCITS ETF',
    'IE00B3RBWM25': 'Vanguard FTSE All-World UCITS ETF Distributing',
    'IE00B5BMR087': 'iShares Core S&P 500 UCITS ETF',
    'IE00B4L5Y983': 'iShares Core MSCI World UCITS ETF',
    'IE00BFY0GT14': 'SPDR MSCI World UCITS ETF',
}


def clean_asset_display_name(
    name: str,
    isin: Optional[str] = None,
    ticker: Optional[str] = None
) -> str:
    """Clean and standardize an asset's display name, resolving known ETF names and stripping truncation."""
    isin_key = (isin or ticker or "").strip().upper()
    if isin_key in KNOWN_ETF_NAMES:
        return KNOWN_ETF_NAMES[isin_key]

    clean = (name or "").strip()
    # Strip trailing ellipsis and periods
    clean = re.sub(r'[\.\s]+$', '', clean)
    return clean if clean else (ticker or "Unnamed Asset")


def slugify_asset_name(
    name: str,
    ticker: Optional[str] = None,
    platform: Optional[str] = None,
    asset_type: Optional[str] = None,
    isin: Optional[str] = None,
) -> str:
    """Generate a clean, filesystem-safe lowercase snake_case filename slug from an asset name.

    Rules:
    - Cash holdings retain standard platform cash ticker (e.g. DEGIRO_CASH_EUR).
    - Retail treasury bonds (PKO BP) retain bond series code.
    - S&P shorthand is preserved as 'sp' (e.g. 'ishares_sp_500_...').
    - Polish & accented characters normalized to ASCII.
    - Punctuation & symbols stripped, spaces replaced with underscores, lowercase.
    """
    plat_upper = (platform or "").upper().strip()
    tick_str = (ticker or "").strip()

    # Cash holdings keep standard platform cash ticker (e.g. DEGIRO_CASH_EUR)
    if asset_type == "cash" or (tick_str and "CASH" in tick_str.upper()):
        return sanitize_filename(tick_str or name)

    # Retail treasury bonds keep bond series code
    if plat_upper == "PKOBP":
        return sanitize_filename(tick_str or name)

    # Resolve display name
    display_name = clean_asset_display_name(name, isin=isin, ticker=ticker)

    clean_name = display_name
    # Normalize corporate suffixes and abbreviations
    clean_name = re.sub(r'\bS\.A\.?', 'SA', clean_name, flags=re.IGNORECASE)
    clean_name = re.sub(r'\bCorporation\b', 'Corp', clean_name, flags=re.IGNORECASE)
    clean_name = re.sub(r'\bIncorporated\b', 'Inc', clean_name, flags=re.IGNORECASE)
    clean_name = re.sub(r'\bS&P\b', 'SP', clean_name, flags=re.IGNORECASE)
    clean_name = clean_name.replace('&', ' and ')
    clean_name = clean_name.replace('%', ' ')

    # Normalize unicode accents
    clean_name = clean_name.replace('ł', 'l').replace('Ł', 'L')
    clean_name = unicodedata.normalize('NFKD', clean_name).encode('ascii', 'ignore').decode('ascii')

    # Remove non-alphanumeric
    clean_name = re.sub(r'[^a-zA-Z0-9\s]', ' ', clean_name)

    # Account suffix handling (e.g. _IKE, _IKZE) to avoid filename collisions across accounts/brokers
    account_suffix = ""
    if tick_str.upper().endswith("_IKZE"):
        account_suffix = "_ikze"
    elif tick_str.upper().endswith("_IKE"):
        account_suffix = "_ike"

    # Convert to lowercase snake_case
    slug = '_'.join(clean_name.lower().split())
    if not slug:
        slug = sanitize_filename(tick_str).lower() if tick_str else "unnamed_asset"

    if account_suffix and not slug.endswith(account_suffix):
        slug = f"{slug}{account_suffix}"

    return slug



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
    vault_cfg = load_vault_config(base_dir=base_dir)
    mapping = vault_cfg.etf.issuer.discovery_mapping
    return {str(k).lower(): str(v) for k, v in mapping.items()}


def load_import_config(base_dir: Optional[str] = None) -> Dict[str, Any]:
    """Load broker import configuration from config.yaml (e.g. default_mode: 'api' or 'csv')."""
    vault_cfg = load_vault_config(base_dir=base_dir)
    return {k: v.model_dump() for k, v in vault_cfg.import_config.items()}


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


def load_template(base_dir: str) -> Tuple[Dict[str, Any], str]:
    """Load the asset template and return frontmatter dictionary and body markdown.

    Raises:
        FileNotFoundError: If asset_template.md is missing in the templates directory.
    """
    template_path = os.path.join(base_dir, "99_System", "Templates", "asset_template.md")
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Required asset template not found at: {template_path}")
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
    dominant_sector: Optional[str] = None,
    industry: Optional[str] = None,
    sector: Optional[str] = None,
    stooq_ticker: Optional[str] = None,
    country: Optional[str] = None,
) -> str:
    """Enrich financial data, create or update asset note in 10_Finance/Assets, and return file path."""
    if not current_date:
        current_date = datetime.now().strftime("%Y-%m-%d")

    # Clean and resolve display name
    display_name = clean_asset_display_name(name, isin=isin, ticker=ticker)
    name = display_name

    target_slug = slugify_asset_name(
        name=name,
        ticker=ticker,
        platform=platform,
        asset_type=asset_type,
        isin=isin
    )
    target_file_path = os.path.join(vault_assets_dir, f"{target_slug}.md")

    # Locate existing note
    file_path = None
    if os.path.exists(target_file_path):
        file_path = target_file_path
    else:
        # Check alternative legacy filenames
        safe_ticker = sanitize_filename(ticker)
        legacy_ticker_path = os.path.join(vault_assets_dir, f"{safe_ticker}.md")
        if os.path.exists(legacy_ticker_path):
            file_path = legacy_ticker_path
        else:
            legacy_name_path = os.path.join(vault_assets_dir, f"{sanitize_filename(name)}.md")
            if os.path.exists(legacy_name_path):
                file_path = legacy_name_path

    # If still not found, check existing notes by frontmatter ticker or isin within same platform and account type
    if not file_path and os.path.exists(vault_assets_dir):
        t_clean = (ticker or "").strip().lower()
        isin_clean = (isin or "").strip().lower() if isin else None
        target_plat = (platform or "").strip().lower()
        for fname in os.listdir(vault_assets_dir):
            if not fname.endswith(".md"):
                continue
            cand_path = os.path.join(vault_assets_dir, fname)
            try:
                cand_asset = Asset.from_file(cand_path)
                cand_plat = (cand_asset.platform or "").strip().lower()
                cand_t = (cand_asset.ticker or "").strip().lower()
                cand_isin = (cand_asset.isin or "").strip().lower() if cand_asset.isin else None

                # CRITICAL: Do NOT match an asset from a different platform!
                if target_plat and cand_plat and target_plat != cand_plat:
                    continue

                # Account suffix protection: match _ikze or _ike if present
                if t_clean.endswith(("_ikze", "_ike")) and not cand_t.endswith(("_ikze", "_ike")):
                    continue
                if not t_clean.endswith(("_ikze", "_ike")) and cand_t.endswith(("_ikze", "_ike")):
                    continue

                if (t_clean and cand_t == t_clean) or (isin_clean and cand_isin == isin_clean):
                    file_path = cand_path
                    break
            except Exception:
                continue

    # Auto-rename legacy ticker note to clean target slug if needed
    if file_path and file_path != target_file_path and os.path.exists(file_path) and not os.path.exists(target_file_path):
        try:
            os.rename(file_path, target_file_path)
            print(f"Renamed legacy asset note: {os.path.basename(file_path)} -> {os.path.basename(target_file_path)}")
            file_path = target_file_path
        except Exception as e:
            sys.stderr.write(f"Warning: could not rename {file_path} to {target_file_path}: {e}\n")

    if not file_path:
        file_path = target_file_path

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
            stooq_ticker=stooq_ticker,
            tags=list(tags) if tags else [],
            last_updated=current_date,
            source=source,
        )
        if dominant_sector:
            asset.dominant_sector = dominant_sector
        if industry:
            asset.industry = industry
        if sector:
            asset.sector = sector
        if country:
            asset.country = country

        if template_fm:
            canonical_keys = set(Asset.model_fields.keys())
            for k, v in template_fm.items():
                if k not in canonical_keys and v is not None:
                    asset.extra_properties[k] = v

        enriched = _asset_enricher.enrich(asset)
        if portfolio:
            enriched.portfolio = portfolio
        elif not enriched.portfolio:
            enriched.portfolio = determine_portfolio(enriched.name, enriched.asset_type, enriched.dominant_sector)

        if dominant_sector:
            enriched.dominant_sector = dominant_sector
        if industry:
            enriched.industry = industry
        if sector:
            enriched.sector = sector
        if stooq_ticker:
            enriched.stooq_ticker = stooq_ticker
        if country:
            enriched.country = country

        if tags:
            for t in tags:
                if t not in enriched.tags:
                    enriched.tags.append(t)

        if asset_type == 'cash':
            body = (
                f"\n# {name} ({ticker})\n\n"
                f"**Platform:** [[{platform}]]\n\n"
                f"## Investment Thesis / Notes\n"
                f"Information about reasoning for buying and keeping this asset.\n"
            )
        elif template_body:
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
        if display_name and (not asset.name or asset.name.endswith('...') or asset.name.endswith('..') or asset.name == asset.ticker):
            asset.name = display_name
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
        if stooq_ticker and not asset.stooq_ticker:
            asset.stooq_ticker = stooq_ticker
        if not asset.issuer and asset.asset_type == 'etf':
            asset.issuer = determine_issuer(asset.name)
        if portfolio and not asset.portfolio:
            asset.portfolio = portfolio
        if asset_allocation and not asset.asset_allocation:
            asset.asset_allocation = asset_allocation
        if dominant_sector:
            asset.dominant_sector = dominant_sector
        if industry:
            asset.industry = industry
        if sector:
            asset.sector = sector
        if country:
            asset.country = country
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

        if dominant_sector:
            enriched.dominant_sector = dominant_sector
        if industry:
            enriched.industry = industry
        if sector:
            enriched.sector = sector
        if stooq_ticker:
            enriched.stooq_ticker = stooq_ticker
        if country:
            enriched.country = country

        enriched.body = _inject_justetf_link(enriched.body, platform, enriched.justetf_url)
        enriched.body = _inject_issuer_link(enriched.body, platform, enriched.issuer_url)
        enriched.save(file_path)
        print(f"Updated: {os.path.basename(file_path)}")

    return file_path


def save_or_update_assets_parallel(
    asset_tasks: List[Dict[str, Any]],
    max_workers: Optional[int] = None,
    base_dir: Optional[str] = None,
    show_progress: bool = True,
) -> Tuple[Set[str], Set[str], int]:
    """Execute asset enrichment and saving concurrently using ThreadPoolExecutor.

    Parameters:
        asset_tasks: List of keyword-argument dicts for save_or_update_asset.
        max_workers: Optional number of worker threads. If omitted/None, automatically
                     detects the CPU hardware threads count (os.cpu_count()).
        base_dir: Optional base repository directory.
        show_progress: Whether to display a real-time Rich progress bar during enrichment.

    Returns:
        Tuple of (active_asset_paths: Set[str], active_tickers: Set[str], imported_count: int)
    """
    if not asset_tasks:
        return set(), set(), 0

    workers = get_max_workers(max_workers, base_dir=base_dir)
    print(f"⚡ Processing {len(asset_tasks)} asset(s) concurrently across {workers} worker threads...")

    active_paths: Set[str] = set()
    active_tickers: Set[str] = set()
    imported_count = 0

    def _worker(task: Dict[str, Any]) -> Tuple[str, str, Optional[str]]:
        fpath = save_or_update_asset(**task)
        ticker = task.get("ticker", "")
        isin = task.get("isin")
        return fpath, ticker, isin

    with create_progress(disable=not show_progress) as progress:
        task_id = progress.add_task(
            "[bold cyan]Enriching & saving assets[/bold cyan]",
            total=len(asset_tasks),
            status="Starting...",
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_task = {executor.submit(_worker, task): task for task in asset_tasks}
            for future in concurrent.futures.as_completed(future_to_task):
                task = future_to_task[future]
                label = task.get("ticker") or task.get("name") or "Asset"
                try:
                    fpath, ticker, isin = future.result()
                    active_paths.add(fpath)
                    if ticker:
                        active_tickers.add(ticker)
                    if isin:
                        active_tickers.add(isin)
                    imported_count += 1
                    progress.update(task_id, advance=1, status=f"[green]✓[/green] {label}")
                except Exception as e:
                    progress.update(task_id, advance=1, status=f"[red]✗[/red] {label}")
                    if hasattr(progress, "console") and progress.console:
                        progress.console.print(f"[red]Error processing asset {label}:[/red] {e}")
                    else:
                        sys.stderr.write(f"Error processing asset {label}: {e}\n")

        progress.update(task_id, status="[bold green]Completed[/bold green]")

    return active_paths, active_tickers, imported_count


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

                os.remove(file_path)
                removed_assets.append(fname)
                print(f"Removed missing platform asset: {fname} ({asset.name or asset.ticker})")
        except Exception as e:
            print(f"Warning: could not evaluate {fname} for removal: {e}")

    if removed_assets:
        print(f"Total removed {platform} assets missing from import: {len(removed_assets)}")
    return removed_assets
