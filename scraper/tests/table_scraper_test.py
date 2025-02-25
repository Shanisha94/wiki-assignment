import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from bs4 import BeautifulSoup

from client.http_client import AsyncHttpClient
from db.animals_db import AnimalsInMemoryDB
from scraper.table_scraper import AnimalTableScraper


@pytest.fixture
def mock_http_client():
    """Fixture for creating a mocked HTTP client."""
    client = AsyncMock(spec=AsyncHttpClient)
    return client


@pytest.fixture
def mock_db():
    """Fixture for creating a mocked in-memory database."""
    db = MagicMock(spec=AnimalsInMemoryDB)
    return db


@pytest.fixture
def mock_queue():
    """Fixture for creating an asyncio queue."""
    return asyncio.Queue()


@pytest.fixture
def scraper(mock_http_client, mock_db, mock_queue):
    """Fixture to create an instance of the scraper."""
    return AnimalTableScraper(mock_http_client, mock_db, mock_queue)


@pytest.mark.asyncio
async def test_fetch_wikipedia_page_success(scraper, mock_http_client):
    """Test successfully fetching and parsing the Wikipedia page."""
    mock_html = "<html><body><table class='wikitable sortable sticky-header'></table></body></html>"
    mock_http_client.fetch.return_value = (
        "https://en.wikipedia.org/wiki/List_of_animal_names",
        mock_html,
    )

    soup = await scraper._fetch_wikipedia_page()
    assert isinstance(soup, BeautifulSoup)
    assert soup.find("table", class_="wikitable sortable sticky-header") is not None


@pytest.mark.asyncio
async def test_fetch_wikipedia_page_failure(scraper, mock_http_client):
    """Test handling a failed HTTP request."""
    mock_http_client.fetch.return_value = (
        "https://en.wikipedia.org/wiki/List_of_animal_names",
        "Error: Timeout",
    )

    soup = await scraper._fetch_wikipedia_page()
    assert soup is None


@pytest.mark.asyncio
async def test_scrap_animal_table_no_table(scraper):
    """Test handling when no animal table is found in the page."""
    soup = BeautifulSoup(
        "<html><body><p>No table here</p></body></html>", "html.parser"
    )

    await scraper._scrap_animal_table(soup)
    assert scraper._stop_event.is_set()  # Ensure scraper stops if table is missing


@pytest.mark.asyncio
async def test_scrap_animal_table_no_collateral_adjective_column(scraper):
    """Test handling when the collateral adjectives column is missing."""
    html = """
    <html>
    <body>
        <table class="wikitable sortable sticky-header">
            <tr><th>Animal</th><th>Something Else</th></tr>
            <tr><td><a href='/wiki/Lion'>Lion</a></td><td>Roaring</td></tr>
        </table>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")

    await scraper._scrap_animal_table(soup)
    assert scraper._stop_event.is_set()


@pytest.mark.asyncio
async def test_process_animal_row(scraper, mock_db, mock_queue):
    """Test extracting and processing an animal row."""
    html = """
    <tr>
        <td><a href='/wiki/Tiger'>Tiger</a></td>
        <td>Feline</td>
    </tr>
    """
    row_soup = BeautifulSoup(html, "html.parser")
    cells = row_soup.find_all("td")

    await scraper._process_animal_row(cells, 1)

    # Check database insertion
    mock_db.insert_animal_to_collateral_adjectives.assert_called_with("Feline", "Tiger")

    # Check queue insertion
    queued_item = await mock_queue.get()
    assert queued_item == ("https://en.wikipedia.org/wiki/Tiger", None)


@pytest.mark.asyncio
async def test_process_animal_row_missing_animal(scraper, mock_db, mock_queue):
    """Test handling a row without a valid animal link."""
    html = """
    <tr>
        <td>No link</td>
        <td>Furry</td>
    </tr>
    """
    row_soup = BeautifulSoup(html, "html.parser")
    cells = row_soup.find_all("td")

    await scraper._process_animal_row(cells, 1)

    # Ensure nothing was added to the database or queue
    mock_db.insert_animal_to_collateral_adjectives.assert_not_called()
    assert mock_queue.empty()


@pytest.mark.asyncio
async def test_get_collateral_adjectives_column_index(scraper):
    """Test finding the correct column index for collateral adjectives."""
    headers = ["Animal", "Type", "Collateral adjective", "Region"]
    index = scraper._get_collateral_adjectives_column_index(headers)
    assert index == 2


@pytest.mark.asyncio
async def test_get_collateral_adjectives_column_index_not_found(scraper):
    """Test when the collateral adjective column is missing."""
    headers = ["Animal", "Type", "Region"]
    index = scraper._get_collateral_adjectives_column_index(headers)
    assert index is None


@pytest.mark.asyncio
async def test_extract_collateral_adjectives_empty(scraper):
    """Test extracting collateral adjectives from an empty cell."""
    html = "<td>—</td>"
    cell = BeautifulSoup(html, "html.parser").td

    adjectives = scraper._extract_collateral_adjectives(cell)
    assert adjectives == []
