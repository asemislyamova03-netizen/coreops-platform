from fastapi import Request


def client_ip(request: Request | None) -> str | None:
    """Return the direct peer IP for rate limiting / audit metadata.

    X-Forwarded-For / Forwarded headers are intentionally ignored.

    There is no trusted-proxy allowlist configured in this codebase yet.
    Until an explicit trusted-proxy mechanism exists, trusting client-supplied
    forwarded headers would allow IP spoofing (e.g. rate-limit bypass).
    Default to ``request.client.host`` only.
    """
    if request is None:
        return None
    if request.client:
        return request.client.host
    return None


def user_agent(request: Request | None) -> str | None:
    if request is None:
        return None
    return request.headers.get("user-agent")
