import asyncio
import shutil
import tempfile
from io import BytesIO
from pathlib import Path
from db.animals_db import AnimalsInMemoryDB
from client.http_client import AsyncHttpClient
import logging
from scraper.web_scraper import WebScraper


class FileHandler(WebScraper):
    def __init__(self, http_client: AsyncHttpClient, db: AnimalsInMemoryDB, max_concurrent_downloads: int = 10):
        super().__init__()
        self._http_client = http_client
        self._logger = logging.getLogger(__name__)
        self._existing_images = self.get_images_with_prefix(tempfile.gettempdir())
        self._db = db
        self._queue = asyncio.Queue()  # Task queue for images
        self._semaphore = asyncio.Semaphore(max_concurrent_downloads)  # Limit concurrent downloads

    async def run(self):
        """Starts the image processing loop"""
        asyncio.create_task(self._fetch_images())
        workers = [asyncio.create_task(self._image_worker()) for _ in range(10)]
        await asyncio.gather(*workers)

    async def _fetch_images(self):
        """Fetch images in batches and queue them for processing."""
        while not self._stop_event.is_set():
            try:
                result = await self._http_client.get_result()
                url, response = result
                await self._queue.put((url, response))  # Add to queue
            except Exception as e:
                self._logger.error(f"Error fetching image: {e}")

            await asyncio.sleep(0.01)  # Small delay to prevent CPU overload

    def get_images_with_prefix(self, directory: str) -> set:
        """Retrieve all image files with a given prefix and store them in a set."""
        return {file for file in Path(directory).glob("*.jpg")}

    async def _image_worker(self):
        """Worker that processes image downloads from the queue."""
        while not self._stop_event.is_set():
            url, response = await self._queue.get()
            await self._save_image_locally(response, url)
            self._queue.task_done()  # Mark task as complete

    async def _save_image_locally(self, image_data: bytes, image_url: str) -> None:
        """Downloads and saves an image."""
        animal_name = self._db.get_animal_name_by_url(image_url)
        if not animal_name:
            print(f"Could not find animal name for image url: {image_url}")
            return

        local_file_path = Path(tempfile.gettempdir(), f"{animal_name}.jpg")
        if local_file_path not in self._existing_images:
            async with self._semaphore:
                await self._write_file(local_file_path, image_data)
        else:
            print(f"Image already exists at {local_file_path}")

        self._db.insert_image_local_path(animal_name, str(local_file_path))

    async def _write_file(self, file_path: Path, file_data: bytes):
        """Writes file asynchronously to avoid blocking."""
        await asyncio.to_thread(self._sync_write_file, file_path, file_data)
        print(f"Image saved at {file_path}")

    def _sync_write_file(self, file_path: Path, file_data: bytes):
        """Blocking file write operation."""
        with open(file_path, "wb") as file:
            file.write(file_data)