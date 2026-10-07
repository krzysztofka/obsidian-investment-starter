import glob
import os
import re
import sys
from typing import Any

import yaml
from bs4 import BeautifulSoup, Tag

# Ensure integrations root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
integrations_dir = os.path.dirname(current_dir)
if integrations_dir not in sys.path:
    sys.path.append(integrations_dir)

from resilience import resilient_get

DELISTING_RISK_MIN_AUM_MILLION = 50.0
ALERT_DELISTING_RISK_TAG = "#alert/delisting_risk"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def load_delisting_risk_threshold(config_path: str | None = None) -> float:
    """Load minimum AUM threshold (in millions) for delisting risk from config.yaml."""
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, encoding="utf-8") as f:
                content = f.read()
            loaded = yaml.safe_load(content) if yaml else None
            if isinstance(loaded, dict):
                dr = loaded.get("alerts", {}).get("delisting_risk", {})
                if isinstance(dr, dict) and "min_aum_million" in dr:
                    return float(dr["min_aum_million"])
        except Exception:
            pass

    current_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_root = os.path.abspath(os.path.join(current_dir, "../../../.."))
    try:
        from model.config import load_vault_config

        cfg = load_vault_config(base_dir=workspace_root)
        return float(cfg.alerts.delisting_risk.min_aum_million)
    except Exception:
        pass

    return DELISTING_RISK_MIN_AUM_MILLION


def parse_fund_size_in_millions(fund_size: str | int | float | None) -> float | None:
    """Parse fund size / AUM string into float representing fund size in millions."""
    if fund_size is None:
        return None
    if isinstance(fund_size, (int, float)):
        return float(fund_size)
    fs_str = str(fund_size).strip()
    if not fs_str:
        return None

    # Billion match (e.g. 1.5b, 1.5bn, 1.5 billion, 1,5b)
    b_match = re.search(r"([\d\.,]+)\s*(?:bn|b|billion)\b", fs_str, re.IGNORECASE)
    if b_match:
        val_str = b_match.group(1).replace(",", ".")
        if val_str.count(".") > 1:
            val_str = val_str.replace(".", "")
        try:
            return float(val_str) * 1000.0
        except ValueError:
            pass

    # Million match (e.g. 7,046m, 959m, 45m, 45.5m, 45,5m, 45 million, 45 mln)
    m_match = re.search(r"([\d\.,]+)\s*(?:m|mn|million|mln)\b", fs_str, re.IGNORECASE)
    if m_match:
        val_str = m_match.group(1).strip()
        if "," in val_str and "." in val_str:
            if val_str.find(",") < val_str.find("."):
                val_str = val_str.replace(",", "")
            else:
                val_str = val_str.replace(".", "").replace(",", ".")
        elif "," in val_str:
            parts = val_str.split(",")
            if len(parts) == 2 and len(parts[1]) == 3:
                val_str = val_str.replace(",", "")
            else:
                val_str = val_str.replace(",", ".")
        try:
            return float(val_str)
        except ValueError:
            pass

    # Thousand match (e.g. 500k, 500 thousand)
    k_match = re.search(r"([\d\.,]+)\s*(?:k|thousand)\b", fs_str, re.IGNORECASE)
    if k_match:
        val_str = k_match.group(1).strip().replace(",", ".")
        try:
            return float(val_str) / 1000.0
        except ValueError:
            pass

    # Raw digits or numbers
    clean_num = re.search(r"([\d\.,]+)", fs_str)
    if clean_num:
        val_str = clean_num.group(1).replace(",", ".")
        try:
            val = float(val_str)
            if val > 1_000_000:
                return val / 1_000_000.0
            return val
        except ValueError:
            pass
    return None


def check_delisting_risk(fund_size: str | int | float | None, threshold_m: float | None = None) -> bool:
    """Check if fund size (AUM) is below the minimum threshold (default: loaded from config.yaml or 50.0M)."""
    if threshold_m is None:
        threshold_m = load_delisting_risk_threshold()
    parsed_aum = parse_fund_size_in_millions(fund_size)
    if parsed_aum is None:
        return False
    return parsed_aum < threshold_m


