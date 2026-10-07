import os
import re
import sys
import threading
import unicodedata
from collections.abc import Sequence
from typing import Any

# Configure UTF-8 encoding for stdout/stderr on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure script root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.dirname(current_dir)
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

from integrations.multi_source_asset_enricher import MultiSourceAssetEnricher
from model.config import load_vault_config

_asset_enricher = MultiSourceAssetEnricher()
_concurrency_lock = threading.Lock()


def get_in(obj: Any, path: str | Sequence[Any], default: Any = None) -> Any:
    """Safely traverse a nested dict/list hierarchy by path (e.g. 'etf.issuer.discovery_mapping' or ['etf', 'issuer'])."""
    if obj is None:
        return default
    keys = path.split(".") if isinstance(path, str) else path
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


def get_max_workers(configured_workers: int | None = None, base_dir: str | None = None) -> int:
    """Determine the number of worker threads to use for parallel execution.

    1. If configured_workers is provided and > 0, returns it.
    2. Otherwise, checks config.yaml for concurrency.max_workers.
    3. If set to 'auto', <= 0, or omitted: detects and returns os.cpu_count() or 4.
    """
    if configured_workers is not None and int(configured_workers) > 0:
        return int(configured_workers)

    vault_cfg = load_vault_config(base_dir=base_dir)
    return vault_cfg.concurrency.resolve_worker_count()


def parse_number(val: Any) -> int | float:
    """Parse a string or number into int or float, handling European decimal/thousand separators."""
    if val is None:
        return 0.0
    val_str = str(val).strip().replace("\xa0", "").replace(" ", "")
    if not val_str:
        return 0.0
    if "," in val_str and "." in val_str:
        if val_str.find(",") < val_str.find("."):
            val_str = val_str.replace(",", "")
        else:
            val_str = val_str.replace(".", "").replace(",", ".")
    elif "," in val_str:
        val_str = val_str.replace(",", ".")
    try:
        f = float(val_str)
        return int(f) if f.is_integer() else f
    except ValueError:
        return 0.0


def sanitize_filename(name: str) -> str:
    """Sanitize a string for safe use as a filename across operating systems."""
    for char in '<>:"/\\|?*':
        name = name.replace(char, "_")
    return name.strip()


KNOWN_ETF_NAMES: dict[str, str] = {
    "IE000YYE6WK5": "VanEck Defense UCITS ETF",
    "IE00B43HR379": "iShares S&P 500 Health Care Sector UCITS ETF",
    "IE00B8GKDB10": "Vanguard FTSE All-World High Dividend Yield UCITS ETF",
    "IE00BK5BQT80": "Vanguard FTSE All-World UCITS ETF",
    "IE00BMVB5P51": "Vanguard LifeStrategy 60% Equity UCITS ETF",
    "IE00BMVB5R75": "Vanguard LifeStrategy 80% Equity UCITS ETF",
    "NL0011683594": "VanEck Morningstar Developed Markets Dividend Leaders UCITS ETF",
    "IE00B3RBWM25": "Vanguard FTSE All-World UCITS ETF Distributing",
    "IE00B5BMR087": "iShares Core S&P 500 UCITS ETF",
    "IE00B4L5Y983": "iShares Core MSCI World UCITS ETF",
    "IE00BFY0GT14": "SPDR MSCI World UCITS ETF",
}


def clean_asset_display_name(name: str, isin: str | None = None, ticker: str | None = None) -> str:
    """Clean and standardize an asset's display name, resolving known ETF names and stripping truncation."""
    isin_key = (isin or ticker or "").strip().upper()
    if isin_key in KNOWN_ETF_NAMES:
        return KNOWN_ETF_NAMES[isin_key]

    clean = (name or "").strip()
    # Strip trailing ellipsis and periods
    clean = re.sub(r"[\.\s]+$", "", clean)
    return clean if clean else (ticker or "Unnamed Asset")


