"""Client for the shared WebFetch service."""

from typing import Any

import httpx

from app.core.config import Settings, get_settings


class WebFetchConfigurationError(RuntimeError):
    """Raised when the WebFetch service has not been configured."""


class WebFetchResponseError(RuntimeError):
    """Raised when WebFetch returns a successful but unusable response."""


class WebFetchClient:
    def __init__(
        self,
        settings: Settings | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._http_client = http_client

    async def fetch(self, url: str) -> str:
        base_url = self.settings.WEB_FETCH_BASE_URL.strip().rstrip("/")
        api_key = self.settings.WEB_FETCH_API_KEY.strip()
        if not base_url or not api_key:
            raise WebFetchConfigurationError(
                "WEB_FETCH_BASE_URL and WEB_FETCH_API_KEY must be configured"
            )

        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {"url": url, "mode": self.settings.WEB_FETCH_MODE}

        if self._http_client is not None:
            response = await self._http_client.post(
                f"{base_url}/v1/fetch", headers=headers, json=payload
            )
        else:
            async with httpx.AsyncClient(
                timeout=self.settings.WEB_FETCH_TIMEOUT_SECONDS
            ) as client:
                response = await client.post(
                    f"{base_url}/v1/fetch", headers=headers, json=payload
                )

        response.raise_for_status()
        data = response.json()
        content = self._extract_content(data)
        if content is None:
            raise WebFetchResponseError("WebFetch response does not contain page content")
        return content

    @classmethod
    def _extract_content(cls, data: Any) -> str | None:
        """Accept the documented response and tolerate a nested result envelope."""
        if not isinstance(data, dict):
            return None
        for key in ("content", "html", "text", "body", "body_text"):
            value = data.get(key)
            if isinstance(value, str):
                return value
        for key in ("data", "result"):
            nested = cls._extract_content(data.get(key))
            if nested is not None:
                return nested
        return None