def apply_delisting_risk_tag(
    tags: list[str] | str | None, fund_size: str | int | float | None, threshold_m: float | None = None
) -> list[str]:
    """Add or remove '#alert/delisting_risk' from a list of tags based on ETF AUM / fund size."""
    if tags is None:
        result_tags = []
    elif isinstance(tags, (list, tuple)):
        result_tags = [str(t).strip() for t in tags if str(t).strip()]
    elif isinstance(tags, str):
        result_tags = [tags.strip()] if tags.strip() else []
    else:
        result_tags = []

    if check_delisting_risk(fund_size, threshold_m):
        if ALERT_DELISTING_RISK_TAG not in result_tags:
            result_tags.append(ALERT_DELISTING_RISK_TAG)
    else:
        if ALERT_DELISTING_RISK_TAG in result_tags:
            result_tags.remove(ALERT_DELISTING_RISK_TAG)

    return result_tags


def fetch_justetf_data(isin: str) -> dict[str, Any] | None:
    """Fetch ETF metadata (TER, Fund Size, Distribution, Replication, Domicile) from JustETF."""
    if not isin or not re.match(r"^[A-Z]{2}[A-Z0-9]{9}\d$", isin):
        return None
    url = f"https://www.justetf.com/en/etf-profile.html?isin={isin}"
    try:
        resp = resilient_get(url, headers=HEADERS, timeout=8)
        if resp.status_code != 200:
            return None
        html = resp.text
    except Exception:
        return None

    soup = BeautifulSoup(html, "html.parser")
    clean_text = soup.get_text("\n", strip=True)

    data: dict[str, Any] = {"justetf_url": url}

    # Total expense ratio (TER)
    ter_match = re.search(
        r"total expense ratio \(TER\)[^.]*?amounts to\s*([\d\.,]+%\s*p\.a\.)", clean_text, re.IGNORECASE
    )
    if not ter_match:
        ter_match = re.search(r"Total expense ratio\s*\n\s*([\d\.,]+%\s*p\.a\.)", clean_text, re.IGNORECASE)
    if not ter_match:
        ter_match = re.search(
            r"TER\s*\n\s*\([^)]*\)\s*amounts to\s*\n\s*([\d\.,]+%\s*p\.a\.)", clean_text, re.IGNORECASE
        )
    if ter_match:
        data["ter"] = ter_match.group(1).strip()

    # Fund size
    fs_match = re.search(r"fund size of [^.]+? is\s+([^.]+?)\.", clean_text, re.IGNORECASE)
    if not fs_match:
        fs_match = re.search(r"Fund size\s*\n\s*([^\n]+(?:\n[^\n]+)?)\s*\n\s*Inception", clean_text, re.IGNORECASE)
    if fs_match:
        raw_fs = fs_match.group(1).replace("\n", " ").strip().rstrip(".")
        data["fund_size"] = raw_fs
        if check_delisting_risk(raw_fs):
            tags = data.setdefault("tags", [])
            if ALERT_DELISTING_RISK_TAG not in tags:
                tags.append(ALERT_DELISTING_RISK_TAG)

    # Distribution policy
    dist_match = re.search(r"Distribution policy\s*\n\s*(Accumulating|Distributing)", clean_text, re.IGNORECASE)
    if not dist_match:
        lowered = clean_text.lower()
        if "accumulating etf" in lowered:
            data["distribution_policy"] = "Accumulating"
        elif "distributing etf" in lowered or "paying dividends" in lowered:
            data["distribution_policy"] = "Distributing"
    else:
        data["distribution_policy"] = dist_match.group(1).strip()

    # Replication
    repl_match = re.search(r"Replication\s*\n\s*([^\n]+(?:\n\([^)]*\))?)", clean_text, re.IGNORECASE)
    if repl_match:
        raw_repl = repl_match.group(1).replace("\n", " ").strip()
        data["replication"] = raw_repl

    # Domicile
    dom_match = re.search(r"Fund domicile\s*\n\s*([^\n]+)", clean_text, re.IGNORECASE)
    if dom_match:
        data["fund_domicile"] = dom_match.group(1).strip()

    # Official ETF Provider / Issuer Profile Link (e.g. Vanguard, iShares direct link from JustETF)
    for a in soup.find_all("a", href=True):
        if a.get_text(strip=True).lower() == "etf profile":
            href = str(a["href"])
            # Clean marketing campaign tracking parameters
            clean_url = re.sub(r"[\?&]cmpgn=[^&]+", "", href)
            clean_url = re.sub(r"[\?&]cid=[^&]+", "", clean_url)
            clean_url = re.sub(r"[\?&]siteEntryPassthrough=[^&]+", "", clean_url)
            clean_url = clean_url.rstrip("?&")
            data["issuer_url"] = clean_url
            break

    return data if len(data) > 1 else None


