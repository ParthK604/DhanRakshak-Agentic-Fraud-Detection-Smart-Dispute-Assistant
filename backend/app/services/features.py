from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from statistics import median

from app.models.schemas import RiskSignal, Transaction


@dataclass(frozen=True)
class RiskConfig:
    merchant_history_days: int = 90
    unusual_merchant_ratio: float = 3.0
    unusual_overall_ratio: float = 5.0
    new_payee_ratio: float = 4.0
    new_payee_floor: float = 150.0
    velocity_five_minutes: int = 5
    velocity_one_hour: int = 10
    duplicate_minutes: int = 15


RISK_CONFIG = RiskConfig()


def _prior(txn: Transaction, history: list[Transaction]) -> list[Transaction]:
    return [
        item for item in history
        if item.user_id == txn.user_id and item.timestamp < txn.timestamp and item.txn_id != txn.txn_id
    ]


def _median_amount(rows: list[Transaction]) -> float:
    return float(median([row.amount for row in rows])) if rows else 0.0


def compute_signals(txn: Transaction, history: list[Transaction]) -> list[RiskSignal]:
    prior = _prior(txn, history)
    cutoff = txn.timestamp - timedelta(days=RISK_CONFIG.merchant_history_days)
    recent = [row for row in prior if row.timestamp >= cutoff]
    merchant_rows = [row for row in recent if row.merchant_name == txn.merchant_name]
    user_median = _median_amount(recent)
    merchant_median = _median_amount(merchant_rows)

    if len(merchant_rows) >= 3 and merchant_median:
        ratio = txn.amount / merchant_median
        threshold = RISK_CONFIG.unusual_merchant_ratio
        max_ratio = 8.0
        evidence = f"{txn.amount:.2f} is {ratio:.1f}x the merchant median {merchant_median:.2f}"
    elif user_median:
        ratio = txn.amount / user_median
        threshold = RISK_CONFIG.unusual_overall_ratio
        max_ratio = 10.0
        evidence = f"{txn.amount:.2f} is {ratio:.1f}x the user median {user_median:.2f}"
    else:
        ratio, threshold, max_ratio = 0.0, float("inf"), 1.0
        evidence = "Insufficient prior amount history"
    unusual = ratio >= threshold
    unusual_severity = min(1.0, max(0.0, (ratio - threshold) / max(0.01, max_ratio - threshold)))

    known_payee = any(
        row.merchant_name == txn.merchant_name
        or (txn.payee_email and row.payee_email == txn.payee_email)
        for row in prior
    )
    new_threshold = max(RISK_CONFIG.new_payee_floor, RISK_CONFIG.new_payee_ratio * user_median) if user_median else RISK_CONFIG.new_payee_floor
    new_payee = not known_payee and txn.amount >= new_threshold
    new_ratio = txn.amount / new_threshold if new_threshold else 0.0

    prior_sorted = sorted(prior, key=lambda row: row.timestamp, reverse=True)
    previous = prior_sorted[0] if prior_sorted else None
    gap = txn.timestamp - previous.timestamp if previous else None
    countries = {row.country for row in recent}
    impossible = bool(previous and gap <= timedelta(hours=6) and previous.country != txn.country)
    novel_country = bool(recent and txn.country not in countries)
    geo_severity = 1.0 if impossible else 0.55 if novel_country else 0.0

    five_minute = sum(1 for row in prior if txn.timestamp - timedelta(minutes=5) <= row.timestamp < txn.timestamp) + 1
    one_hour = sum(1 for row in prior if txn.timestamp - timedelta(hours=1) <= row.timestamp < txn.timestamp) + 1
    velocity = five_minute >= RISK_CONFIG.velocity_five_minutes or one_hour >= RISK_CONFIG.velocity_one_hour
    velocity_severity = min(1.0, max(five_minute / 10, one_hour / 20))

    duplicate = any(
        row.merchant_name == txn.merchant_name
        and row.amount == txn.amount
        and abs((txn.timestamp - row.timestamp).total_seconds()) <= RISK_CONFIG.duplicate_minutes * 60
        for row in prior
    )

    return [
        RiskSignal(name="unusual_amount", triggered=unusual, severity=unusual_severity, weight=30, value=round(ratio, 2), evidence=evidence),
        RiskSignal(name="new_payee_large", triggered=new_payee, severity=min(1.0, new_ratio / 3), weight=30, value=round(new_ratio, 2), evidence=f"New merchant/payee; amount {txn.amount:.2f}, threshold {new_threshold:.2f}"),
        RiskSignal(name="geo_anomaly", triggered=impossible or novel_country, severity=geo_severity, weight=30, value=txn.country, evidence="Country changed within six hours" if impossible else "Country not seen in prior 90 days" if novel_country else "No geographic anomaly"),
        RiskSignal(name="velocity", triggered=velocity, severity=velocity_severity, weight=35, value=max(five_minute, one_hour), evidence=f"{five_minute} transactions in five minutes; {one_hour} in one hour"),
        RiskSignal(name="possible_duplicate", triggered=duplicate, severity=0.35 if duplicate else 0, weight=8, value=txn.merchant_name, evidence="Same merchant and amount within 15 minutes" if duplicate else "No recent matching transaction"),
    ]


def combine_rules_score(signals: list[RiskSignal]) -> int:
    strong = [signal for signal in signals if signal.triggered and signal.name != "possible_duplicate"]
    score = 8 + sum(signal.weight * signal.severity for signal in signals if signal.triggered)
    if len(strong) >= 2:
        score = max(score, 70)
    elif len(strong) == 1:
        score = max(score, 35)
    return min(100, round(score))


def risk_level(score: int) -> str:
    return "low" if score < 35 else "medium" if score < 70 else "high"


def build_context(txn: Transaction, history: list[Transaction]) -> dict[str, object]:
    prior = _prior(txn, history)
    cutoff = txn.timestamp - timedelta(days=90)
    recent = [row for row in prior if row.timestamp >= cutoff]
    merchant = [row for row in recent if row.merchant_name == txn.merchant_name]
    previous = max(prior, key=lambda row: row.timestamp, default=None)
    return {
        "user_median": round(_median_amount(recent), 2),
        "merchant_median": round(_median_amount(merchant), 2),
        "merchant_prior_count": len(merchant),
        "countries_seen": sorted({row.country for row in recent}),
        "transactions_last_5_minutes": sum(1 for row in prior if txn.timestamp - timedelta(minutes=5) <= row.timestamp < txn.timestamp) + 1,
        "transactions_last_hour": sum(1 for row in prior if txn.timestamp - timedelta(hours=1) <= row.timestamp < txn.timestamp) + 1,
        "previous_country": previous.country if previous else None,
        "previous_time_gap_minutes": round((txn.timestamp - previous.timestamp).total_seconds() / 60, 1) if previous else None,
    }
