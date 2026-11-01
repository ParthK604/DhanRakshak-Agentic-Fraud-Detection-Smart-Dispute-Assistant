from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from scripts.nightly_maintenance import describe_sync_error, select_stale_merchants
from app.services.paypal_transactions import PayPalTransactionSearchPermissionError


def test_select_stale_merchants_is_deterministic() -> None:
    now = datetime(2026, 1, 2, tzinfo=UTC)
    rows = [
        SimpleNamespace(expires_at=now - timedelta(seconds=1)),
        SimpleNamespace(expires_at=now + timedelta(seconds=1)),
    ]
    assert select_stale_merchants(rows, now) == rows[:1]


def test_permission_error_is_safe_to_continue() -> None:
    message = describe_sync_error(PayPalTransactionSearchPermissionError("forbidden"))
    assert "continuing" in message
