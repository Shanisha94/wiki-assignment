import asyncio
import logging
from bs4 import BeautifulSoup
from db.animals_db import AnimalsInMemoryDB
from client.http_client import AsyncHttpClient
from scraper.web_scraper import WebScraper


class AnimalPageScraper(WebScraper):
    def __init__(self, http_client: AsyncHttpClient, http_client_image: AsyncHttpClient, db: AnimalsInMemoryDB,
                 max_concurrent_requests: int = 10):
        super().__init__()
        self._logger = logging.getLogger(__name__)
        self._http_client_animal_page = http_client
        self._http_client_image = http_client_image
        self._db = db
        self._queue = asyncio.Queue()  # Queue for processing pages
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)  # Limit concurrent requests

    async def run(self):
        """Starts the animal page processing"""
        asyncio.create_task(self._fetch_animal_pages())

        # Start multiple worker tasks to process pages faster
        workers = [asyncio.create_task(self._page_worker()) for _ in range(10)]
        await asyncio.gather(*workers)

    async def _fetch_animal_pages(self):
        """Continuously fetches animal pages and adds them to the queue."""
        while not self._stop_event.is_set():
            try:
                result = await self._http_client_animal_page.get_result()
                await self._queue.put(result)
            except Exception as e:
                self._logger.error(f"Error fetching animal page: {e}")
            await asyncio.sleep(0.01)

    async def _page_worker(self):
        """Processes animal pages from the queue asynchronously."""
        while not self._stop_event.is_set():
            url, response = await self._queue.get()
            await self._process_page(url, response)
            self._queue.task_done()

    async def _process_page(self, url: str, response: str):
        """Processes an individual animal page and fetches the image URL."""
        animal_name = url.split('/')[-1]
        image_url = await self._extract_image_url(response, animal_name)
        if image_url:
            self._db.insert_image_url(image_url, animal_name)
            asyncio.create_task(self._http_client_image.submit_urls([image_url]))  # Non-blocking image fetch

    async def _extract_image_url(self, html_page: str, animal_name: str) -> str | None:
        """Extracts the first available image URL from the page."""
        print(f"Fetching image for {animal_name}")
        soup = BeautifulSoup(html_page, "html.parser")
        image_tag = soup.find("img")
        if not image_tag:
            print(f"No image found for {animal_name}")
            return None
        return "https:" + image_tag.get("src")
