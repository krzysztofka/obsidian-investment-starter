"""Unit tests for platforms.template module."""

import os

from platforms.template import (
    _inject_issuer_link,
    _inject_justetf_link,
    load_template,
    render_template_body,
)


def test_load_template():
    vault_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
    fm, body = load_template(vault_root)
    assert isinstance(fm, dict)
    assert isinstance(body, str)
    assert len(body) > 0


def test_render_template_body():
    template = "# Dummy Title\n\n**Platform:** [[Placeholder]]\n"
    rendered = render_template_body(template, name="Apple Inc.", ticker="AAPL", platform="Degiro")
    assert "# Apple Inc. (AAPL)" in rendered
    assert "**Platform:** [[Degiro]]" in rendered


def test_inject_justetf_link():
    body = "**Platform:** [[Degiro]]\n## Notes"
    url = "https://www.justetf.com/en/etf-profile.html?isin=IE00BK5BQT80"
    injected = _inject_justetf_link(body, "Degiro", url)
    assert f"**JustETF Profile:** [{url}]({url})" in injected

    # Already present - do not duplicate
    re_injected = _inject_justetf_link(injected, "Degiro", url)
    assert re_injected == injected


def test_inject_issuer_link():
    body = "**Platform:** [[Degiro]]\n## Notes"
    url = "https://www.vanguard.com"
    injected = _inject_issuer_link(body, "Degiro", url)
    assert f"**Issuer Profile:** [{url}]({url})" in injected
