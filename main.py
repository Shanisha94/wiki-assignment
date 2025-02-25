import asyncio
import time
import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.templating import Jinja2Templates

from db.animals_db import AnimalsInMemoryDB
from client.http_client import AsyncHttpClient
from scraper.animal_page_scraper import AnimalPageScraper
from scraper.file_handler import FileHandler
from scraper.table_scraper import AnimalTableScraper

# Initialize FastAPI app and templates
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Shared database instance
db = AnimalsInMemoryDB()


async def scrape_data():
    """Runs the web scraper to populate the database."""
    print("Starting data scraping...")

    queue_animals_pages = asyncio.Queue()
    queue_images = asyncio.Queue()

    start_time = time.perf_counter()

    # Clear old data before re-scraping
    global db
    db = AnimalsInMemoryDB()  # Reset DB instance

    async with AsyncHttpClient() as client, AsyncHttpClient() as client_image:
        print("Created HTTP clients")

        table_scraper = AnimalTableScraper(client, db, queue_animals_pages)
        page_scraper = AnimalPageScraper(
            client, client_image, db, queue_animals_pages, queue_images
        )
        file_handler = FileHandler(client_image, db, queue_images)

        print("Initialized scrapers")

        async with asyncio.TaskGroup() as tg:
            tg.create_task(table_scraper.run())
            tg.create_task(page_scraper.run())
            tg.create_task(file_handler.run())

    db.get_all_data()
    end_time = time.perf_counter()
    print(f"Scraping complete. Execution time: {end_time - start_time:.4f} seconds")


@app.get("/")
async def homepage(request: Request):
    """Renders the HTML page with scraped data."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "adjective_to_animals": db._collateral_adjectives_to_animals,
            "animal_images": db._animal_image_urls,
            "local_paths": db._animal_images_local_paths,
        },
    )


@app.post("/refresh")
async def refresh_data(background_tasks: BackgroundTasks):
    """
    API endpoint to trigger a fresh data scrape.
    - Runs scraping in the background.
    - Returns an immediate response while the data refreshes.
    """
    background_tasks.add_task(asyncio.run, scrape_data())  # Runs asynchronously
    return {"message": "Data refresh started! Check back in a few minutes."}


async def main():
    """Runs the scraper and then starts the web server."""
    await scrape_data()  # First, scrape and populate the database

    print("Starting FastAPI server on http://127.0.0.1:8000")
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
