"""Create a small approval-required PayPal sandbox order.

Open the printed approval URL with the sandbox personal account, then use the
order id with the capture command documented in the Phase 2 notes.
"""
import asyncio
import argparse
import uuid

from app.services.paypal_client import paypal


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture-order-id")
    args = parser.parse_args()
    if args.capture_order_id:
        payload = await paypal.request(
            "POST", f"/v2/checkout/orders/{args.capture_order_id}/capture",
            headers={"PayPal-Request-Id": f"dhanrakshak-capture-{args.capture_order_id}"},
        )
        print(f"Capture status: {payload.get('status', 'unknown')}")
        return
    request_id = f"dhanrakshak-demo-{uuid.uuid4()}"
    payload = await paypal.request(
        "POST", "/v2/checkout/orders",
        headers={"PayPal-Request-Id": request_id},
        json={
            "intent": "CAPTURE",
            "purchase_units": [{"amount": {"currency_code": "USD", "value": "9.99"}}],
            "application_context": {
                "return_url": "https://example.com/paypal/return",
                "cancel_url": "https://example.com/paypal/cancel",
            },
        },
    )
    print(f"Order id: {payload.get('id')}")
    for link in payload.get("links", []):
        if link.get("rel") == "approve":
            print(f"Approval URL: {link.get('href')}")


if __name__ == "__main__":
    asyncio.run(main())
