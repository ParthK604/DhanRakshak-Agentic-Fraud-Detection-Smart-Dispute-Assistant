import argparse
import asyncio
from collections import Counter
from datetime import UTC, datetime, timedelta
from random import Random

from app import db
from app.models.schemas import Transaction
from app.repositories.transactions import upsert_many

BASE_TIME = datetime(2026, 10, 18, 12, tzinfo=UTC)
USER_ID = "demo-user-1"


def _transaction(txn_id: str, when: datetime, merchant: str, amount: float, **kwargs) -> Transaction:
    fields = {
        "txn_id": txn_id, "user_id": USER_ID, "amount": amount, "currency": "USD",
        "merchant_name": merchant, "direction": "outgoing", "country": "US",
        "timestamp": when, "status": "COMPLETED", "source": "seeded",
    }
    fields.update(kwargs)
    return Transaction(**fields)


def generate_baseline() -> list[Transaction]:
    rng = Random(20261018)
    merchants = [
        ("Whole Foods", 68.0, 22), ("Netflix", 15.49, 30),
        ("Spotify", 11.99, 28), ("Uber", 24.0, 11), ("Amazon", 52.0, 17),
        ("City Utilities", 118.0, 31),
    ]
    rows: list[Transaction] = []
    for merchant, typical, day_step in merchants:
        day = 6
        index = 0
        while day < 90:
            amount = round(max(4, rng.gauss(typical, typical * 0.12)), 2)
            rows.append(_transaction(
                f"seed-baseline-{index}-{merchant.lower().replace(' ', '-')}",
                BASE_TIME - timedelta(days=day, hours=rng.randrange(0, 18)),
                merchant, amount, scenario="baseline",
            ))
            day += day_step
            index += 1
    return rows


def generate_duplicate_charge() -> list[Transaction]:
    when = BASE_TIME - timedelta(days=5, hours=2)
    return [
        _transaction("seed-duplicate-netflix-1", when, "Netflix", 15.49, scenario="duplicate_charge"),
        _transaction("seed-duplicate-netflix-2", when + timedelta(minutes=3), "Netflix", 15.49, scenario="duplicate_charge"),
        _transaction("seed-duplicate-amazon-1", when - timedelta(days=2), "Amazon", 42.00, scenario="duplicate_charge"),
        _transaction("seed-duplicate-amazon-2", when - timedelta(days=2, minutes=-4), "Amazon", 42.00, scenario="duplicate_charge"),
    ]


def generate_unusual_amount() -> list[Transaction]:
    return [_transaction("seed-unusual-amount", BASE_TIME - timedelta(days=4), "Amazon", 489.99, scenario="unusual_amount")]


def generate_new_payee_large() -> list[Transaction]:
    return [_transaction(
        "seed-new-payee-large", BASE_TIME - timedelta(days=3, hours=5),
        "Northstar Electronics", 1250.00, payee_email="orders@northstar.example",
        scenario="new_payee_large",
    )]


def generate_geo_anomaly() -> list[Transaction]:
    when = BASE_TIME - timedelta(days=2)
    return [
        _transaction("seed-geo-us", when, "Uber", 22.50, country="US", city="New York", scenario="geo_anomaly"),
        _transaction("seed-geo-sg", when + timedelta(hours=2), "Luxury Goods SG", 310.00, country="SG", city="Singapore", scenario="geo_anomaly"),
    ]


def generate_velocity_burst() -> list[Transaction]:
    when = BASE_TIME - timedelta(days=1, hours=3)
    return [
        _transaction(f"seed-velocity-{i}", when + timedelta(seconds=i * 32),
                     "QuickCart", 8.50 + i, scenario="velocity_burst")
        for i in range(9)
    ]


def generate_suspicious_merchant() -> list[Transaction]:
    when = BASE_TIME - timedelta(days=1)
    return [
        _transaction("seed-suspicious-merchant", when, "Flash Prize Outlet", 299.00,
                     payee_email="claim-reward@example.invalid", scenario="suspicious_merchant"),
        _transaction("seed-legitimate-merchant", when - timedelta(days=24), "Acme Hardware", 74.25,
                     scenario="baseline"),
    ]


def generate_cancelled_subscription_charge() -> list[Transaction]:
    cancel_date = BASE_TIME - timedelta(days=12)
    return [_transaction(
        "seed-cancelled-netflix", BASE_TIME - timedelta(days=3), "Netflix", 15.49,
        description=f"Subscription renewal; stated cancel date: {cancel_date.date().isoformat()}",
        scenario="cancelled_subscription",
    )]


def generate_wrong_amount() -> list[Transaction]:
    return [_transaction(
        "seed-wrong-amount-spotify", BASE_TIME - timedelta(days=2, hours=4),
        "Spotify", 19.99, description="Plan renewal; expected price: 9.99",
        scenario="wrong_amount",
    )]


def generate_seed_transactions() -> list[Transaction]:
    rows: list[Transaction] = []
    for generator in (
        generate_baseline, generate_duplicate_charge, generate_unusual_amount,
        generate_new_payee_large, generate_geo_anomaly, generate_velocity_burst,
        generate_suspicious_merchant, generate_cancelled_subscription_charge,
        generate_wrong_amount,
    ):
        rows.extend(generator())
    return rows


async def seed(reset: bool = False) -> None:
    db.connect()
    collection = db.get_db().transactions
    if reset:
        await collection.delete_many({"source": "seeded"})
    rows = generate_seed_transactions()
    await upsert_many(rows)
    counts = Counter(row.scenario for row in rows)
    print("Scenario                 Count")
    print("------------------------------")
    for name, count in sorted(counts.items()):
        print(f"{name:<24} {count}")
    print(f"{'total':<24} {len(rows)}")
    db.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Delete seeded rows before loading them")
    args = parser.parse_args()
    asyncio.run(seed(args.reset))


if __name__ == "__main__":
    main()
