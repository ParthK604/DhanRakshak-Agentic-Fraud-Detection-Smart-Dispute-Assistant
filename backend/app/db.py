from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings

_client: AsyncIOMotorClient | None = None


def connect() -> None:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            get_settings().mongodb_uri, serverSelectionTimeoutMS=5000
        )


def close() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_db() -> AsyncIOMotorDatabase:
    if _client is None:
        connect()
    return _client[get_settings().mongodb_db]  # type: ignore[index]


async def ping() -> None:
    if _client is None:
        connect()
    await _client.admin.command("ping")  # type: ignore[union-attr]


async def ensure_indexes() -> None:
    database = get_db()
    await database.transactions.create_index("txn_id", unique=True)
    await database.transactions.create_index([("user_id", 1), ("timestamp", -1)])
    await database.transactions.create_index([("user_id", 1), ("merchant_name", 1)])
    for collection in ("risk_scores", "disputes", "merchants"):
        await database[collection].create_index("_id")
    await database.risk_scores.create_index("txn_id", unique=True)
    await database.risk_scores.create_index([("user_id", 1), ("created_at", -1)])
    await database.disputes.create_index("dispute_id", unique=True)
    await database.disputes.create_index([("user_id", 1), ("created_at", -1)])
    await database.dispute_sessions.create_index("session_id", unique=True)
    await database.dispute_sessions.create_index("updated_at", expireAfterSeconds=7 * 24 * 60 * 60)
    await database.merchants.create_index("merchant_id", unique=True)
    await database.merchants.create_index("trust_score")
    await database.merchants.create_index([("updated_at", -1)])