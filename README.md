# Arba Minch Tourism Scraper

This project scrapes tourism data (hotels, restaurants, etc.) from Google Maps, TripAdvisor, and Booking.com for Arba Minch, Ethiopia.

## Prerequisites

1. Python 3.8+
2. Google Chrome installed (for Selenium)

## Setup

1. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r scraper/requirements.txt
   ```

## Usage

Run the main script to scrape all sources:

```bash
python main.py
```

The data will be saved in the `data/` directory as JSON and CSV files.

## Project Structure

- `scraper/`: Contains the scraping logic
  - `base_scraper.py`: Shared functionality
  - `google_maps_scraper.py`: Selenium-based scraper for Google Maps
  - `tripadvisor_scraper.py`: Requests/BeautifulSoup scraper for TripAdvisor
  - `booking_scraper.py`: Requests/BeautifulSoup scraper for Booking.com
- `main.py`: Entry point script
- `data/`: Output directory for scraped data
