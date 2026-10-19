from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.config import get_settings
from app.models.dispute import DisputeRecord, TimelineEvent
from app.services.paypal_client import paypal


async def file_dispute(record: DisputeRecord) -> DisputeRecord:
    if get_settings().dispute_submission_mode == "prepared":
        return _prepared(record, "Configured DISPUTE_SUBMISSION_MODE=prepared.")
    try:
        response = await paypal.request(
            "POST",
            "/v1/customer/disputes",
            headers={"PayPal-Request-Id": str(uuid4())},
            json={
                "disputed_transactions": [{"buyer_transaction_id": txn_id} for txn_id in record.txn_ids],
                "reason": record.issue_type.upper(),
                "dispute_amount": {
                    "currency_code": record.refund.currency,
                    "value": f"{record.refund.amount:.2f}",
                },
            },
        )
        record.paypal_dispute_id = response.get("dispute_id")
        if not record.paypal_dispute_id:
            return _prepared(record, "PayPal returned no dispute ID.")
        record.submission_mode = "paypal"
        record.status = "submitted"
        record.updated_at = datetime.now(UTC)
        record.timeline.append(TimelineEvent(event="submitted", detail="Created through PayPal Customer Disputes API.", at=record.updated_at))
        return record
    except Exception as exc:
        return _prepared(record, f"PayPal filing unavailable; dispute prepared locally: {str(exc)[:200]}")


def _prepared(record: DisputeRecord, reason: str) -> DisputeRecord:
    now = datetime.now(UTC)
    record.submission_mode = "prepared"
    record.status = "submitted"
    record.fallback_reason = reason
    record.updated_at = now
    record.timeline.append(TimelineEvent(
        event="prepared", detail="Letter and evidence are ready. Submit them through the PayPal sandbox Resolution Center.",
        at=now,
    ))
    return record


async def sync_status(record: DisputeRecord) -> DisputeRecord:
    if record.submission_mode == "prepared" or not record.paypal_dispute_id:
        return record
    response = await paypal.request("GET", f"/v1/customer/disputes/{record.paypal_dispute_id}")
    status = response.get("status")
    if status:
        record.timeline.append(TimelineEvent(event="status_sync", detail=f"PayPal status: {status}", at=datetime.now(UTC)))
    return record
