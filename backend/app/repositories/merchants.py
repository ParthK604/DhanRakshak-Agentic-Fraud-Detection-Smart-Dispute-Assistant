from __future__ import annotations

from typing import Any

from app import db
from app.models.merchant import MerchantSummary, TrustAssessment


async def save(assessment: TrustAssessment) -> TrustAssessment:
    await db.get_db().merchants.replace_one(
        {"merchant_id": assessment.merchant_id}, assessment.model_dump(mode="json"), upsert=True
    )
    return assessment


async def get(merchant_id: str) -> TrustAssessment | None:
    document = await db.get_db().merchants.find_one({"merchant_id": merchant_id})
    return TrustAssessment.model_validate(document) if document else None


async def list_assessments(filters: dict[str, Any], page: int, page_size: int) -> tuple[list[TrustAssessment], int]:
    query: dict[str, Any] = {}
    if filters.get("q"):
        query["merchant_name"] = {"$regex": filters["q"], "$options": "i"}
    if filters.get("trust_level"):
        query["trust_level"] = filters["trust_level"]
    if filters.get("min_score") is not None or filters.get("max_score") is not None:
        query["trust_score"] = {}
        if filters.get("min_score") is not None:
            query["trust_score"]["$gte"] = filters["min_score"]
        if filters.get("max_score") is not None:
            query["trust_score"]["$lte"] = filters["max_score"]
    collection = db.get_db().merchants
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort("updated_at", -1).skip((page - 1) * page_size).limit(page_size)
    return [TrustAssessment.model_validate(item) async for item in cursor], total


async def summary() -> MerchantSummary:
    rows, _ = await list_assessments({}, 1, 10000)
    levels = {level: sum(row.trust_level == level for row in rows) for level in ("trusted", "caution", "high_risk", "unknown")}
    red_flags: dict[str, int] = {}
    for row in rows:
        for flag in row.red_flags:
            red_flags[flag] = red_flags.get(flag, 0) + 1
    lowest = sorted(rows, key=lambda row: row.trust_score)[:5]
    return MerchantSummary(
        total=len(rows), by_level=levels,
        lowest_trust_merchants=[{"merchant_id": row.merchant_id, "merchant_name": row.merchant_name, "trust_score": row.trust_score} for row in lowest],
        common_red_flags=[{"flag": flag, "count": count} for flag, count in sorted(red_flags.items(), key=lambda item: item[1], reverse=True)[:5]],
    )
