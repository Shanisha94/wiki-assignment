import asyncio
import logging

from bs4 import BeautifulSoup

from client.http_client import AsyncHttpClient
from db.animals_db import AnimalsInMemoryDB
from scraper.web_scraper import WebScraper

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="wiki_scrape.log",
)


class AnimalTableScraper(WebScraper):
    URL = "https://en.wikipedia.org/wiki/List_of_animal_names"
    ANIMAL_COLUMN_INDEX = 0
    COLLATERAL_ADJECTIVE_COLUMN = "Collateral adjective"
    EMPTY_COLUMN = "—"

    def __init__(
        self,
        http_client: AsyncHttpClient,
        db: AnimalsInMemoryDB,
        queue: asyncio.Queue,
        max_concurrent_requests: int = 10,
    ):
        super().__init__()
        self._http_client = http_client
        self._db = db
        self._queue = queue
        self._logger = logging.getLogger(__name__)
        self._semaphore = asyncio.Semaphore(
            max_concurrent_requests
        )  # Limit concurrent requests

    async def run(self):
        """Runs the Wikipedia scraping process."""
        self._logger.info("[AnimalTableScraper] Starting run()")

        soup = await self._fetch_wikipedia_page()
        if soup:
            await self._scrap_animal_table(soup)

        self._logger.info(
            "[AnimalTableScraper] Finished processing, setting stop event."
        )

        self._stop_event.set()  # Ensure this scraper stops

        self._logger.info("[AnimalTableScraper] Exiting run()")

    async def _fetch_wikipedia_page(self):
        """Fetches the Wikipedia page and parses it using BeautifulSoup."""
        self._logger.info("Fetching Wikipedia page")
        try:
            _, response = await self._http_client.fetch(self.URL)

            if not response or response.startswith("Error:"):  # Check for failure
                raise ValueError(f"Failed to retrieve page content: {response}")

            return BeautifulSoup(response, "html.parser")
        except Exception as e:
            self._logger.error(f"Failed to fetch Wikipedia page: {e}")
            return None

    async def _scrap_animal_table(self, soup: BeautifulSoup):
        """Scrape the animal table asynchronously in batches."""
        animals_table = soup.find("table", class_="wikitable sortable sticky-header")
        if not animals_table:
            self._logger.warning("Failed to find the animal table")
            self._stop_event.set()  # Signal that scraping is complete
            return

        headers = [header.text.strip() for header in animals_table.find_all("th")]
        collateral_adjectives_column_index = (
            self._get_collateral_adjectives_column_index(headers)
        )
        if collateral_adjectives_column_index is None:
            self._logger.warning(
                f"Collateral adjectives column '{self.COLLATERAL_ADJECTIVE_COLUMN}' was not found"
            )
            self._stop_event.set()  # Signal completion to avoid indefinite hang
            return

        rows = list(animals_table.find_all("tr"))
        if not rows:
            self._logger.warning("No rows found in animal table")
            self._stop_event.set()
            return

        batch_size = 10  # Process in batches
        for i in range(0, len(rows), batch_size):
            tasks = []
            for row in rows[i : i + batch_size]:
                cells = row.find_all(["td"])
                if len(cells) > collateral_adjectives_column_index:
                    task = asyncio.create_task(
                        self._process_animal_row(
                            cells, collateral_adjectives_column_index
                        )
                    )
                    tasks.append(task)

            if tasks:
                await asyncio.gather(
                    *tasks
                )  # Ensure all tasks complete before moving forward

        self._logger.info("Finished processing animal table")
        self._stop_event.set()  # Ensure the scraper signals completion

    async def _process_animal_row(self, cells, collateral_adjectives_column_index):
        """Processes a single row asynchronously."""
        animal_link = cells[self.ANIMAL_COLUMN_INDEX].find("a")
        if not animal_link:
            return

        animal_name = animal_link.text.strip()
        self._logger.info(f"[AnimalTableScraper] Adding {animal_name} to queue")

        # Extract collateral adjectives
        collateral_adjectives = self._extract_collateral_adjectives(
            cells[collateral_adjectives_column_index]
        )
        for adjective in collateral_adjectives:
            self._db.insert_animal_to_collateral_adjectives(adjective, animal_name)

        # Add animal page URL to queue for `AnimalPageScraper`
        full_url = f"https://en.wikipedia.org/wiki/{animal_name}"
        await self._queue.put((full_url, None))

        async with self._semaphore:
            await self._http_client.submit_urls([full_url])

    def _get_collateral_adjectives_column_index(self, headers: list[str]) -> int | None:
        """Gets the column index for collateral adjectives."""
        return (
            headers.index(self.COLLATERAL_ADJECTIVE_COLUMN)
            if self.COLLATERAL_ADJECTIVE_COLUMN in headers
            else None
        )

    def _extract_collateral_adjectives(self, cell) -> list[str]:
        """Extracts collateral adjectives from a cell."""
        if cell.get_text(strip=True) == self.EMPTY_COLUMN:
            return []
        return [text.strip() for text in cell.stripped_strings if text.strip()]
