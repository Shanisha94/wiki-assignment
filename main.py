# from fastapi import FastAPI, Request
# from fastapi.templating import Jinja2Templates
#
# app = FastAPI()
#
# # Set up Jinja2 template rendering
# templates = Jinja2Templates(directory="templates")
#
# @app.get("/")
# async def display_results(request: Request):
#     scraper = AnimalWebScraper()
#     animal_table = scraper.scrap_animal_table()
#     return templates.TemplateResponse("index.html", {"request": request, "data": animal_table})
import time
import asyncio

from db.animals_db import AnimalsInMemoryDB
from client.http_client import AsyncHttpClient
from scraper.animal_page_scraper import AnimalPageScraper
from scraper.file_handler import FileHandler
from scraper.table_scraper import AnimalTableScraper


async def main():
    start_time = time.perf_counter()

    db = AnimalsInMemoryDB()
    async with AsyncHttpClient() as client, AsyncHttpClient() as client_image:
        table_scraper = AnimalTableScraper(client, db)
        page_scraper = AnimalPageScraper(client, client_image, db)
        file_handler = FileHandler(client_image, db)
        table_task = asyncio.create_task(table_scraper.run())
        page_task = asyncio.create_task(page_scraper.run())
        file_task = asyncio.create_task(file_handler.run())
        await asyncio.sleep(100)
        # await table_scraper.stop()
        # await page_scraper.stop()
        # await file_handler.stop()
        # await table_task
        # await page_task
        # await file_task
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"Execution time: {elapsed_time:.4f} seconds")
    exit()

if __name__ == "__main__":
    asyncio.run(main())