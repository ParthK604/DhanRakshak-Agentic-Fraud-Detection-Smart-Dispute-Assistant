from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.models.schemas import SyncResult, Transaction, TransactionPage
from app.repositories import transactions as repository
from app.services.paypal_transactions import (
    PayPalTransactionSearchPermissionError,
    fetch_transactions,
)
from scripts.seed_data import generate_seed_transactions

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("", response_model=TransactionPage)
async def list_transaction_endpoint(
    user_id: str | None = None,
    merchant: str | None = None,
    min_amount: float | None = Query(default=None, ge=0),
    max_amount: float | None = Query(default=None, ge=0),
    from_date: datetime | None = Query(default=None, alias="from"),
    to_date: datetime | None = Query(default=None, alias="to"),
    source: Literal["paypal_sandbox", "seeded"] | None = None,
    scenario: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    sort_by: Literal["timestamp", "amount", "merchant_name", "status"] = "timestamp",
    sort_dir: Literal["asc", "desc"] = "desc",
) -> TransactionPage:
    if min_amount is not None and max_amount is not None and min_amount > max_amount:
        raise HTTPException(status_code=400, detail="min_amount cannot exceed max_amount")
    items, total = await repository.list_transactions(
        {
            "user_id": user_id, "merchant": merchant, "min_amount": min_amount,
            "max_amount": max_amount, "from_date": from_date, "to_date": to_date,
            "source": source, "scenario": scenario,
        },
        page,
        page_size,
        (sort_by, 1 if sort_dir == "asc" else -1),
    )
    return TransactionPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/{txn_id}", response_model=Transaction)
async def get_transaction_endpoint(txn_id: str) -> Transaction:
    transaction = await repository.get_transaction(txn_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


@router.post("/sync", response_model=SyncResult)
async def sync_transactions(
    days: int = Query(default=30, ge=1, le=365),
) -> SyncResult:
    try:
        fetched = await fetch_transactions(datetime.now(UTC) - timedelta(days=days), datetime.now(UTC))
    except PayPalTransactionSearchPermissionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    upserted = await repository.upsert_many(fetched)
    return SyncResult(fetched=len(fetched), upserted=upserted, source="paypal_sandbox")


@router.post("/seed", response_model=SyncResult)
async def seed_transactions() -> SyncResult:
    if not get_settings().enable_dev_endpoints:
        raise HTTPException(status_code=404, detail="Not found")
    rows = generate_seed_transactions()
    upserted = await repository.upsert_many(rows)
    return SyncResult(fetched=len(rows), upserted=upserted, source="seeded")


@router.post("/seed/reset", response_model=SyncResult)
async def reset_seed_transactions() -> SyncResult:
    if not get_settings().enable_dev_endpoints:
        raise HTTPException(status_code=404, detail="Not found")
    from app import db

    result = await db.get_db().transactions.delete_many({"source": "seeded"})
    return SyncResult(
        fetched=0, upserted=int(result.deleted_count), source="seeded",
        note=f"Deleted {result.deleted_count} seeded transactions.",
    )
