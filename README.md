# 🦁 Wiki Assignment

Wiki Assignment is a Python-based web scraper that:
- **Extracts animal names** from the [Wikipedia animal list](https://en.wikipedia.org/wiki/List_of_animal_names).
- **Visits each animal's Wikipedia page** to retrieve additional details.
- **Downloads animal images** from their respective pages.
- **Serves the collected data via a FastAPI web interface.**
- **Provides an API to refresh the data** asynchronously.

## 🚀 Features
✅ **Automated Web Scraping:** Fetches animal names and images from Wikipedia.  
✅ **Image Downloading:** Saves images locally for each animal.  
✅ **FastAPI Web Interface:** Displays animal data in a clean table.  
✅ **Data Refresh API:** Refreshes the dataset without restarting the server.  
✅ **Asynchronous Processing:** Uses Python `asyncio` for concurrent scraping.  

---

## 📌 **Installation**
### **1️⃣ Clone the Repository**
```sh
git clone https://github.com/your-username/wiki-assignment.git
cd wiki-assignment
```
## 2️⃣ Create and Activate a Virtual Environment
```sh
python -m venv venv
source venv/bin/activate  # On macOS/Linux
venv\Scripts\activate     # On Windows
```
## 3️⃣ Install Dependencies
```sh
pip install -r requirements.txt
```
## 🏃 Running the Project
Start the Scraper and Web Server
```sh
python main.py
```
This will:
1. Scrape animal data from Wikipedia.
2. Download images for each animal.
3. Start a FastAPI server at http://127.0.0.1:8000/.

### Access the Web Interface
- Open your browser and visit:
    🔗 http://127.0.0.1:8000/
- The page will display a table of animals with:
  - Animal Names
  - Collateral Adjectives
  - Downloaded Images
  - Local Image Paths

## 🔄 Refreshing Data
If new data is available, trigger a refresh **without restarting the server**.

### Method 1: Click the Refresh Button
Click the "🔄 Refresh Data" button on the homepage.

### Method 2: API Request
Send a POST request to refresh data:

```sh
curl -X POST http://127.0.0.1:8000/refresh
```

This will:
- Clear old data.
- Scrape Wikipedia again.
- Update the database and web page.

## 🔗 API Endpoints
### 1️⃣ Homepage
- `GET /`
- Displays the animal data in an HTML table.

### 2️⃣ Refresh Data
- `POST /refresh`
- Starts a background process to re-scrape Wikipedia.

### 🛠 Project Structure
```graphql
wiki-assignment/
│── db/
│   ├── animals_db.py          # In-memory database for storing animals
│
│── client/
│   ├── http_client.py         # Handles HTTP requests
│
│── scraper/
│   ├── table_scraper.py       # Scrapes animal names from Wikipedia
│   ├── animal_page_scraper.py # Visits animal pages and extracts images
│   ├── file_handler.py        # Downloads images and manages files
│
│── templates/
│   ├── index.html             # Jinja2 template for displaying the web page
│
│── main.py                    # Runs the scraper and starts the FastAPI server
│── requirements.txt            # Required dependencies
│── README.md                   # Project documentation
```

## 🏗 Future Enhancements
🔹 Store scraped data in SQLite/PostgreSQL instead of memory.
🔹 Add a search/filter option in the web interface.
🔹 Implement image caching to avoid redundant downloads.

## 📝 License
This project is licensed under the MIT License.

## ❤️ Contributions
Contributions are welcome! Feel free to submit issues or pull requests.