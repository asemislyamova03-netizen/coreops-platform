"""Unit tests for audit request metadata helpers."""

from types import SimpleNamespace

from app.modules.audit.request_meta import client_ip


class _FakeRequest:
    def __init__(self, host: str | None, headers: dict[str, str] | None = None):
        self.client = SimpleNamespace(host=host) if host is not None else None
        self.headers = headers or {}


def test_client_ip_uses_direct_peer_host():
    request = _FakeRequest("203.0.113.10", headers={"x-forwarded-for": "198.51.100.1"})
    assert client_ip(request) == "203.0.113.10"


def test_client_ip_ignores_x_forwarded_for_entirely():
    request = _FakeRequest(
        "127.0.0.1",
        headers={"x-forwarded-for": "198.51.100.1, 203.0.113.5"},
    )
    assert client_ip(request) == "127.0.0.1"


def test_client_ip_ignores_forwarded_header_variants():
    request = _FakeRequest(
        "10.0.0.2",
        headers={
            "x-forwarded-for": "1.2.3.4",
            "forwarded": "for=5.6.7.8",
            "x-real-ip": "9.9.9.9",
        },
    )
    assert client_ip(request) == "10.0.0.2"


def test_client_ip_none_without_client():
    assert client_ip(None) is None
    assert client_ip(_FakeRequest(None)) is None