def fetch_justetf_sectors(isin: str) -> dict[str, float]:
    """Fetch sector allocation structure (percentages) for an ETF from JustETF using ISIN."""
    if not isin or not re.match(r"^[A-Z]{2}[A-Z0-9]{9}\d$", isin):
        return {}
    url = f"https://www.justetf.com/en/etf-profile.html?isin={isin}"
    try:
        resp = resilient_get(url, headers=HEADERS, timeout=8)
        if resp.status_code != 200:
            return {}
        html = resp.text
    except Exception:
        return {}

    soup = BeautifulSoup(html, "html.parser")
    sectors: dict[str, float] = {}

    name_nodes = soup.find_all(None, attrs={"data-testid": "tl_etf-holdings_sectors_value_name"})
    for node in name_nodes:
        name = node.get_text(strip=True)
        parent = node.find_parent("tr") or node.find_parent("div")
        if isinstance(parent, Tag):
            pct_node = parent.find(None, attrs={"data-testid": "tl_etf-holdings_sectors_value_percentage"})
            if pct_node:
                try:
                    pct_str = pct_node.get_text(strip=True).replace(",", ".").replace("%", "").strip()
                    sectors[name] = float(pct_str)
                except ValueError:
                    pass

    if sectors:
        return sectors

    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) >= 2:
            text0 = tds[0].get_text(strip=True)
            text1 = tds[1].get_text(strip=True)
            if "%" in text1 and re.match(r"^[A-Za-z\s\-&]+$", text0):
                try:
                    pct_val = float(text1.replace(",", ".").replace("%", "").strip())
                    sectors[text0] = pct_val
                except ValueError:
                    pass

    return sectors


def fetch_justetf_top_holdings(isin: str, limit: int = 10) -> list[dict[str, Any]]:
    """Fetch top holdings list (company name, weight percentage) for an ETF from JustETF using ISIN."""
    if not isin or not re.match(r"^[A-Z]{2}[A-Z0-9]{9}\d$", isin):
        return []
    url = f"https://www.justetf.com/en/etf-profile.html?isin={isin}"
    try:
        resp = resilient_get(url, headers=HEADERS, timeout=8)
        if resp.status_code != 200:
            return []
        html = resp.text
    except Exception:
        return []

    soup = BeautifulSoup(html, "html.parser")
    holdings: list[dict[str, Any]] = []

    container = soup.find(None, attrs={"data-testid": "etf-holdings_top-holdings_container"})
    if container:
        for tr in container.find_all("tr"):
            cols = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if len(cols) >= 2:
                name = cols[0].strip()
                pct_str = cols[1].replace(",", ".").replace("%", "").strip()
                try:
                    pct_val = float(pct_str)
                    if name and pct_val > 0:
                        holdings.append({"name": name, "weight_pct": pct_val, "ticker": None})
                except ValueError:
                    pass
            if len(holdings) >= limit:
                break

    return holdings


def update_delisting_risk_alerts(assets_dir: str | None = None) -> int:
    """Scan all asset files in 10_Finance/Assets and update #alert/delisting_risk tags based on fund_size (AUM)."""
    if assets_dir is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        assets_dir = os.path.abspath(os.path.join(current_dir, "../../../../10_Finance/Assets"))

    if not os.path.exists(assets_dir):
        sys.stderr.write(f"Assets directory not found: {assets_dir}\n")
        return 0

    scripts_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if scripts_dir not in sys.path:
        sys.path.append(scripts_dir)

    from model.asset import Asset

    threshold_m = load_delisting_risk_threshold()
    md_files = glob.glob(os.path.join(assets_dir, "*.md"))
    updated_count = 0

    for file_path in md_files:
        asset = Asset.from_file(file_path)
        new_tags = apply_delisting_risk_tag(asset.tags, asset.fund_size, threshold_m=threshold_m)
        if new_tags != asset.tags:
            asset.tags = new_tags
            asset.save(file_path)
            updated_count += 1
            print(f"Updated delisting risk alert for {os.path.basename(file_path)}: tags={asset.tags}")

    return updated_count
