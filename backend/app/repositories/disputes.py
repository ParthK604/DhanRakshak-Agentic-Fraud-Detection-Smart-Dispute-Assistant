from __future__ import annotations

from typing import Any

from app import db
from app.models.dispute import DisputeRecord, DisputeSummary


async def save(record: DisputeRecord) -> DisputeRecord:
    await db.get_db().disputes.replace_one(
        {"dispute_id": record.dispute_id}, record.model_dump(mode="json"), upsert=True
    )
    return record


async def get(dispute_id: str) -> DisputeRecord | None:
    document = await db.get_db().disputes.find_one({"dispute_id": dispute_id})
    return DisputeRecord.model_validate(document) if document else None


async def list_records(filters: dict[str, Any], page: int, page_size: int) -> tuple[list[DisputeRecord], int]:
    query = {key: value for key, value in filters.items() if value}
    collection = db.get_db().disputes
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size)
    return [DisputeRecord.model_validate(item) async for item in cursor], total


async def summary(user_id: str | None = None) -> DisputeSummary:
    rows, _ = await list_records({"user_id": user_id}, 1, 10000)
    by_status: dict[str, int] = {}
    by_issue_type: dict[str, int] = {}
    total_refund = 0.0
    for row in rows:
        by_status[row.status] = by_status.get(row.status, 0) + 1
        by_issue_type[row.issue_type] = by_issue_type.get(row.issue_type, 0) + 1
        total_refund += row.refund.amount
    return DisputeSummary(total=len(rows), by_status=by_status, by_issue_type=by_issue_type, total_refund_amount=round(total_refund, 2))


async def save_session(session_id: str, state: dict[str, Any]) -> None:
    await db.get_db().dispute_sessions.replace_one(
        {"session_id": session_id}, {"session_id": session_id, **state}, upsert=True
    )


async def get_session(session_id: str) -> dict[str, Any] | None:
    return await db.get_db().dispute_sessions.find_one({"session_id": session_id})
