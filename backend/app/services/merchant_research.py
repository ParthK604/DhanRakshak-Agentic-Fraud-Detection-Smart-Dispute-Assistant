from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from app.config import get_settings
from app.models.merchant import MerchantSignal, ResearchFinding
from app.services.safe_fetch import fetch

SUSPICIOUS_TOKENS = (
    "prize", "outlet", "urgent", "reward", "crypto", "guaranteed",
    "gift card", "ignore previous instructions", "verification required",
)
KNOWN_BRANDS = ("paypal", "amazon", "google", "microsoft", "apple", "netflix", "spotify")


def lookalike_signal(name: str) -> MerchantSignal:
    normalized = re.sub(r"[^a-z0-9]", "", name.casefold())
    folded = normalized.translate(str.maketrans({"0": "o", "1": "l"}))
    for brand in KNOWN_BRANDS:
        suffix_match = folded.startswith(brand) and folded[len(brand):] in {"support", "billing", "verify"}
        distance = _edit_distance(folded, brand)
        if (distance <= 1 and folded != brand) or suffix_match:
            return MerchantSignal(name="lookalike", source="name", triggered=True, direction="negative", impact=-1, weight=35, value=brand, evidence=f"Merchant name resembles known brand {brand}.", available=True)
    return MerchantSignal(name="lookalike", source="name", triggered=False, direction="neutral", impact=0, weight=35, value=None, evidence="No close known-brand lookalike detected.", available=True)


def _edit_distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, 1):
        current = [i]
        for j, right_char in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (left_char != right_char)))
        previous = current
    return previous[-1]


def _fixture_data(name: str) -> dict[str, object] | None:
    path = Path(__file__).parents[1] / "fixtures" / "merchants.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get(name)


async def research_merchant(name: str, url: str | None = None) -> tuple[list[MerchantSignal], list[ResearchFinding], list[str], str | None]:
    settings = get_settings()
    key = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
    data = _fixture_data(key) if settings.merchant_research_mode == "fixture" else None
    signals: list[MerchantSignal] = [lookalike_signal(name)]
    findings: list[ResearchFinding] = []
    sources: list[str] = []
    page_text = ""
    if data is not None:
        resolved = data.get("domain_resolves")
        age = data.get("domain_age_days")
        https = data.get("https_https")
        page_text = str(data.get("page_text") or "")
        findings.append(ResearchFinding(type="fixture", summary=str(data.get("summary")), source_url=data.get("url"), retrieved_at=datetime.now(UTC)))
        signals.extend([
            MerchantSignal(name="domain_resolves", source="domain", triggered=resolved is not None, direction="positive" if resolved is True else "negative", impact=0.6 if resolved is True else -1, weight=25, value=resolved, evidence="Fixture domain resolution result.", available=resolved is not None),
            MerchantSignal(name="https", source="domain", triggered=https is not None, direction="positive" if https is True else "negative", impact=0.4 if https is True else -0.7, weight=15, value=https, evidence="Fixture HTTPS result.", available=https is not None),
            MerchantSignal(name="domain_age", source="domain", triggered=isinstance(age, int), direction="positive" if isinstance(age, int) and age >= 90 else "negative", impact=0.7 if isinstance(age, int) and age >= 90 else -0.8, weight=20, value=age, evidence=f"Domain age fixture: {age} days.", available=age is not None),
        ])
        sources.append("fixture")
    elif url:
        result = await fetch(url)
        signals.append(MerchantSignal(name="domain_fetch", source="domain", triggered=result.available, direction="positive" if result.available else "negative", impact=0.5 if result.available else -1, weight=25, value=result.status, evidence=result.error or f"Fetched {result.final_url}.", available=result.status is not None))
        page_text = result.text
        if result.available:
            findings.append(ResearchFinding(type="page", summary="Fetched merchant page for keyword analysis.", source_url=result.final_url, retrieved_at=datetime.now(UTC)))
            sources.append("safe_fetch")
    else:
        signals.append(MerchantSignal(name="domain", source="domain", triggered=False, direction="neutral", impact=0, weight=20, evidence="No merchant URL was supplied.", available=False))
    text_lower = page_text.casefold()
    suspicious = [token for token in SUSPICIOUS_TOKENS if token in text_lower or token in name.casefold()]
    signals.append(MerchantSignal(name="scam_language", source="web", triggered=bool(suspicious), direction="negative" if suspicious else "neutral", impact=-1 if suspicious else 0, weight=30, value=", ".join(suspicious), evidence=f"Suspicious terms found: {', '.join(suspicious)}." if suspicious else "No configured scam terms found.", available=bool(page_text)))
    for keyword in ("contact", "refund", "return", "terms", "privacy"):
        if keyword in text_lower:
            signals.append(MerchantSignal(name=f"site_{keyword}", source="web", triggered=True, direction="positive", impact=0.2, weight=4, value=True, evidence=f"Page contains {keyword} information.", available=True))
    return signals, findings, sources, page_text[:6000] if page_text else None
