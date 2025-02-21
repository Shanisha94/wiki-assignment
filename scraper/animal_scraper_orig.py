# import asyncio
# import os
# import tempfile
# from collections import defaultdict
# from pathlib import Path
#
# import aiohttp
# from bs4 import BeautifulSoup
# import logging
#
# # Configure logging
# logging.basicConfig(
#     level=logging.WARNING,
#     format="%(asctime)s - %(levelname)s - %(message)s",
# )
#
#
# class AnimalWebScraper:
#     URL = "https://en.wikipedia.org/wiki/List_of_animal_names"
#     ANIMAL_COLUMN_INDEX = 0
#     COLLATERAL_ADJECTIVE_COLUMN = "Collateral adjective"
#     EMPTY_COLUMN = "—"
#
#     def __init__(self):
#         self._logger = logging.getLogger(__name__)
#         self._collateral_adjectives_to_animals: defaultdict[str, list[str]] = defaultdict(list)  # Collateral adjectives to list of animals
#         self._animal_pictures: defaultdict[str, Path] = defaultdict(None)  # Map animal to its image file path
#         self._session = None  # For async requests
#         self._soup = None  # Cached soup object
#         self._init_soup()
#
#     async def fetch(self, url):
#         """Asynchronous HTTP GET request using aiohttp"""
#         async with self._session.get(url) as response:
#             return await response.text()
#
#     async def _init_soup(self):
#         """Initialize BeautifulSoup for Wikipedia's animal names page"""
#         print("Fetching Wikipedia page")
#         html = await self.fetch(self.URL)
#         self._soup = BeautifulSoup(html, "html.parser")
#
#     async def scrap_animal_table(self):
#         """Scrape the animal table asynchronously"""
#         await self._init_soup()
#         animals_table = self._soup.find("table", class_="wikitable sortable sticky-header")
#         if not animals_table:
#             print("Failed to find the animal table")
#             return
#         headers = [header.text.strip() for header in animals_table.find_all('th')]
#         collateral_adjectives_column_index = self._get_collateral_adjectives_column_index(headers)
#         if collateral_adjectives_column_index is None:
#             print(f"Collateral adjectives column '{self.COLLATERAL_ADJECTIVE_COLUMN}' was not found")
#             return
#         tasks = []
#         for row in animals_table.find_all("tr"):
#             cells = row.find_all(["td"])
#             if len(cells) > collateral_adjectives_column_index:
#                 tasks.append(self._process_animal_row(cells, collateral_adjectives_column_index))
#         await asyncio.gather(*tasks)
#
#     async def _process_animal_row(self, cells, collateral_adjectives_column_index):
#         """Process a single row asynchronously"""
#         animal_link = cells[self.ANIMAL_COLUMN_INDEX].find("a")
#         if not animal_link:
#             return
#         animal_name = animal_link.text.strip()
#         print(f"Processing animal: {animal_name}")
#         collateral_adjectives = self._extract_collateral_adjectives(cells[collateral_adjectives_column_index])
#         for adjective in collateral_adjectives:
#             self._collateral_adjectives_to_animals[adjective].append(animal_name)
#         # Fetch and download image asynchronously
#         file_path = await self._download_image(animal_link.get("href"), animal_name)
#         if file_path:
#             self._animal_pictures[animal_name] = file_path
#
#     def _get_collateral_adjectives_column_index(self, headers: list[str]) -> int | None:
#         return headers.index(self.COLLATERAL_ADJECTIVE_COLUMN) if self.COLLATERAL_ADJECTIVE_COLUMN in headers else None
#
#     def _extract_collateral_adjectives(self, cell) -> list[str]:
#         if cell.get_text(strip=True) == self.EMPTY_COLUMN:
#             return []
#         return [text.strip() for text in cell.stripped_strings if text.strip()]
#
#     async def _download_image(self, relative_url: str, animal_name: str) -> Path | None:
#         print(f"Fetching image for {animal_name}")
#         full_url = f"https://en.wikipedia.org{relative_url}"
#         page_html = await self.fetch(full_url)
#         soup = BeautifulSoup(page_html, "html.parser")
#         # Try infobox first, then fallback to first image
#         image_tag = None
#         infobox = soup.find("table", class_="infobox")
#         if infobox:
#             image_tag = infobox.find("img")
#         if not image_tag:
#             image_tag = soup.find("img", class_="mw-file-element")
#         if not image_tag:
#             printing(f"No image found for {animal_name}")
#             return None
#         image_src = "https:" + image_tag["src"]
#         return await self._save_image_locally(image_src, animal_name)
#
#     async def _save_image_locally(self, image_url, animal_name):
#         print(f"Downloading image: {image_url}")
#         async with self._session.get(image_url) as response:
#             image_data = await response.read()
#         file_path = Path(tempfile.gettempdir(), f"{animal_name}.jpg")
#         if not os.path.isfile(file_path):
#             with open(file_path, "wb") as file:
#                 file.write(image_data)
#             print(f"Image saved at {file_path}")
#         else:
#             print(f"Image already exists at {file_path}")
#         return file_path
#
#
# async def main():
#     async with aiohttp.ClientSession() as session:
#         scraper = AnimalWebScraper()
#         scraper._session = session  # Assign the session
#         await scraper.scrap_animal_table()
#         print("Scraping complete!")
#
# # Run the async scraper
# if __name__ == "__main__":
#     asyncio.run(main())
