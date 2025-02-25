import asyncio
from typing import Any, Coroutine

import aiohttp
from yarl import URL


class AsyncHttpClient:
    def __init__(self, max_connections: int = 10):
        self.session: aiohttp.ClientSession = None
        self.max_connections = max_connections
        self.queue = asyncio.Queue()  # Queue to store responses

    async def __aenter__(self):
        """Initialize the session with connection pooling."""
        connector = aiohttp.TCPConnector(limit=self.max_connections)
        self.session = aiohttp.ClientSession(connector=connector)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Ensure session closure."""
        await self.session.close()

    async def fetch(self, url: str, is_image=False) -> tuple[str, str] | tuple[URL, bytes] | str:
        """Fetch a URL and return its response or error."""
        print(f"[AsyncHttpClient] Fetching {url}")

        try:
            async with self.session.get(url, timeout=30) as response:
                if is_image:
                    content = await response.read()
                    self.queue.put_nowait((url, content))
                    return response.url, content
                text = await response.text()
                print(f"[AsyncHttpClient] Received response from {url}")
                self.queue.put_nowait((url, text))
                return url, text
        except asyncio.TimeoutError:
            print(f"[AsyncHttpClient] Timeout fetching {url}")
            return "Error: Timeout"
        except Exception as e:
            print(f"[AsyncHttpClient] Failed to fetch {url}: {e}")
            return f"Error: {e}", ''

    async def get_result(self):
        """
        Retrieve the next result from the queue.
        Blocks if no result is available.
        """
        return await self.queue.get()  # Get the next available item (FIFO behavior)

    async def get_results(self, batch_size: int = 5):
        """Fetch multiple results asynchronously."""
        return await asyncio.gather(*[self.get_result() for _ in range(batch_size)])

    async def submit_urls(self, urls, is_image=False):
        """
        Fetch multiple URLs concurrently.
        """
        tasks = [self.fetch(url, is_image=is_image) for url in urls]
        await asyncio.gather(*tasks)
