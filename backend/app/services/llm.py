from groq import AsyncGroq

from app.config import get_settings

_client: AsyncGroq | None = None


def get_llm() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=get_settings().groq_api_key)
    return _client


async def ping() -> str:
    resp = await get_llm().chat.completions.create(
        model=get_settings().groq_model,
        messages=[{"role": "user", "content": "Reply with the single word: pong"}],
        max_completion_tokens=256,
    )
    return (resp.choices[0].message.content or "").strip()