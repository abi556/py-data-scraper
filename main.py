import logging
import json
import os
import sys
import pandas as pd
import time
from scraper.base_scraper import create_driver
from scraper.google_maps_scraper import GoogleMapsScraper
from scraper.tripadvisor_scraper import TripAdvisorScraper
from scraper.booking_scraper import BookingScraper

# Fix Windows console encoding for special characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Main")


def main():
    logger.info("=" * 60)
    logger.info("Starting Arba Minch Tourism Scraper")
    logger.info("=" * 60)

    # Create output directory
    os.makedirs("data", exist_ok=True)

    all_data = []

    # Create a SINGLE shared browser (English forced)
    logger.info("Launching Chrome browser (English)...")
    driver = create_driver(headless=False)

    try:
        # == 1. Google Maps ==================================================
        logger.info("-" * 40)
        logger.info("PHASE 1: Google Maps")
        logger.info("-" * 40)

        gm_scraper = GoogleMapsScraper(driver=driver)

        service_types = [
            'hotels',
            'motels',
            'resorts',
            'lodges',
            'guest house',
            'restaurants',
            'tour agency',
            'car rental',
            'boat rental',
            'helicopter ride',
        ]

        for service in service_types:
            logger.info(f"Scraping '{service}' from Google Maps...")
            data = gm_scraper.search_arbaminch_services(service)
            all_data.extend(data)
            logger.info(f"  -> Got {len(data)} results")
            time.sleep(3)

        # == 2. TripAdvisor ==================================================
        logger.info("-" * 40)
        logger.info("PHASE 2: TripAdvisor")
        logger.info("-" * 40)

        ta_scraper = TripAdvisorScraper(driver=driver)

        logger.info("Scraping hotels from TripAdvisor...")
        hotels = ta_scraper.scrape_arbaminch_hotels()
        all_data.extend(hotels)
        logger.info(f"  -> Got {len(hotels)} hotels")
        time.sleep(3)

        logger.info("Scraping restaurants from TripAdvisor...")
        restaurants = ta_scraper.scrape_arbaminch_restaurants()
        all_data.extend(restaurants)
        logger.info(f"  -> Got {len(restaurants)} restaurants")
        time.sleep(3)

        logger.info("Scraping attractions from TripAdvisor...")
        attractions = ta_scraper.scrape_arbaminch_things_to_do()
        all_data.extend(attractions)
        logger.info(f"  -> Got {len(attractions)} attractions")

        # == 3. Booking.com ==================================================
        logger.info("-" * 40)
        logger.info("PHASE 3: Booking.com")
        logger.info("-" * 40)

        booking_scraper = BookingScraper(driver=driver)

        logger.info("Scraping accommodations from Booking.com...")
        accommodations = booking_scraper.scrape_arbaminch_accommodations()
        all_data.extend(accommodations)
        logger.info(f"  -> Got {len(accommodations)} accommodations")

    except Exception as e:
        logger.error(f"Unexpected error during scraping: {e}")
    finally:
        logger.info("Closing browser...")
        driver.quit()

    # == Save data ============================================================
    if all_data:
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        # JSON
        json_path = f"data/arbaminch_tourism_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved JSON -> {json_path}")

        # CSV
        csv_path = f"data/arbaminch_tourism_{timestamp}.csv"
        df = pd.DataFrame(all_data)
        preferred_cols = ['name', 'type', 'category', 'rating', 'price', 'address',
                          'review_score', 'link', 'source', 'reviews', 'cuisine']
        existing = [c for c in preferred_cols if c in df.columns]
        remaining = [c for c in df.columns if c not in preferred_cols]
        df = df[existing + remaining]
        df.to_csv(csv_path, index=False, encoding='utf-8')
        logger.info(f"Saved CSV  -> {csv_path}")

        logger.info("=" * 60)
        logger.info(f"DONE! Total records scraped: {len(all_data)}")
        logger.info("=" * 60)
    else:
        logger.warning("No data was scraped!")


if __name__ == "__main__":
    main()
