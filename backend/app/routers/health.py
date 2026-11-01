import asyncio
from datetime import UTC, datetime
from time import monotonic

from fastapi import APIRouter

from app import db
from app.config import get_settings
from app.services import llm
from app.services.paypal_client import paypal

router = APIRouter(prefix="/api", tags=["health"])
_cached_results: dict[str, dict] | None = None
_cached_at = 0.0


async def _check(name: str, coro) -> tuple[str, dict]:
    try:
        detail = await asyncio.wait_for(coro, timeout=20)
        return name, {"ok": True, "detail": detail if isinstance(detail, str) else None}
    except Exception as e:  # report error type + message only, never secrets
        return name, {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


@router.get("/health")
async def health():
    global _cached_results, _cached_at
    now = monotonic()
    settings = get_settings()
    if _cached_results is not None and now - _cached_at < settings.health_cache_seconds:
        return _response(_cached_results, cached=True)
    results = dict(
        await asyncio.gather(
            _check("paypal", paypal.ping()),
            _check("mongodb", db.ping()),
            _check("groq", llm.ping()),
        )
    )
    _cached_results = results
    _cached_at = now
    return _response(results, cached=False)


def _response(results: dict[str, dict], *, cached: bool) -> dict:
    return {
        "status": "ok" if all(r["ok"] for r in results.values()) else "degraded",
        "groq_model": get_settings().groq_model,
        "services": results,
        "checked_at": datetime.now(UTC).isoformat(),
        "cached": cached,
    }