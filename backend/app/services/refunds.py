from app.models.dispute import EvidencePack, RefundCalculation
from app.models.schemas import Transaction


DISCLAIMER = "Estimate; the final decision rests with PayPal and the merchant."


def calculate_refund(
    issue_type: str,
    evidence: EvidencePack,
    user_inputs: dict[str, object] | None = None,
) -> RefundCalculation:
    rows = evidence.matched_txns
    currency = rows[0].currency if rows else "USD"
    amount = 0.0
    line_items: list[str] = []
    basis = "No matching charge was established."
    inputs = user_inputs or {}
    if issue_type == "duplicate_charge" and len(rows) >= 2:
        amount = min(row.amount for row in rows)
        line_items = [f"Extra duplicate charge: {amount:.2f} {currency}"]
        basis = "Refund the extra equal charge; retain one legitimate charge."
    elif issue_type == "wrong_amount" and rows:
        expected = float(inputs.get("expected_amount", 0) or 0)
        if not expected:
            expected = next((float(fact.split(" is ")[1].split(" ")[0]) for fact in evidence.facts if fact.startswith("Expected price")), 0)
        amount = max(0.0, rows[0].amount - expected)
        line_items = [f"Difference between charged {rows[0].amount:.2f} and expected {expected:.2f} {currency}"]
        basis = "Refund only the amount charged above the documented expected price."
    elif issue_type in {"unauthorized", "not_received"} and rows:
        amount = rows[0].amount
        line_items = [f"Full charge: {amount:.2f} {currency}"]
        basis = "Refund the full disputed transaction, subject to PayPal review."
    elif issue_type == "cancelled_subscription" and rows:
        amount = sum(row.amount for row in rows)
        line_items = [f"Post-cancellation charge: {amount:.2f} {currency}"]
        basis = "Refund charges identified after the supplied cancellation date."
    return RefundCalculation(amount=round(amount, 2), currency=currency, line_items=line_items, basis=basis, disclaimer=DISCLAIMER)
