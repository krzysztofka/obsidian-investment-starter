"""Template loading and note body rendering for platform extensions."""

import os
import re
import sys
from typing import Any

# Ensure scripts root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.dirname(current_dir)
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

from model.asset import Asset


def load_template(base_dir: str) -> tuple[dict[str, Any], str]:
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
    body = re.sub(r"^# .+$", f"# {name} ({ticker})", body, count=1, flags=re.MULTILINE)
    body = re.sub(r"\[\[\w+\]\]", f"[[{platform}]]", body, count=1)
    return body


def _inject_justetf_link(body: str, platform: str, justetf_url: str | None) -> str:
    """Inject JustETF profile link below the platform line if not already present."""
    if not justetf_url or justetf_url in body:
        return body
    platform_pattern = rf"(\*\*Platform:\*\* \[\[{re.escape(platform)}\]\])"
    justetf_line = f"\n**JustETF Profile:** [{justetf_url}]({justetf_url})"
    return re.sub(platform_pattern, r"\1" + justetf_line, body, count=1)


def _inject_issuer_link(body: str, platform: str, issuer_url: str | None) -> str:
    """Inject or update Issuer Profile link below JustETF profile or platform line."""
    if not issuer_url:
        return body
    if "**Issuer Profile:**" in body:
        return re.sub(
            r"\*\*Issuer Profile:\*\* \[.*?\]\(.*?\)",
            f"**Issuer Profile:** [{issuer_url}]({issuer_url})",
            body,
            count=1,
        )
    if "**JustETF Profile:**" in body:
        justetf_pattern = r"(\*\*JustETF Profile:\*\* \[.*?\]\(.*?\))"
        issuer_line = f"\n**Issuer Profile:** [{issuer_url}]({issuer_url})"
        return re.sub(justetf_pattern, r"\1" + issuer_line, body, count=1)
    platform_pattern = rf"(\*\*Platform:\*\* \[\[{re.escape(platform)}\]\])"
    issuer_line = f"\n**Issuer Profile:** [{issuer_url}]({issuer_url})"
    return re.sub(platform_pattern, r"\1" + issuer_line, body, count=1)
