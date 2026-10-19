import asyncio
from datetime import UTC, datetime, timedelta

import httpx

from app.services.paypal_client import paypal


async def probe(name: str, operation) -> None:
    try:
        await operation
        print(f"{name}: 200 ok")
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        detail = exc.response.json().get("name", "http_error") if exc.response.content else "http_error"
        print(f"{name}: {code} {detail}")
    except Exception as exc:
        print(f"{name}: error {type(exc).__name__}")


async def main() -> None:
    now = datetime.now(UTC)
    await probe("OAuth token", paypal._get_token())
    await probe("Transaction Search", paypal.request(
        "GET", "/v1/reporting/transactions",
        params={
            "start_date": (now - timedelta(days=30)).isoformat().replace("+00:00", "Z"),
            "end_date": now.isoformat().replace("+00:00", "Z"),
            "page_size": 1,
            "fields": "transaction_info,payer_info,shipping_info",
        },
    ))
    await probe("Disputes list", paypal.request("GET", "/v1/customer/disputes", params={"page_size": 1}))
    await probe("Orders create", paypal.request(
        "POST", "/v2/checkout/orders",
        headers={"PayPal-Request-Id": "dhanrakshak-probe-order"},
        json={
            "intent": "CAPTURE",
            "purchase_units": [{"amount": {"currency_code": "USD", "value": "1.00"}}],
            "application_context": {
                "return_url": "https://example.com/paypal/return",
                "cancel_url": "https://example.com/paypal/cancel",
            },
        },
    ))


if __name__ == "__main__":
    asyncio.run(main())
