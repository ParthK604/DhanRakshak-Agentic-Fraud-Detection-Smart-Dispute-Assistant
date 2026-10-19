import time

import httpx

from app.config import get_settings


class PayPalClient:
    """Thin async wrapper over PayPal REST: OAuth token caching + generic request()."""

    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at: float = 0.0

    async def _get_token(self) -> str:
        if self._token and time.time() < self._expires_at - 30:
            return self._token
        s = get_settings()
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{s.paypal_base_url}/v1/oauth2/token",
                auth=(s.paypal_client_id, s.paypal_client_secret),
                data={"grant_type": "client_credentials"},
            )
            response.raise_for_status()
        data = response.json()
        self._token = data["access_token"]
        self._expires_at = time.time() + int(data.get("expires_in", 300))
        return self._token

    async def request(self, method: str, path: str, **kwargs) -> dict:
        token = await self._get_token()
        headers = {"Content-Type": "application/json", "Authorization": "Bearer " + token}
        headers.update(kwargs.pop("headers", {}))
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(
                method, f"{get_settings().paypal_base_url}{path}",
                headers=headers, **kwargs,
            )
            response.raise_for_status()
        return response.json() if response.content else {}

    async def ping(self) -> None:
        await self._get_token()


paypal = PayPalClient()
