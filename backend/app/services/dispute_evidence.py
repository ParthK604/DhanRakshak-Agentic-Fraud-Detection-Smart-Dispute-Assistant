from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher

from app.models.dispute import EvidenceItem, EvidencePack, DisputeIntent
from app.models.schemas import Transaction


def resolve_merchant(text: str, merchants: list[str]) -> str | None:
    if not text.strip() or not merchants:
        return None
    lowered = text.casefold().strip()
    exact = next((merchant for merchant in merchants if merchant.casefold() == lowered), None)
    if exact:
        return exact
    ranked = sorted(
        merchants,
        key=lambda merchant: SequenceMatcher(None, lowered, merchant.casefold()).ratio(),
        reverse=True,
    )
    return ranked[0] if SequenceMatcher(None, lowered, ranked[0].casefold()).ratio() >= 0.55 else None


def find_duplicates(
    user_id: str,
    merchant: str,
    transactions: list[Transaction],
    window: timedelta = timedelta(hours=24),
) -> list[tuple[Transaction, Transaction, float]]:
    rows = sorted(
        [row for row in transactions if row.user_id == user_id and row.merchant_name == merchant],
        key=lambda row: row.timestamp,
    )
    matches: list[tuple[Transaction, Transaction, float]] = []
    for first, second in zip(rows, rows[1:]):
        gap = (second.timestamp - first.timestamp).total_seconds()
        if gap <= window.total_seconds() and first.amount == second.amount:
            matches.append((first, second, gap / 60))
    return matches


def _item(txn: Transaction, relevance: str) -> EvidenceItem:
    return EvidenceItem(
        txn_id=txn.txn_id, amount=txn.amount, currency=txn.currency,
        merchant_name=txn.merchant_name, timestamp=txn.timestamp, relevance=relevance,
    )


def _expected_from_description(txn: Transaction) -> float | None:
    match = re.search(r"expected price:\s*([0-9]+(?:\.[0-9]{1,2})?)", txn.description or "", re.I)
    return float(match.group(1)) if match else None


def _cancel_date_from_description(txn: Transaction) -> date | None:
    match = re.search(r"(?:cancel date|cancellation date):\s*(\d{4}-\d{2}-\d{2})", txn.description or "", re.I)
    return date.fromisoformat(match.group(1)) if match else None


def build_evidence_pack(
    txn: Transaction,
    candidates: list[Transaction],
    intent: DisputeIntent,
    *,
    risk_summary: str | None = None,
    expected_amount: float | None = None,
    cancel_date: date | None = None,
) -> EvidencePack:
    prior = [row for row in candidates if row.timestamp < txn.timestamp and row.txn_id != txn.txn_id]
    matched: list[Transaction] = []
    facts: list[str] = []
    timeline: list[str] = []
    merchant_rows = [row for row in prior if row.merchant_name == txn.merchant_name]
    if intent.issue_type == "duplicate_charge":
        duplicates = find_duplicates(txn.user_id, txn.merchant_name, candidates)
        for first, second, _ in duplicates:
            if txn.txn_id in {first.txn_id, second.txn_id}:
                matched.extend([first, second])
                facts.append(f"Matched equal {first.currency} charges of {first.amount:.2f} at the same merchant.")
                facts.append(f"The charges are {abs((second.timestamp - first.timestamp).total_seconds()) / 60:.1f} minutes apart.")
                break
    elif intent.issue_type in {"wrong_amount", "cancelled_subscription", "unauthorized", "not_received"}:
        matched = [txn]
        if intent.issue_type == "wrong_amount":
            expected = expected_amount or _expected_from_description(txn)
            if expected is not None:
                facts.append(f"Expected price is {expected:.2f} {txn.currency}; charged amount is {txn.amount:.2f} {txn.currency}.")
        if intent.issue_type == "cancelled_subscription":
            cancelled = cancel_date or _cancel_date_from_description(txn)
            if cancelled:
                facts.append(f"Charge timestamp is after the stated cancellation date {cancelled.isoformat()}.")
    cadence = "no prior billing pattern"
    if len(merchant_rows) >= 2:
        gaps = [(b.timestamp - a.timestamp).days for a, b in zip(merchant_rows, merchant_rows[1:])]
        cadence = "monthly, one charge per cycle" if 20 <= sum(gaps) / len(gaps) <= 40 else "recurring merchant activity"
    for row in sorted(matched, key=lambda item: item.timestamp):
        timeline.append(f"{row.timestamp.isoformat()}: {row.txn_id}, {row.amount:.2f} {row.currency}")
    return EvidencePack(
        candidate_txns=[_item(row, "candidate") for row in candidates],
        matched_txns=[_item(row, "matched") for row in matched],
        timeline=timeline,
        merchant_billing_pattern=cadence,
        risk_summary=risk_summary,
        facts=facts,
    )
