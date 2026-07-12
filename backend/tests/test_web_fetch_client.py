import unittest

import httpx

from app.core.config import Settings
from app.services.scraper.web_fetch_client import (
    WebFetchClient,
    WebFetchConfigurationError,
    WebFetchResponseError,
)


class WebFetchClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_calls_central_service_with_bearer_token(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url), "http://webfetch.test/v1/fetch")
            self.assertEqual(request.headers["Authorization"], "Bearer secret")
            self.assertEqual(
                request.read(), b'{"url":"https://example.com","mode":"auto"}'
            )
            return httpx.Response(200, json={"content": "<html>ok</html>"})

        settings = Settings(
            WEB_FETCH_BASE_URL="http://webfetch.test/",
            WEB_FETCH_API_KEY="secret",
        )
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as http_client:
            client = WebFetchClient(settings=settings, http_client=http_client)
            self.assertEqual(
                await client.fetch("https://example.com"), "<html>ok</html>"
            )

    async def test_fetch_requires_configuration(self) -> None:
        client = WebFetchClient(
            settings=Settings(WEB_FETCH_BASE_URL="", WEB_FETCH_API_KEY="")
        )
        with self.assertRaises(WebFetchConfigurationError):
            await client.fetch("https://example.com")

    async def test_fetch_rejects_response_without_content(self) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, json={"status": "ok"})
        )
        settings = Settings(
            WEB_FETCH_BASE_URL="http://webfetch.test", WEB_FETCH_API_KEY="secret"
        )
        async with httpx.AsyncClient(transport=transport) as http_client:
            client = WebFetchClient(settings=settings, http_client=http_client)
            with self.assertRaises(WebFetchResponseError):
                await client.fetch("https://example.com")


if __name__ == "__main__":
    unittest.main()
