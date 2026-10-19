from datetime import UTC, datetime, timedelta

from app.models.dispute import DisputeIntent
from app.models.schemas import Transaction
from app.services.dispute_evidence import build_evidence_pack, find_duplicates, resolve_merchant
from app.services.letter import template_letter, verify_letter_grounding
from app.services.refunds import calculate_refund


def transaction(txn_id: str, when: datetime, amount: float, merchant: str = "Netflix") -> Transaction:
    return Transaction(
        txn_id=txn_id, user_id="u1", amount=amount, currency="USD",
        merchant_name=merchant, direction="outgoing", country="US",
        timestamp=when, status="COMPLETED", source="seeded",
    )


def test_duplicate_edges_and_no_lookahead() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    first = transaction("txn-1", now, 15.49)
    second = transaction("txn-2", now + timedelta(hours=24), 15.49)
    future = transaction("txn-future", now + timedelta(hours=25), 15.49)
    assert find_duplicates("u1", "Netflix", [first, second], timedelta(hours=24))
    assert not find_duplicates("u1", "Netflix", [first, future], timedelta(hours=24))
    assert not find_duplicates("u1", "Netflix", [first, transaction("txn-3", now + timedelta(minutes=1), 20)])


def test_fuzzy_merchant_and_refunds() -> None:
    assert resolve_merchant("netflx", ["Netflix", "Spotify"]) == "Netflix"
    now = datetime(2026, 1, 1, tzinfo=UTC)
    rows = [transaction("txn-1", now, 15.49), transaction("txn-2", now + timedelta(minutes=3), 15.49)]
    evidence = build_evidence_pack(rows[1], rows, DisputeIntent(issue_type="duplicate_charge", merchant_text="Netflix", confidence=1))
    refund = calculate_refund("duplicate_charge", evidence)
    assert refund.amount == 15.49
    assert refund.currency == "USD"


def test_refund_math_for_wrong_amount_and_full_charge() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    row = transaction("txn-1", now, 19.99)
    evidence = build_evidence_pack(
        row, [row], DisputeIntent(issue_type="wrong_amount", merchant_text="Netflix", confidence=1),
        expected_amount=9.99,
    )
    assert calculate_refund("wrong_amount", evidence, {"expected_amount": 9.99}).amount == 10
    assert calculate_refund("unauthorized", evidence).amount == 19.99


def test_letter_grounding_rejects_invented_amount_or_id() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    row = transaction("txn-1", now, 19.99)
    evidence = build_evidence_pack(row, [row], DisputeIntent(issue_type="unauthorized", merchant_text="Netflix", confidence=1))
    letter = template_letter("unauthorized", evidence, calculate_refund("unauthorized", evidence))
    assert verify_letter_grounding(letter, evidence)
    letter.body += " Extra invented transaction txn-999 for 999.00 USD."
    assert not verify_letter_grounding(letter, evidence)
