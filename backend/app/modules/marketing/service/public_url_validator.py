"""Mode B static public URL validator — no network fetch / DNS / redirects.

Policy:
- HTTPS only, static checks;
- registered_unverified ≠ SSRF-safe / publish-ready;
- valid IDN must already be in ASCII punycode (xn--) form or plain LDH labels;
- encoded path segments do not make a URL trusted (no fetch).
"""

from __future__ import annotations

import hashlib
import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

from app.modules.marketing.enums import DEFAULT_MAX_URL_LENGTH
from app.modules.marketing.exceptions import MarketingPublicUrlValidationError

_LOCALHOST_LABELS = frozenset({"localhost", "localhost."})
_METADATA_IPV4 = ipaddress.ip_address("169.254.169.254")
_METADATA_HOSTS = frozenset(
    {
        "metadata.google.internal",
        "metadata",
        "instance-data",
        "kubernetes.default",
        "kubernetes.default.svc",
    }
)
_FORBIDDEN_SUFFIXES = (".local", ".localhost", ".internal", ".lan")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
# Noncanonical IPv4-like hosts: decimal, octal-ish, hex-ish single labels / dotted octal.
_HEX_IP_HOST = re.compile(r"^0x[0-9a-fA-F]+$")
_DECIMAL_IP_HOST = re.compile(r"^\d{8,10}$")
_OCTAL_DOTTED = re.compile(r"^0[0-7]+(\.0[0-7]+){1,3}$")
_LDH_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)
_PUNYCODE_LABEL = re.compile(r"^xn--[a-z0-9-]+$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class PublicUrlValidationResult:
    normalized_url: str
    host: str
    host_fingerprint: str


def host_fingerprint(host: str) -> str:
    digest = hashlib.sha256(host.strip().lower().encode("utf-8")).hexdigest()
    return digest[:16]


def validate_public_url(
    raw_url: str,
    *,
    max_url_length: int | None = None,
) -> PublicUrlValidationResult:
    """Static HTTPS URL registration rules for M8-C2a Mode B.

    Does NOT claim SSRF-safe. No HEAD/GET/DNS. Query parameters are rejected.
    """
    limit = max_url_length if max_url_length is not None else DEFAULT_MAX_URL_LENGTH
    if limit <= 0:
        raise MarketingPublicUrlValidationError("invalid_max_url_length")

    if raw_url is None:
        raise MarketingPublicUrlValidationError("url_required")
    if not isinstance(raw_url, str):
        raise MarketingPublicUrlValidationError("url_required")

    # Reject before strip so leading/trailing control/null are visible.
    if _CONTROL_RE.search(raw_url):
        raise MarketingPublicUrlValidationError("control_chars_forbidden")
    if "\\" in raw_url:
        raise MarketingPublicUrlValidationError("backslash_forbidden")
    if any(ch.isspace() for ch in raw_url):
        raise MarketingPublicUrlValidationError("url_contains_whitespace")

    url = raw_url.strip()
    if not url:
        raise MarketingPublicUrlValidationError("url_required")
    if len(url) > limit:
        raise MarketingPublicUrlValidationError("url_too_long")
    if "\x00" in url:
        raise MarketingPublicUrlValidationError("null_byte_forbidden")

    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        raise MarketingPublicUrlValidationError("https_required")
    if parsed.username is not None or parsed.password is not None:
        raise MarketingPublicUrlValidationError("userinfo_forbidden")
    if parsed.fragment:
        raise MarketingPublicUrlValidationError("fragment_forbidden")
    if parsed.query:
        raise MarketingPublicUrlValidationError("query_forbidden")
    if not parsed.hostname:
        raise MarketingPublicUrlValidationError("host_required")

    host = parsed.hostname.strip().lower().rstrip(".")
    if not host:
        raise MarketingPublicUrlValidationError("host_required")
    if _CONTROL_RE.search(host):
        raise MarketingPublicUrlValidationError("control_chars_forbidden")

    if host in _LOCALHOST_LABELS or host.endswith(".localhost"):
        raise MarketingPublicUrlValidationError("localhost_forbidden")
    if host in _METADATA_HOSTS or host.endswith(".metadata.google.internal"):
        raise MarketingPublicUrlValidationError("metadata_host_forbidden")
    for suffix in _FORBIDDEN_SUFFIXES:
        if host == suffix[1:] or host.endswith(suffix):
            raise MarketingPublicUrlValidationError("internal_suffix_forbidden")

    if _is_obfuscated_numeric_host(host):
        raise MarketingPublicUrlValidationError("obfuscated_ip_forbidden")

    if _is_ip_literal(host):
        _reject_unsafe_ip(host)
    else:
        _validate_hostname_labels(host)
        if "." not in host:
            raise MarketingPublicUrlValidationError("single_label_host_forbidden")

    path = parsed.path or ""
    # Encoded path is opaque — does not grant trust; still stored as registered_unverified.
    _ = unquote(path)
    normalized = f"https://{host}{path}"
    return PublicUrlValidationResult(
        normalized_url=normalized,
        host=host,
        host_fingerprint=host_fingerprint(host),
    )


def _is_obfuscated_numeric_host(host: str) -> bool:
    if _HEX_IP_HOST.match(host) or _DECIMAL_IP_HOST.match(host) or _OCTAL_DOTTED.match(host):
        return True
    # Dotted forms with leading-zero octal segments like 0177.0.0.1
    if re.fullmatch(r"[0-9.]+", host) and re.search(r"(^|\.)0[0-9]+", host):
        return True
    return False


def _validate_hostname_labels(host: str) -> None:
    labels = host.split(".")
    if any(not label for label in labels):
        raise MarketingPublicUrlValidationError("malformed_hostname")
    for label in labels:
        if label.startswith("xn--"):
            if not _PUNYCODE_LABEL.match(label):
                raise MarketingPublicUrlValidationError("malformed_punycode")
            continue
        # Reject raw non-ASCII IDN (require documented punycode form).
        try:
            label.encode("ascii")
        except UnicodeEncodeError:
            raise MarketingPublicUrlValidationError("idn_must_be_punycode") from None
        if not _LDH_LABEL.match(label):
            raise MarketingPublicUrlValidationError("malformed_hostname")


def _is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _reject_unsafe_ip(host: str) -> None:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        raise MarketingPublicUrlValidationError("invalid_ip_literal") from None

    if ip == _METADATA_IPV4:
        raise MarketingPublicUrlValidationError("metadata_ip_forbidden")
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        raise MarketingPublicUrlValidationError("unsafe_ip_forbidden")
