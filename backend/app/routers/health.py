import asyncio

from fastapi import APIRouter

from app import db
from app.config import get_settings
from app.services import llm
from app.services.paypal_client import paypal

router = APIRouter(prefix="/api", tags=["health"])


async def _check(name: str, coro) -> tuple[str, dict]:
    try:
        detail = await asyncio.wait_for(coro, timeout=20)
        return name, {"ok": True, "detail": detail if isinstance(detail, str) else None}
    except Exception as e:  # report error type + message only, never secrets
        return name, {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


@router.get("/health")
async def health():
    results = dict(
        await asyncio.gather(
            _check("paypal", paypal.ping()),
            _check("mongodb", db.ping()),
            _check("groq", llm.ping()),
        )
    )
    return {
        "status": "ok" if all(r["ok"] for r in results.values()) else "degraded",
        "groq_model": get_settings().groq_model,
        "services": results,
    }