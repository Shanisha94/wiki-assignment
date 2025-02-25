import asyncio
import logging
import random

from bs4 import BeautifulSoup
from db.animals_db import AnimalsInMemoryDB
from client.http_client import AsyncHttpClient
from scraper.web_scraper import WebScraper

MAX_ATTEMPTS = 5  # Maximum number of retry attempts
INITIAL_BACKOFF = 1  # Initial backoff time in seconds
BACKOFF_MULTIPLIER = 2  # Multiplier for exponential backoff


class AnimalPageScraper(WebScraper):
    def __init__(self, http_client: AsyncHttpClient, http_client_image: AsyncHttpClient, db: AnimalsInMemoryDB, input_queue = asyncio.Queue(), output_queue = asyncio.Queue(),
                 max_concurrent_requests: int = 10):
        super().__init__()
        self._logger = logging.getLogger(__name__)
        self._http_client_animal_page = http_client
        self._http_client_image = http_client_image
        self._db = db
        self._input_queue = input_queue
        self._output_queue = output_queue
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)
        self._stop_event = asyncio.Event()  # Ensuring stop signal for workers

    async def run(self):
        """Ensure the scraper waits for data before processing."""
        print("[AnimalPageScraper] Waiting for data in queue...")
        self._logger.info("[AnimalPageScraper] Waiting for data in queue...")

        while self._http_client_animal_page.queue.empty():
            print("[AnimalPageScraper] Still waiting...")
            await asyncio.sleep(1)

        print("[AnimalPageScraper] Data available! Starting processing.")
        self._logger.info("[AnimalPageScraper] Data available! Starting processing.")

        async with asyncio.TaskGroup() as tg:
            tg.create_task(self._fetch_animal_pages())

            workers = [tg.create_task(self._page_worker()) for _ in range(10)]

            await self._input_queue.join()

            print("[AnimalPageScraper] Queue fully processed, stopping workers...")
            self._logger.info("[AnimalPageScraper] Queue fully processed, stopping workers...")

            self._stop_event.set()
            self._logger.info("[AnimalPageScraper] Stop event set, awaiting workers...")
            await asyncio.gather(*workers)
            self._logger.info("[AnimalPageScraper] Workers stopped.")

        print("[AnimalPageScraper] Exiting run()")
        self._logger.info("[AnimalPageScraper] Exiting run()")

    async def _fetch_animal_pages(self):
        """Fetches animal pages and enqueues them for workers."""
        print("[AnimalPageScraper] Starting _fetch_animal_pages")
        self._logger.info("[AnimalPageScraper] Starting _fetch_animal_pages")

        while not self._stop_event.is_set():
            try:
                # Fetch batch of results
                results = await self._http_client_animal_page.get_results(batch_size=10)

                if not results:
                    print("[AnimalPageScraper] No results received, stopping fetch loop.")
                    self._logger.warning("[AnimalPageScraper] No results received, stopping fetch loop.")
                    break  # Stop if no more results are available

                print(f"[AnimalPageScraper] Fetched {len(results)} animal pages")
                self._logger.info(f"[AnimalPageScraper] Fetched {len(results)} animal pages")

                # Debug what we received
                for result in results:
                    if not result or len(result) < 2:
                        print(f"[AnimalPageScraper] Invalid result received: {result}")
                        continue  # Skip bad results

                    url, response = result
                    print(f"[AnimalPageScraper] Adding {url} to queue")
                    await self._output_queue.put((url, response))  # **Ensure tasks are enqueued!**
                    self._input_queue.task_done()

            except Exception as e:
                self._logger.error(f"Error fetching animal page: {e}")
                print(f"[AnimalPageScraper] Error: {e}")

        print("[AnimalPageScraper] Finished fetching pages, exiting.")
        self._logger.info("[AnimalPageScraper] Finished fetching pages, exiting.")

    async def _page_worker(self):
        """Processes animal pages from the queue with retry logic and backoff."""
        print("[AnimalPageScraper] Starting _page_worker")
        self._logger.info("[AnimalPageScraper] Starting _page_worker")

        attempts = 0
        backoff = INITIAL_BACKOFF

        while not self._stop_event.is_set() or not self._output_queue.empty():
            try:
                item = await asyncio.wait_for(self._output_queue.get(), timeout=2)
                attempts = 0  # Reset attempts on success
            except asyncio.TimeoutError:
                logging.warning(
                    f"[AnimalPageScraper] Timeout waiting for output queue, attempt {attempts + 1}/{MAX_ATTEMPTS}"
                )
                attempts += 1
                if attempts >= MAX_ATTEMPTS:
                    logging.error("[AnimalPageScraper] Max retry attempts reached, giving up")
                    break
                await asyncio.sleep(backoff + random.uniform(0, 0.5))
                backoff *= BACKOFF_MULTIPLIER
                continue  # Skip the rest of the loop and retry

            if item is None:
                break  # Ensure worker exits if no more items

            url, response = item

            print(f"[AnimalPageScraper] Processing {url}")
            self._logger.info(f"[AnimalPageScraper] Processing {url}")

            await self._process_page(url, response)

            self._output_queue.task_done()  # Call task_done() only after successfully processing

            print(f"[AnimalPageScraper] Finished processing {url}")
            self._logger.info(f"[AnimalPageScraper] Finished processing {url}")

        print("[AnimalPageScraper] Exiting _page_worker")
        self._logger.info("[AnimalPageScraper] Exiting _page_worker")

    async def _process_page(self, url: str, response: str):
        """Processes an individual animal page and fetches the image URL."""
        animal_name = url.split('/')[-1]
        self._logger.info(f"[AnimalPageScraper] Extracting image of {animal_name}")
        image_url = await self._extract_image_url(response, animal_name)

        if image_url:
            self._db.insert_image_url(image_url, animal_name)
            asyncio.create_task(self._submit_image(image_url))  # Non-blocking

    async def _submit_image(self, image_url: str):
        """Handles async submission of images with proper error handling."""
        try:
            await self._http_client_image.submit_urls([image_url], is_image=True)
        except Exception as e:
            self._logger.error(f"Failed to submit image URL {image_url}: {e}")

    async def _extract_image_url(self, html_page: str, animal_name: str) -> str | None:
        """Extracts the first available image URL from the page."""
        self._logger.info(f"Fetching image for {animal_name}")
        image_tag = None
        if html_page:
            soup = BeautifulSoup(html_page, "html.parser")
            infobox = soup.find("table", {"class": "infobox"})
            if infobox:
                image_tag = infobox.find("img")
                if image_tag:
                    image_url = "https:" + image_tag.get("src")
                    self._logger.info(f"Found infobox image for {animal_name}: {image_url}")
                    return image_url

            if not image_tag:
                self._logger.warning(f"No image found for {animal_name}")
                return None

        return "https:" + image_tag.get("src")