def slugify_asset_name(
    name: str,
    ticker: str | None = None,
    platform: str | None = None,
    asset_type: str | None = None,
    isin: str | None = None,
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
    clean_name = re.sub(r"\bS\.A\.?", "SA", clean_name, flags=re.IGNORECASE)
    clean_name = re.sub(r"\bCorporation\b", "Corp", clean_name, flags=re.IGNORECASE)
    clean_name = re.sub(r"\bIncorporated\b", "Inc", clean_name, flags=re.IGNORECASE)
    clean_name = re.sub(r"\bS&P\b", "SP", clean_name, flags=re.IGNORECASE)
    clean_name = clean_name.replace("&", " and ")
    clean_name = clean_name.replace("%", " ")

    # Normalize unicode accents
    clean_name = clean_name.replace("ł", "l").replace("Ł", "L")
    clean_name = unicodedata.normalize("NFKD", clean_name).encode("ascii", "ignore").decode("ascii")

    # Remove non-alphanumeric
    clean_name = re.sub(r"[^a-zA-Z0-9\s]", " ", clean_name)

    # Account suffix handling (e.g. _IKE, _IKZE) to avoid filename collisions across accounts/brokers
    account_suffix = ""
    if tick_str.upper().endswith("_IKZE"):
        account_suffix = "_ikze"
    elif tick_str.upper().endswith("_IKE"):
        account_suffix = "_ike"

    # Convert to lowercase snake_case
    slug = "_".join(clean_name.lower().split())
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
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        text = raw_bytes.decode("utf-8-sig")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
        return text

    # Try strict UTF-8
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        pass

    # Try legacy Polish / European encodings
    detected_encoding = None
    decoded_text: str | None = None
    for enc in ["cp1250", "windows-1250", "iso-8859-2", "latin2", "cp1252", "latin1"]:
        try:
            decoded_text = raw_bytes.decode(enc)
            detected_encoding = enc
            break
        except Exception:
            continue

    if decoded_text is None:
        raise ValueError(f"Could not decode {file_path} with supported encodings.")

    # Convert and fix file on disk in-place as UTF-8
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(decoded_text)

    print(
        f"Detected {detected_encoding} encoding for {os.path.basename(file_path)} — converted and saved in-place as UTF-8."
    )
    return decoded_text


def determine_asset_type(name: str) -> str:
    """Determine asset type ('equity', 'etf', 'cash') based on asset name keywords."""
    name_upper = name.upper()
    if "CASH" in name_upper:
        return "cash"
    etf_keywords = ["ETF", "UCITS", "VANGUARD", "VANECK", "ISHARES", "VNGRD", "INDEX", "SCTR"]
    if any(kw in name_upper for kw in etf_keywords):
        return "etf"
    return "equity"


DEFAULT_ISSUER_DISCOVERY_MAPPING: dict[str, str] = {
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

_issuer_mapping_cache: dict[str, str] | None = None


def load_issuer_discovery_mapping(base_dir: str | None = None) -> dict[str, str]:
    """Load etf.issuer.discovery_mapping from config.yaml with built-in fallbacks."""
    vault_cfg = load_vault_config(base_dir=base_dir)
    mapping = vault_cfg.etf.issuer.discovery_mapping
    return {str(k).lower(): str(v) for k, v in mapping.items()}


def load_import_config(base_dir: str | None = None) -> dict[str, Any]:
    """Load broker import configuration from config.yaml (e.g. default_mode: 'api' or 'csv')."""
    vault_cfg = load_vault_config(base_dir=base_dir)
    return {k: v.model_dump() for k, v in vault_cfg.import_config.items()}


def determine_issuer(name: str, mapping: dict[str, str] | None = None) -> str | None:
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


def determine_portfolio(name: str, asset_type: str, dominant_sector: str | None = None) -> str | None:
    """Determine sub-portfolio ('Safety net', 'Long term', 'Aggressive') based on asset attributes."""
    if asset_type == "cash":
        return None  # Uninvested broker cash is unallocated dry powder (portfolio: null)
    if asset_type == "equity":
        return "Aggressive"
    if asset_type == "etf":
        sec = (dominant_sector or "").lower()
        name_lower = name.lower()
        if (
            "bond" in name_lower
            or "treasury" in name_lower
            or sec in ["sovereign", "bonds", "real estate", "diversified"]
        ):
            return "Long term"
        return "Aggressive"
    return "Long term"


# Re-export note persistence and platform synchronization functions from platforms.storage
from platforms.storage import (
    remove_missing_platform_assets,
    save_or_update_asset,
    save_or_update_assets_parallel,
)

# Re-export template loading and rendering functions from platforms.template
from platforms.template import (
    load_template,
    render_template_body,
)

__all__ = [
    "clean_asset_display_name",
    "determine_asset_type",
    "determine_portfolio",
    "ensure_utf8_file",
    "get_in",
    "get_max_workers",
    "load_template",
    "parse_number",
    "remove_missing_platform_assets",
    "render_template_body",
    "sanitize_filename",
    "save_or_update_asset",
    "save_or_update_assets_parallel",
    "slugify_asset_name",
]
