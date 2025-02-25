import asyncio
import random
import tempfile
from pathlib import Path
import aiofiles
from db.animals_db import AnimalsInMemoryDB
from client.http_client import AsyncHttpClient
import logging
from scraper.web_scraper import WebScraper


MAX_ATTEMPTS = 5  # Maximum number of retry attempts
INITIAL_BACKOFF = 1  # Initial backoff time in seconds
BACKOFF_MULTIPLIER = 2  # Multiplier for exponential backoff


class FileHandler(WebScraper):
    def __init__(
        self,
        http_client: AsyncHttpClient,
        db: AnimalsInMemoryDB,
        queue=asyncio.Queue(),
        max_concurrent_downloads: int = 10,
    ):
        super().__init__()
        self._http_client = http_client
        self._logger = logging.getLogger(__name__)
        self._db = db
        self._queue = queue
        self._semaphore = asyncio.Semaphore(
            max_concurrent_downloads
        )  # Limit concurrent downloads
        self._existing_images = self.get_existing_images(
            tempfile.gettempdir()
        )  # Use a set for quick lookups

    async def run(self):
        """Ensure FileHandler waits for image URLs before processing."""
        print("[FileHandler] Waiting for data in queue...")
        self._logger.info("[FileHandler] Waiting for data in queue...")

        # Wait until the queue has at least 1 item
        while self._http_client.queue.empty():
            await asyncio.sleep(1)

        print("[FileHandler] Starting processing as data is available")
        self._logger.info("[FileHandler] Starting processing as data is available")

        async with asyncio.TaskGroup() as tg:
            tg.create_task(self._fetch_images())

            workers = [tg.create_task(self._image_worker()) for _ in range(10)]

            await self._queue.join()  # Ensure all queued images are processed

            print("[FileHandler] Queue fully processed, stopping workers...")
            self._logger.info(
                "[FileHandler] Queue fully processed, stopping workers..."
            )

            self._stop_event.set()
            await asyncio.gather(*workers)

        print("[FileHandler] Exiting run()")
        self._logger.info("[FileHandler] Exiting run()")

    async def _fetch_images(self):
        """Fetch images asynchronously in small batches to improve performance."""
        while not self._stop_event.is_set():
            try:
                results = await asyncio.gather(
                    *[
                        self._http_client.get_result() for _ in range(10)
                    ]  # Fetch multiple images at once
                )
                for result in results:
                    await self._queue.put(result)  # Add images to the queue
            except Exception as e:
                self._logger.error(f"Error fetching image: {e}")

    def get_existing_images(self, directory: str) -> set:
        """Retrieve all image filenames in the directory and store them in a set."""
        return {
            file.name for file in Path(directory).glob("*.jpg")
        }  # Store as str for quick lookup

    async def _image_worker(self):
        """Worker that processes image downloads from the queue."""
        attempts = 0
        backoff = INITIAL_BACKOFF

        while not self._stop_event.is_set() or not self._queue.empty():
            try:
                item = await asyncio.wait_for(self._queue.get(), timeout=2)
                attempts = 0  # Reset attempts on success
            except asyncio.TimeoutError:
                attempts += 1
                if attempts >= MAX_ATTEMPTS:
                    logging.error("[FileHandler] Max retry attempts reached, giving up")
                    break
                await asyncio.sleep(backoff + random.uniform(0, 0.5))
                backoff *= BACKOFF_MULTIPLIER
                continue  # Skip the rest of the loop and retry

            await self._save_image_locally(*item)
            self._queue.task_done()

        print("[FileHandler] Exiting _image_worker")
        self._logger.info("[FileHandler] Exiting _image_worker")

    async def _save_image_locally(self, image_url: str, image_data: bytes) -> None:
        """Downloads and saves an image asynchronously with minimal blocking."""
        animal_name = self._db.get_animal_name_by_url(image_url)
        if not animal_name:
            self._logger.warning(
                f"Could not find animal name for image url: {image_url}"
            )
            return

        local_file_path = Path(tempfile.gettempdir(), f"{animal_name}.jpg")

        # Faster existence check
        if local_file_path.name in self._existing_images:
            self._logger.info(f"Image already exists at {local_file_path}")
            return

        async with self._semaphore:
            await self._write_file(local_file_path, image_data)

        self._db.insert_image_local_path(animal_name, str(local_file_path))

    async def _write_file(self, file_path: Path, file_data: bytes):
        """Writes file asynchronously to avoid blocking I/O."""
        try:
            async with aiofiles.open(file_path, "wb") as file:
                await file.write(file_data)
            self._logger.info(f"Image saved at {file_path}")
        except Exception as e:
            self._logger.error(f"Failed to save image {file_path}: {e}")
