"""Animal Page Scraper Module

This module defines the AnimalPageScraper class, responsible for fetching and processing
animal pages using asynchronous HTTP requests and an in-memory database.
"""

import asyncio
import logging
from typing import Optional

from bs4 import BeautifulSoup
from db.animals_db import AnimalsInMemoryDB
from client.http_client import AsyncHttpClient
from scraper.web_scraper import WebScraper

MAX_ATTEMPTS = 5  # Maximum number of retry attempts
INITIAL_BACKOFF = 1  # Initial backoff time in seconds
BACKOFF_MULTIPLIER = 2  # Multiplier for exponential backoff


class AnimalPageScraper(WebScraper):
    """Scrapes animal pages asynchronously and processes images."""

    def __init__(
            self,
            http_client: AsyncHttpClient,
            http_client_image: AsyncHttpClient,
            db: AnimalsInMemoryDB,
            input_queue: Optional[asyncio.Queue] = None,
            output_queue: Optional[asyncio.Queue] = None,
            max_concurrent_requests: int = 10,
    ):
        super().__init__()
        self._logger = logging.getLogger(__name__)
        self._http_client_animal_page = http_client
        self._http_client_image = http_client_image
        self._db = db
        self._input_queue = input_queue or asyncio.Queue()
        self._output_queue = output_queue or asyncio.Queue()
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)
        self._stop_event = asyncio.Event()

    async def run(self):
        """Ensures the scraper waits for data before processing."""
        self._logger.info("[AnimalPageScraper] Waiting for data in queue...")

        while self._http_client_animal_page.queue.empty():
            self._logger.info("[AnimalPageScraper] Still waiting...")
            await asyncio.sleep(1)

        self._logger.info("[AnimalPageScraper] Data available! Starting processing.")

        async with asyncio.TaskGroup() as tg:
            tg.create_task(self._fetch_animal_pages())
            workers = [tg.create_task(self._page_worker()) for _ in range(10)]
            await self._input_queue.join()
            self._stop_event.set()
            await asyncio.gather(*workers)

        self._logger.info("[AnimalPageScraper] Exiting run()")

    async def _fetch_animal_pages(self):
        """Fetches animal pages and enqueues them for workers."""
        self._logger.info("[AnimalPageScraper] Starting _fetch_animal_pages")

        while not self._stop_event.is_set():
            try:
                results = await self._http_client_animal_page.get_results(batch_size=10)
                if not results:
                    self._logger.warning(
                        "[AnimalPageScraper] No results received, stopping fetch loop."
                    )
                    break

                self._logger.info(
                    "[AnimalPageScraper] Fetched %d animal pages", len(results)
                )

                for url, response in results:
                    if not url or not response:
                        self._logger.warning(
                            "[AnimalPageScraper] Invalid results received: %s", results
                        )
                        continue
                    await self._output_queue.put((url, response))
                    self._input_queue.task_done()

            except asyncio.TimeoutError:
                self._logger.warning("[AnimalPageScraper] Timeout fetching pages")
            except Exception as exc:
                self._logger.error("Error fetching animal page: %s", exc)

        self._logger.info("[AnimalPageScraper] Finished fetching pages, exiting.")

    async def _page_worker(self):
        """Processes animal pages from the queue with retry logic and backoff."""
        self._logger.info("[AnimalPageScraper] Starting _page_worker")

        while not self._stop_event.is_set() or not self._output_queue.empty():
            try:
                item = await asyncio.wait_for(self._output_queue.get(), timeout=2)
            except asyncio.TimeoutError:
                self._logger.warning("[AnimalPageScraper] Timeout waiting for output queue")
                continue

            if not item:
                break

            url, response = item
            self._logger.info("[AnimalPageScraper] Processing %s", url)

            await self._process_page(url, response)
            self._output_queue.task_done()

            self._logger.info("[AnimalPageScraper] Finished processing %s", url)

        self._logger.info("[AnimalPageScraper] Exiting _page_worker")

    async def _process_page(self, url: str, response: str):
        """Processes an individual animal page and fetches the image URL."""
        animal_name = url.split("/")[-1]
        self._logger.info("[AnimalPageScraper] Extracting image of %s", animal_name)
        image_url = await self._extract_image_url(response, animal_name)

        if image_url:
            self._db.insert_image_url(image_url, animal_name)
            asyncio.create_task(self._submit_image(image_url))

    async def _submit_image(self, image_url: str):
        """Handles async submission of images with proper error handling."""
        try:
            await self._http_client_image.submit_urls([image_url], is_image=True)
        except Exception as exc:
            self._logger.error("Failed to submit image URL %s: %s", image_url, exc)

    async def _extract_image_url(self, html_page: str, animal_name: str) -> Optional[str]:
        """Extracts the first available image URL from the page."""
        self._logger.info("Fetching image for %s", animal_name)
        if not html_page:
            return None

        soup = BeautifulSoup(html_page, "html.parser")
        infobox = soup.find("table", {"class": "infobox"})
        image_tag = infobox.find("img") if infobox else None

        if image_tag:
            image_url = "https:" + image_tag.get("src")
            self._logger.info("Found infobox image for %s: %s", animal_name, image_url)
            return image_url

        self._logger.warning("No image found for %s", animal_name)
        return None
