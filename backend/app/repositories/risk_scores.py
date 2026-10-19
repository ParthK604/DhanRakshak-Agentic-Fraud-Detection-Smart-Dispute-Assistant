from __future__ import annotations

from datetime import datetime
from typing import Any

from app import db
from app.models.schemas import RiskAssessment, RiskSummary


async def save(assessment: RiskAssessment) -> RiskAssessment:
    await db.get_db().risk_scores.replace_one(
        {"txn_id": assessment.txn_id},
        assessment.model_dump(mode="json"),
        upsert=True,
    )
    return assessment


async def get(txn_id: str) -> RiskAssessment | None:
    document = await db.get_db().risk_scores.find_one({"txn_id": txn_id})
    return RiskAssessment.model_validate(document) if document else None


async def list_scores(
    filters: dict[str, Any], page: int, page_size: int, sort: tuple[str, int] = ("created_at", -1)
) -> tuple[list[RiskAssessment], int]:
    query: dict[str, Any] = {}
    for key in ("user_id", "risk_level"):
        if filters.get(key):
            query[key] = filters[key]
    if filters.get("min_score") is not None or filters.get("max_score") is not None:
        query["risk_score"] = {}
        if filters.get("min_score") is not None:
            query["risk_score"]["$gte"] = filters["min_score"]
        if filters.get("max_score") is not None:
            query["risk_score"]["$lte"] = filters["max_score"]
    if filters.get("from_date") is not None or filters.get("to_date") is not None:
        query["created_at"] = {}
        if filters.get("from_date") is not None:
            query["created_at"]["$gte"] = filters["from_date"]
        if filters.get("to_date") is not None:
            query["created_at"]["$lte"] = filters["to_date"]
    collection = db.get_db().risk_scores
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort([sort]).skip((page - 1) * page_size).limit(page_size)
    return [RiskAssessment.model_validate(item) async for item in cursor], total


async def summary(user_id: str | None = None) -> RiskSummary:
    query = {"user_id": user_id} if user_id else {}
    rows = [RiskAssessment.model_validate(item) async for item in db.get_db().risk_scores.find(query)]
    counts = {level: sum(row.risk_level == level for row in rows) for level in ("low", "medium", "high")}
    signal_counts: dict[str, int] = {}
    for row in rows:
        for signal in row.signals:
            if signal.triggered:
                signal_counts[signal.name] = signal_counts.get(signal.name, 0) + 1
    top = [{"name": name, "count": count} for name, count in sorted(signal_counts.items(), key=lambda item: item[1], reverse=True)[:5]]
    return RiskSummary(
        total=len(rows), **counts,
        average_score=round(sum(row.risk_score for row in rows) / len(rows), 2) if rows else 0.0,
        top_signals=top,
    )
