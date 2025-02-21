import asyncio
import aiohttp

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

    async def fetch(self, url: str):
        """
        Fetch a URL and store its response in the queue.
        """
        try:
            async with self.session.get(url) as response:
                text = await response.read()
                await self.queue.put((url, text))  # Store result in the queue
        except Exception as e:
            await self.queue.put((url, f"Error: {str(e)}"))  # Store error response

    async def get_result(self):
        """
        Retrieve the next result from the queue.
        Blocks if no result is available.
        """
        return await self.queue.get()  # Get the next available item (FIFO behavior)

    async def submit_urls(self, urls):
        """
        Fetch multiple URLs concurrently.
        """
        tasks = [self.fetch(url) for url in urls]
        await asyncio.gather(*tasks)
