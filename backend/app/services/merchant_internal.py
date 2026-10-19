from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, datetime
from statistics import mean, pstdev

from app.models.merchant import MerchantSignal
from app.models.schemas import Transaction


def normalize_merchant_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.casefold()).strip()


def merchant_id(name: str) -> str:
    return normalize_merchant_name(name).replace(" ", "-")


def internal_signals(
    merchant_name: str,
    transactions: list[Transaction],
    disputes: list[dict[str, object]] | None = None,
    risk_scores: list[dict[str, object]] | None = None,
) -> list[MerchantSignal]:
    normalized = normalize_merchant_name(merchant_name)
    rows = [row for row in transactions if normalize_merchant_name(row.merchant_name) == normalized]
    if not rows:
        return [MerchantSignal(name="internal_data", source="internal", triggered=False, direction="neutral", impact=0, weight=1, evidence="No internal transactions found.", available=False)]
    now = max(row.timestamp for row in rows)
    days = max(0, (now - min(row.timestamp for row in rows)).days)
    values = [row.amount for row in rows]
    cv = pstdev(values) / mean(values) if len(values) > 1 and mean(values) else 0.0
    dispute_rows = [
        item for item in (disputes or [])
        if item.get("merchant_name") == merchant_name
        or merchant_name in str(item.get("txn_ids", ""))
    ]
    merchant_txn_ids = {row.txn_id for row in rows}
    high_risk = [
        item for item in (risk_scores or [])
        if item.get("risk_level") == "high" and item.get("txn_id") in merchant_txn_ids
    ]
    countries = {row.country for row in rows}
    return [
        MerchantSignal(name="tenure", source="internal", triggered=days >= 180, direction="positive" if days >= 180 else "neutral", impact=1 if days >= 180 else 0, weight=16, value=days, evidence=f"Observed for {days} days.", available=True),
        MerchantSignal(name="volume", source="internal", triggered=len(rows) >= 10 and len({row.user_id for row in rows}) >= 2, direction="positive" if len(rows) >= 10 else "neutral", impact=1 if len(rows) >= 10 else 0, weight=14, value=len(rows), evidence=f"{len(rows)} transactions from {len({row.user_id for row in rows})} users.", available=True),
        MerchantSignal(name="amount_consistency", source="internal", triggered=cv <= 0.5, direction="positive" if cv <= 0.5 else "negative", impact=0.6 if cv <= 0.5 else -0.4, weight=10, value=round(cv, 3), evidence=f"Amount coefficient of variation is {cv:.2f}.", available=True),
        MerchantSignal(name="dispute_rate", source="internal", triggered=bool(dispute_rows), direction="negative" if dispute_rows else "positive", impact=-1 if dispute_rows else 0.4, weight=18, value=len(dispute_rows) / len(rows), evidence=f"{len(dispute_rows)} related dispute records found.", available=True),
        MerchantSignal(name="high_risk_share", source="internal", triggered=bool(risk_scores), direction="negative" if high_risk else "neutral", impact=-1 if high_risk else 0, weight=14, value=len(high_risk) / len(risk_scores) if risk_scores else None, evidence=f"{len(high_risk)} high-risk assessments in supplied records.", available=bool(risk_scores)),
        MerchantSignal(name="country_consistency", source="internal", triggered=len(countries) == 1, direction="positive" if len(countries) == 1 else "negative", impact=0.5 if len(countries) == 1 else -0.5, weight=8, value=len(countries), evidence=f"Transactions span {len(countries)} countries.", available=True),
    ]
