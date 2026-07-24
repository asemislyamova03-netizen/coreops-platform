"""Static contract tests for Landing KZ Social-S0 demo form and login hosts."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

LANDING_WWW = Path(__file__).resolve().parents[1] / "www"
DEMO_INDEX = LANDING_WWW / "demo" / "index.html"

EXPECTED_PUBLIC_LEADS = "https://app.flexity.kz/api/v1/public/leads"
EXPECTED_LOGIN = "https://app.flexity.kz/console/login"
OLD_PUBLIC_LEADS = "https://flexity.asia/api/v1/public/leads"
OLD_LOGIN = "https://flexity.asia/console/login"

# Align with backend PublicLeadCreate (backend/app/modules/public_leads/schemas.py)
EXPECTED_MAXLENGTH = {
    "name": "120",
    "phone": "40",
    "email": "320",
    "company": "160",
    "process_area": "120",
    "message": "2000",
    "website": "200",
}


def _html_files() -> list[Path]:
    return sorted(LANDING_WWW.rglob("*.html"))


def _attr(html: str, element_id: str, attr: str) -> str | None:
    pattern = rf'id=["\']{re.escape(element_id)}["\'][^>]*>'
    # Prefer matching the opening tag that contains id=...
    tag_pat = re.compile(
        rf"<([a-zA-Z0-9]+)([^>]*\bid=[\"']{re.escape(element_id)}[\"'][^>]*)>",
        re.DOTALL,
    )
    match = tag_pat.search(html)
    if not match:
        return None
    attrs = match.group(2)
    attr_match = re.search(rf'\b{re.escape(attr)}=["\']([^"\']*)["\']', attrs)
    return attr_match.group(1) if attr_match else None


def _form_attr(html: str, attr: str) -> str | None:
    match = re.search(
        r'<form\b[^>]*\bid=["\']inboundLeadForm["\'][^>]*>',
        html,
        re.DOTALL | re.IGNORECASE,
    )
    if not match:
        # multiline form open with attrs on following lines before >
        match = re.search(
            r'<form\b([^>]*\bid=["\']inboundLeadForm["\'][^>]*)>',
            html,
            re.DOTALL | re.IGNORECASE,
        )
    if not match:
        return None
    block = match.group(0)
    attr_match = re.search(rf'\b{re.escape(attr)}=["\']([^"\']*)["\']', block)
    return attr_match.group(1) if attr_match else None


@pytest.fixture(scope="module")
def demo_html() -> str:
    assert DEMO_INDEX.is_file(), f"missing {DEMO_INDEX}"
    return DEMO_INDEX.read_text(encoding="utf-8")


def test_public_leads_endpoint_centralized(demo_html: str) -> None:
    endpoint = _form_attr(demo_html, "data-public-leads-endpoint")
    assert endpoint == EXPECTED_PUBLIC_LEADS
    assert "data-public-leads-endpoint=" in demo_html
    assert "PUBLIC_LEADS_ENDPOINT" in demo_html
    assert "getAttribute('data-public-leads-endpoint')" in demo_html
    # Single source of truth: endpoint string appears once (data attribute), not in JS literal.
    assert demo_html.count(EXPECTED_PUBLIC_LEADS) == 1
    assert "var SUBMIT_URL" not in demo_html
    assert "var PUBLIC_LEADS_ENDPOINT = 'http" not in demo_html


def test_no_old_public_leads_endpoint() -> None:
    offenders = []
    for path in _html_files():
        text = path.read_text(encoding="utf-8")
        if OLD_PUBLIC_LEADS in text:
            offenders.append(path.as_posix())
    assert offenders == [], f"old public-leads endpoint still present: {offenders}"


def test_login_host_is_app_flexity_kz() -> None:
    missing_new = []
    still_old = []
    for path in _html_files():
        text = path.read_text(encoding="utf-8")
        if OLD_LOGIN in text:
            still_old.append(path.as_posix())
        # Pages that previously had login CTA should now use KZ app host.
        if "Войти в систему" in text and EXPECTED_LOGIN not in text:
            missing_new.append(path.as_posix())
    assert still_old == [], f"old login host remains: {still_old}"
    assert missing_new == [], f"login CTA without KZ host: {missing_new}"


def test_consent_required(demo_html: str) -> None:
    assert 'id="consent"' in demo_html
    assert re.search(
        r'<input[^>]*\bid=["\']consent["\'][^>]*\brequired\b',
        demo_html,
        re.DOTALL,
    ) or re.search(
        r'<input[^>]*\brequired\b[^>]*\bid=["\']consent["\']',
        demo_html,
        re.DOTALL,
    )
    assert "consent_accepted" in demo_html
    assert "consent.checked" in demo_html


def test_honeypot_website(demo_html: str) -> None:
    assert 'id="website"' in demo_html
    assert "demo-honeypot" in demo_html
    assert "aria-hidden=\"true\"" in demo_html or "aria-hidden='true'" in demo_html
    assert "honeypotOk" in demo_html
    assert "website:" in demo_html


def test_utm_propagation(demo_html: str) -> None:
    for field in (
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "utm_term",
    ):
        assert f"utm.{field}" in demo_html or f"'{field}'" in demo_html
        assert f"{field}:" in demo_html
    assert "readUtmParams" in demo_html
    assert "URLSearchParams" in demo_html
    assert "source_page: window.location.href" in demo_html
    assert "referrer: document.referrer" in demo_html


def test_accessible_success_error_states(demo_html: str) -> None:
    assert 'id="formSuccess"' in demo_html
    assert 'role="status"' in demo_html
    assert 'id="formError"' in demo_html
    assert 'role="alert"' in demo_html


def test_html_maxlength_matches_backend_schema(demo_html: str) -> None:
    for field_id, expected in EXPECTED_MAXLENGTH.items():
        actual = _attr(demo_html, field_id, "maxlength")
        assert actual == expected, f"{field_id}: expected maxlength={expected}, got {actual}"


def test_static_site_link_scan_no_asia_api_or_login() -> None:
    """Scan landing/www for forbidden absolute asia product endpoints."""
    forbidden = (
        OLD_PUBLIC_LEADS,
        OLD_LOGIN,
        "https://flexity.asia/api/v1/public/leads",
        "http://flexity.asia/api/v1/public/leads",
    )
    hits: list[str] = []
    for path in _html_files():
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            if needle in text:
                hits.append(f"{path.as_posix()}: {needle}")
    assert hits == []
