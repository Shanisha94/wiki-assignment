import asyncio
import logging
import threading

import aiohttp
from bs4 import BeautifulSoup
from db.animals_db import AnimalsInMemoryDB
from client.http_client import AsyncHttpClient
import requests
import timeit

from scraper.web_scraper import WebScraper

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

class AnimalTableScraper(WebScraper):
    URL = "https://en.wikipedia.org/wiki/List_of_animal_names"
    ANIMAL_COLUMN_INDEX = 0
    COLLATERAL_ADJECTIVE_COLUMN = "Collateral adjective"
    EMPTY_COLUMN = "—"

    def __init__(self, http_client: AsyncHttpClient, db: AnimalsInMemoryDB):
        super().__init__()
        self._http_client = http_client
        self._db = db
        self._logger = logging.getLogger(__name__)
        self._soup = None

    async def _fetch_wikipedia_page(self):
        print("Fetching Wikipedia page")
        async with aiohttp.ClientSession() as session:
            async with session.get(self.URL) as response:
                html = await response.text()
                self._soup = BeautifulSoup(html, "html.parser")

    async def run(self):
        await self._fetch_wikipedia_page()
        asyncio.create_task(self._scrap_animal_table())

    async def _scrap_animal_table(self):
        """Scrape the animal table asynchronously"""
        animals_table = self._soup.find("table", class_="wikitable sortable sticky-header")
        if not animals_table:
            print("Failed to find the animal table")
            return
        headers = [header.text.strip() for header in animals_table.find_all('th')]
        collateral_adjectives_column_index = self._get_collateral_adjectives_column_index(headers)
        if collateral_adjectives_column_index is None:
            print(f"Collateral adjectives column '{self.COLLATERAL_ADJECTIVE_COLUMN}' was not found")
            return
        rows = list(animals_table.find_all("tr"))
        tasks = []
        for row in rows:
            cells = row.find_all(["td"])
            if len(cells) > collateral_adjectives_column_index:
                task = asyncio.create_task(self._process_animal_row(cells, collateral_adjectives_column_index))
                tasks.append(task)
        # Wait for all tasks to finish per batch to limit memory usage
        await asyncio.gather(*tasks)
        tasks.clear()
        await asyncio.sleep(0.01) # Small delay to avoid excessive CPU usage
        await self._http_client.queue.task_done()

    async def _process_animal_row(self, cells, collateral_adjectives_column_index):
        """Process a single row asynchronously"""
        animal_link = cells[self.ANIMAL_COLUMN_INDEX].find("a")
        if not animal_link:
            return
        animal_name = animal_link.text.strip()
        print(f"Processing animal: {animal_name}")
        collateral_adjectives = self._extract_collateral_adjectives(cells[collateral_adjectives_column_index])
        for adjective in collateral_adjectives:
            self._db.insert_animal_to_collateral_adjectives(adjective, animal_name)
        # Fetch and download image asynchronously
        full_url = f"https://en.wikipedia.org/wiki/{animal_name}"
        await self._http_client.submit_urls([full_url])

    def _get_collateral_adjectives_column_index(self, headers: list[str]) -> int | None:
        return headers.index(self.COLLATERAL_ADJECTIVE_COLUMN) if self.COLLATERAL_ADJECTIVE_COLUMN in headers else None

    def _extract_collateral_adjectives(self, cell) -> list[str]:
        if cell.get_text(strip=True) == self.EMPTY_COLUMN:
            return []
        return [text.strip() for text in cell.stripped_strings if text.strip()]
