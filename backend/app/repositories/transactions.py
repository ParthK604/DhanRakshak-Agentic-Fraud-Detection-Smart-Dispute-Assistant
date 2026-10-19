from datetime import datetime
from typing import Any, Literal

from app import db
from app.models.schemas import Transaction


async def upsert_many(transactions: list[Transaction]) -> int:
    collection = db.get_db().transactions
    count = 0
    for transaction in transactions:
        result = await collection.replace_one(
            {"txn_id": transaction.txn_id},
            transaction.model_dump(mode="json"),
            upsert=True,
        )
        if result.upserted_id is not None or result.modified_count:
            count += 1
    return count


def _filters_query(
    *,
    user_id: str | None = None,
    merchant: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    source: str | None = None,
    scenario: str | None = None,
) -> dict[str, Any]:
    query: dict[str, Any] = {}
    if user_id:
        query["user_id"] = user_id
    if merchant:
        query["merchant_name"] = {"$regex": merchant, "$options": "i"}
    amount: dict[str, float] = {}
    if min_amount is not None:
        amount["$gte"] = min_amount
    if max_amount is not None:
        amount["$lte"] = max_amount
    if amount:
        query["amount"] = amount
    if from_date is not None or to_date is not None:
        query["timestamp"] = {}
        if from_date is not None:
            query["timestamp"]["$gte"] = from_date
        if to_date is not None:
            query["timestamp"]["$lte"] = to_date
    if source:
        query["source"] = source
    if scenario:
        query["scenario"] = scenario
    return query


async def list_transactions(
    filters: dict[str, Any],
    page: int,
    page_size: int,
    sort: tuple[str, Literal[1, -1]] = ("timestamp", -1),
) -> tuple[list[Transaction], int]:
    query = _filters_query(**filters)
    collection = db.get_db().transactions
    total = await collection.count_documents(query)
    cursor = (
        collection.find(query)
        .sort([sort])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [Transaction.model_validate(document) async for document in cursor]
    return items, total


async def get_transaction(txn_id: str) -> Transaction | None:
    document = await db.get_db().transactions.find_one({"txn_id": txn_id})
    return Transaction.model_validate(document) if document else None


async def get_user_history(
    user_id: str, since: datetime | None = None, until: datetime | None = None
) -> list[Transaction]:
    query = _filters_query(user_id=user_id, from_date=since, to_date=until)
    cursor = db.get_db().transactions.find(query).sort("timestamp", -1)
    return [Transaction.model_validate(document) async for document in cursor]


async def get_merchant_history(user_id: str, merchant_name: str) -> list[Transaction]:
    query = {"user_id": user_id, "merchant_name": merchant_name}
    cursor = db.get_db().transactions.find(query).sort("timestamp", -1)
    return [Transaction.model_validate(document) async for document in cursor]
