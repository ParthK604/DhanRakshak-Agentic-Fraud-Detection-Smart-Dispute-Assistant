from groq import AsyncGroq

from app.config import get_settings

_client: AsyncGroq | None = None


def get_llm() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=get_settings().groq_api_key)
    return _client


async def ping() -> str:
    models = await get_llm().models.list()
    return f"models available: {len(getattr(models, 'data', []))}"