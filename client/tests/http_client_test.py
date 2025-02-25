import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from yarl import URL

from client.http_client import AsyncHttpClient


@pytest.mark.asyncio
async def test_fetch_success_text():
    url = "https://example.com"
    response_text = "Hello, World!"

    mock_response = AsyncMock()
    mock_response.text.return_value = response_text
    mock_response.url = URL(url)

    with patch("aiohttp.ClientSession.get", return_value=mock_response):
        async with AsyncHttpClient() as client:
            result = await client.fetch(url)
            assert result == (url, response_text)


@pytest.mark.asyncio
async def test_fetch_timeout():
    url = "https://example.com"

    with patch("aiohttp.ClientSession.get", side_effect=asyncio.TimeoutError()):
        async with AsyncHttpClient() as client:
            result = await client.fetch(url)
            assert result == "Error: Timeout"


@pytest.mark.asyncio
async def test_fetch_exception():
    url = "https://example.com"
    error_message = "Connection Error"

    with patch("aiohttp.ClientSession.get", side_effect=Exception(error_message)):
        async with AsyncHttpClient() as client:
            result = await client.fetch(url)
            assert result == (f"Error: {error_message}", "")


@pytest.mark.asyncio
async def test_queue_operations():
    async with AsyncHttpClient() as client:
        await client.queue.put(("https://example.com", "response text"))
        result = await client.get_result()
        assert result == ("https://example.com", "response text")


@pytest.mark.asyncio
async def test_get_results():
    async with AsyncHttpClient() as client:
        for i in range(3):
            await client.queue.put((f"https://example.com/{i}", f"response {i}"))

        results = await client.get_results(batch_size=3)
        expected_results = [
            (f"https://example.com/{i}", f"response {i}") for i in range(3)
        ]
        assert results == expected_results
