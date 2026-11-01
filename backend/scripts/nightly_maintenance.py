"""Small, safe maintenance job for an optional Render cron service."""

import asyncio
import logging
from datetime import UTC, datetime

from app import db
from app.agents.merchant_graph import score_merchant
from app.repositories import merchants, risk_scores, transactions
from app.services.paypal_transactions import (
    PayPalTransactionSearchPermissionError,
    fetch_transactions,
)
from app.agents.risk_graph import score_transaction

logger = logging.getLogger("nightly_maintenance")


def select_stale_merchants(rows, now: datetime | None = None):
    current = now or datetime.now(UTC)
    return [row for row in rows if row.expires_at <= current]


def describe_sync_error(error: Exception) -> str:
    if isinstance(error, PayPalTransactionSearchPermissionError):
        return "PayPal Transaction Search permission is unavailable; continuing with stored data."
    return f"PayPal sync failed ({type(error).__name__}); continuing with stored data."


async def run() -> int:
    db.connect()
    try:
        try:
            fetched = await fetch_transactions(
                datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0),
                datetime.now(UTC),
            )
            logger.info("PayPal sync fetched %d transactions.", len(fetched))
            await transactions.upsert_many(fetched)
        except Exception as exc:
            logger.warning(describe_sync_error(exc))

        rows, _ = await transactions.list_transactions({}, 1, 25, ("timestamp", -1))
        scored = 0
        for row in rows:
            if await risk_scores.get(row.txn_id) is None:
                await score_transaction(row)
                scored += 1
        logger.info("Scored %d previously unscored transactions.", scored)

        merchant_rows, _ = await merchants.list_assessments({}, 1, 100)
        refreshed = 0
        for merchant in select_stale_merchants(merchant_rows):
            await score_merchant(merchant.merchant_name)
            refreshed += 1
        logger.info("Refreshed %d stale merchant assessments.", refreshed)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    raise SystemExit(asyncio.run(run()))
