from fastapi import HTTPException
from starlette.requests import Request

from app.config import get_settings
from app.services.rate_limit import enforce_rate_limit, reset_rate_limiter


def _request(ip: str = "203.0.113.10", forwarded: str | None = None) -> Request:
    headers = []
    if forwarded:
        headers.append((b"x-forwarded-for", forwarded.encode()))
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/risk/score",
            "headers": headers,
            "client": (ip, 1234),
        }
    )


def test_rate_limit_uses_first_forwarded_ip(monkeypatch) -> None:
    reset_rate_limiter()
    monkeypatch.setattr(get_settings(), "rate_limit_per_minute", 1)
    asyncio.run(enforce_rate_limit(_request(forwarded="198.51.100.4, 10.0.0.1")))
    try:
        asyncio.run(enforce_rate_limit(_request(forwarded="198.51.100.4, 10.0.0.2")))
    except HTTPException as exc:
        assert exc.status_code == 429
        assert "Retry-After" in exc.headers
        assert "limit" in exc.detail
    else:
        raise AssertionError("Expected the second request to be rate limited")
    reset_rate_limiter()
import asyncio
