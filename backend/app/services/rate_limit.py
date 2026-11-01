from collections import defaultdict, deque
from time import monotonic

from fastapi import HTTPException, Request

from app.config import get_settings

_WINDOW_SECONDS = 60.0
_requests: dict[str, deque[float]] = defaultdict(deque)


def _client_key(request: Request) -> str:
    # Render terminates TLS and forwards the original client as the first hop.
    forwarded = request.headers.get("x-forwarded-for")
    return forwarded.split(",", 1)[0].strip() if forwarded else (request.client.host if request.client else "unknown")


async def enforce_rate_limit(request: Request) -> None:
    now = monotonic()
    window = _requests[_client_key(request)]
    while window and now - window[0] >= _WINDOW_SECONDS:
        window.popleft()
    limit = max(1, get_settings().rate_limit_per_minute)
    if len(window) >= limit:
        retry_after = max(1, int(_WINDOW_SECONDS - (now - window[0])) + 1)
        raise HTTPException(
            status_code=429,
            detail="AI request limit reached. Please wait a moment and try again.",
            headers={"Retry-After": str(retry_after)},
        )
    window.append(now)


def reset_rate_limiter() -> None:
    _requests.clear()
