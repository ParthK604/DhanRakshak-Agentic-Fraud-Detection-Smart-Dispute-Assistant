from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.models.schemas import Transaction
from app.services.paypal_client import paypal


class PayPalTransactionSearchPermissionError(RuntimeError):
    """Transaction Search is unavailable until enabled for the sandbox app."""


def _paypal_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        result = value
    else:
        text = str(value or "").replace("Z", "+00:00")
        try:
            result = datetime.fromisoformat(text)
        except ValueError:
            result = datetime.now(UTC)
    return result.replace(tzinfo=UTC) if result.tzinfo is None else result.astimezone(UTC)


def map_paypal_transaction(raw: dict[str, Any]) -> Transaction:
    info = raw.get("transaction_info") or {}
    payer = raw.get("payer_info") or {}
    shipping = raw.get("shipping_info") or {}
    payer_name = payer.get("payer_name") or {}
    merchant = (
        info.get("receiver_business_name")
        or info.get("receiver_email")
        or info.get("merchant_name")
        or "PayPal merchant"
    )
    amount = info.get("transaction_amount") or {}
    address = shipping.get("address") or {}
    country = address.get("country_code") or payer.get("country_code") or "US"
    return Transaction(
        txn_id=str(info.get("transaction_id") or raw.get("transaction_id") or "unknown"),
        user_id=str(payer.get("account_id") or payer.get("email") or "paypal-user"),
        amount=float(amount.get("value") or 0),
        currency=str(amount.get("currency_code") or "USD"),
        merchant_name=str(merchant),
        merchant_id=info.get("receiver_account_id"),
        payee_email=info.get("receiver_email"),
        direction="incoming"
        if str(info.get("transaction_event_code", "")).startswith("T00")
        else "outgoing",
        country=str(country),
        city=address.get("city") or payer_name.get("alternate_full_name"),
        timestamp=_parse_timestamp(info.get("transaction_initiation_date")),
        status=str(info.get("transaction_status") or "UNKNOWN"),
        description=info.get("transaction_subject") or info.get("transaction_note"),
        source="paypal_sandbox",
    )


async def fetch_transactions(since: datetime, until: datetime) -> list[Transaction]:
    """Fetch Transaction Search data in PayPal's documented 31-day windows."""
    transactions: list[Transaction] = []
    window_start = since.astimezone(UTC)
    until = until.astimezone(UTC)
    while window_start < until:
        window_end = min(window_start + timedelta(days=31), until)
        page = 1
        while True:
            params = {
                "start_date": _paypal_timestamp(window_start),
                "end_date": _paypal_timestamp(window_end),
                "page_size": 100,
                "page": page,
                "fields": "transaction_info,payer_info,shipping_info",
            }
            try:
                payload = await paypal.request(
                    "GET", "/v1/reporting/transactions", params=params
                )
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (401, 403):
                    raise PayPalTransactionSearchPermissionError(
                        "PayPal Transaction Search is not enabled for this sandbox app. "
                        "Enable Transaction Search in the PayPal Developer Dashboard."
                    ) from exc
                raise
            details = payload.get("transaction_details") or []
            transactions.extend(map_paypal_transaction(item) for item in details)
            total_pages = int(payload.get("total_pages") or page)
            if page >= total_pages or not details:
                break
            page += 1
        window_start = window_end
    return transactions
