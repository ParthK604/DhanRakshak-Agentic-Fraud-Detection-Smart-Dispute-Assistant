from datetime import UTC, datetime, timedelta

import pytest

import app.services.paypal_transactions as paypal_transactions
from app.services.paypal_transactions import map_paypal_transaction


def test_map_paypal_transaction_payload() -> None:
    transaction = map_paypal_transaction({
        "transaction_info": {
            "transaction_id": "9AB",
            "transaction_amount": {"currency_code": "USD", "value": "12.50"},
            "receiver_business_name": "Example Store",
            "receiver_account_id": "merchant-1",
            "receiver_email": "merchant@example.com",
            "transaction_status": "S",
            "transaction_initiation_date": "2026-10-01T12:00:00Z",
            "transaction_subject": "Order",
        },
        "payer_info": {"account_id": "buyer-1", "email": "buyer@example.com"},
        "shipping_info": {"address": {"country_code": "US", "city": "Austin"}},
    })
    assert transaction.txn_id == "9AB"
    assert transaction.amount == 12.5
    assert transaction.merchant_name == "Example Store"
    assert transaction.source == "paypal_sandbox"


@pytest.mark.asyncio
async def test_fetch_transactions_uses_paypal_timestamp_precision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request_params: list[dict[str, object]] = []

    async def fake_request(method: str, path: str, **kwargs: object) -> dict[str, object]:
        params = kwargs["params"]
        assert isinstance(params, dict)
        request_params.append(params)
        return {"transaction_details": []}

    monkeypatch.setattr(paypal_transactions.paypal, "request", fake_request)

    start = datetime(2026, 10, 1, 12, 0, 0, 123456, tzinfo=UTC)
    await paypal_transactions.fetch_transactions(start, start + timedelta(days=1))

    assert request_params == [{
        "start_date": "2026-10-01T12:00:00Z",
        "end_date": "2026-10-02T12:00:00Z",
        "page_size": 100,
        "page": 1,
        "fields": "transaction_info,payer_info,shipping_info",
    }]
