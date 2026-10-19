from datetime import UTC, datetime, timedelta

from app.models.schemas import Transaction
from app.services.features import combine_rules_score, compute_signals


def txn(txn_id: str, when: datetime, amount: float = 10, merchant: str = "Shop", country: str = "US") -> Transaction:
    return Transaction(
        txn_id=txn_id, user_id="u1", amount=amount, currency="USD",
        merchant_name=merchant, direction="outgoing", country=country,
        timestamp=when, status="COMPLETED", source="seeded",
    )


def test_signals_use_only_prior_history() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    prior = [txn(f"old-{i}", now - timedelta(days=i + 1), 10, "Shop") for i in range(4)]
    future = [txn("future", now + timedelta(days=1), 10000, "Shop")]
    signals = compute_signals(txn("target", now, 40, "Shop"), prior + future)
    signals = compute_signals(txn("target", now, 25, "Shop"), prior + future)
    assert not next(signal for signal in signals if signal.name == "unusual_amount").triggered


def test_unusual_amount_and_new_payee() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    history = [txn(f"old-{i}", now - timedelta(days=i + 1), 20, "Known") for i in range(4)]
    signals = compute_signals(txn("target", now, 200, "New"), history)
    assert next(signal for signal in signals if signal.name == "unusual_amount").triggered
    assert next(signal for signal in signals if signal.name == "new_payee_large").triggered


def test_geo_velocity_and_duplicate() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    history = [txn(f"old-{i}", now - timedelta(seconds=30 * (i + 1)), 10, f"Shop-{i}", "US") for i in range(9)]
    history.append(txn("same", now - timedelta(minutes=3), 10, "Target", "US"))
    signals = compute_signals(txn("target", now, 10, "Target", "SG"), history)
    names = {signal.name for signal in signals if signal.triggered}
    assert {"geo_anomaly", "velocity", "possible_duplicate"} <= names


def test_score_targets() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    none = compute_signals(txn("target", now), [])
    strong = compute_signals(txn("target", now, 50, "Known"), [txn(f"old-{i}", now - timedelta(days=i + 1), 10, "Known") for i in range(4)])
    assert combine_rules_score(none) < 20
    assert 35 <= combine_rules_score(strong) < 70
