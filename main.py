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
from scraper.expedia_scraper import ExpediaScraper
from scraper.agoda_scraper import AgodaScraper
from scraper.tourhq_scraper import TourHQScraper
from scraper.toursbylocals_scraper import ToursByLocalsScraper
from scraper.local_directory_scraper import LocalDirectoryScraper
from scraper.tripadvisor_guide_scraper import TripAdvisorGuideScraper
from scraper.post_process import deduplicate_and_filter

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

        try:
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
                try:
                    data = gm_scraper.search_arbaminch_services(service)
                    all_data.extend(data)
                    logger.info(f"  -> Got {len(data)} results")
                except Exception as e:
                    logger.error(f"  -> Error scraping {service}: {e}")
                time.sleep(3)
        except Exception as e:
            logger.error(f"Error in Google Maps scraping phase: {e}")

        # == 2. TripAdvisor ==================================================
        logger.info("-" * 40)
        logger.info("PHASE 2: TripAdvisor")
        logger.info("-" * 40)

        try:
            ta_scraper = TripAdvisorScraper(driver=driver)

            logger.info("Scraping hotels from TripAdvisor...")
            try:
                hotels = ta_scraper.scrape_arbaminch_hotels()
                all_data.extend(hotels)
                logger.info(f"  -> Got {len(hotels)} hotels")
            except Exception as e:
                logger.error(f"  -> Error scraping hotels: {e}")
            time.sleep(3)

            logger.info("Scraping restaurants from TripAdvisor...")
            try:
                restaurants = ta_scraper.scrape_arbaminch_restaurants()
                all_data.extend(restaurants)
                logger.info(f"  -> Got {len(restaurants)} restaurants")
            except Exception as e:
                logger.error(f"  -> Error scraping restaurants: {e}")
            time.sleep(3)

            logger.info("Scraping attractions from TripAdvisor...")
            try:
                attractions = ta_scraper.scrape_arbaminch_things_to_do()
                all_data.extend(attractions)
                logger.info(f"  -> Got {len(attractions)} attractions")
            except Exception as e:
                logger.error(f"  -> Error scraping attractions: {e}")
        except Exception as e:
            logger.error(f"Error in TripAdvisor scraping phase: {e}")

        # == 3. Booking.com ==================================================
        logger.info("-" * 40)
        logger.info("PHASE 3: Booking.com")
        logger.info("-" * 40)

        try:
            booking_scraper = BookingScraper(driver=driver)

            logger.info("Scraping accommodations from Booking.com...")
            try:
                accommodations = booking_scraper.scrape_arbaminch_accommodations()
                all_data.extend(accommodations)
                logger.info(f"  -> Got {len(accommodations)} accommodations")
            except Exception as e:
                logger.error(f"  -> Error scraping accommodations: {e}")
        except Exception as e:
            logger.error(f"Error in Booking.com scraping phase: {e}")

        # == 4. Expedia ======================================================
        logger.info("-" * 40)
        logger.info("PHASE 4: Expedia")
        logger.info("-" * 40)

        try:
            expedia_scraper = ExpediaScraper(driver=driver)

            logger.info("Scraping hotels from Expedia...")
            try:
                hotels = expedia_scraper.scrape_arbaminch_hotels()
                all_data.extend(hotels)
                logger.info(f"  -> Got {len(hotels)} hotels")
            except Exception as e:
                logger.error(f"  -> Error scraping hotels: {e}")
        except Exception as e:
            logger.error(f"Error in Expedia scraping phase: {e}")

        # == 5. Agoda =========================================================
        logger.info("-" * 40)
        logger.info("PHASE 5: Agoda")
        logger.info("-" * 40)

        try:
            agoda_scraper = AgodaScraper(driver=driver)

            logger.info("Scraping hotels from Agoda...")
            try:
                hotels = agoda_scraper.scrape_arbaminch_hotels()
                all_data.extend(hotels)
                logger.info(f"  -> Got {len(hotels)} hotels")
            except Exception as e:
                logger.error(f"  -> Error scraping hotels: {e}")
        except Exception as e:
            logger.error(f"Error in Agoda scraping phase: {e}")

        # == 6. Tour Guides - tourHQ ==========================================
        logger.info("-" * 40)
        logger.info("PHASE 6: tourHQ (Tour Guides)")
        logger.info("-" * 40)

        try:
            tourhq_scraper = TourHQScraper(driver=driver)

            logger.info("Scraping tour guides from tourHQ...")
            try:
                guides = tourhq_scraper.scrape_arbaminch_guides()
                all_data.extend(guides)
                logger.info(f"  -> Got {len(guides)} tour guides")
            except Exception as e:
                logger.error(f"  -> Error scraping tour guides: {e}")
        except Exception as e:
            logger.error(f"Error in tourHQ scraping phase: {e}")

        # == 7. Tour Guides - ToursByLocals ===================================
        logger.info("-" * 40)
        logger.info("PHASE 7: ToursByLocals (Tour Guides)")
        logger.info("-" * 40)

        try:
            tbl_scraper = ToursByLocalsScraper(driver=driver)

            logger.info("Scraping tour guides from ToursByLocals...")
            try:
                guides = tbl_scraper.scrape_arbaminch_guides()
                all_data.extend(guides)
                logger.info(f"  -> Got {len(guides)} tour guides")
            except Exception as e:
                logger.error(f"  -> Error scraping tour guides: {e}")
        except Exception as e:
            logger.error(f"Error in ToursByLocals scraping phase: {e}")

        # == 8. Tour Guides - TripAdvisor =====================================
        logger.info("-" * 40)
        logger.info("PHASE 8: TripAdvisor (Tour Guides)")
        logger.info("-" * 40)

        try:
            ta_guide_scraper = TripAdvisorGuideScraper(driver=driver)

            logger.info("Scraping tour guides from TripAdvisor...")
            try:
                guides = ta_guide_scraper.scrape_arbaminch_guides()
                all_data.extend(guides)
                logger.info(f"  -> Got {len(guides)} tour guides")
            except Exception as e:
                logger.error(f"  -> Error scraping tour guides: {e}")
        except Exception as e:
            logger.error(f"Error in TripAdvisor guide scraping phase: {e}")

        # == 9. Arba Minch Local Directory ===================================
        logger.info("-" * 40)
        logger.info("PHASE 9: Arba Minch Local Directory")
        logger.info("-" * 40)

        try:
            local_dir_scraper = LocalDirectoryScraper(driver=driver)

            logger.info("Scraping all categories from Local Directory...")
            try:
                businesses = local_dir_scraper.scrape_all_categories()
                all_data.extend(businesses)
                logger.info(f"  -> Got {len(businesses)} businesses")
            except Exception as e:
                logger.error(f"  -> Error scraping local directory: {e}")
        except Exception as e:
            logger.error(f"Error in Local Directory scraping phase: {e}")

    finally:
        logger.info("Closing browser...")
        driver.quit()

    # == Post-process: deduplicate & filter ====================================
    if all_data:
        logger.info("-" * 40)
        logger.info("POST-PROCESSING")
        logger.info("-" * 40)
        
        # Load existing cleaned data and merge with new data
        from scraper.post_process import load_existing_cleaned_data
        existing_data = load_existing_cleaned_data()
        
        # Process new data (will skip entries already in existing_data, but merge new sources)
        new_cleaned_data, updated_existing = deduplicate_and_filter(all_data, existing_data)
        
        # Merge existing and new data
        if existing_data:
            # Update existing entries with new sources
            existing_list = []
            for key, entry in existing_data.items():
                if key in updated_existing:
                    # Merge new sources into existing entry
                    existing_sources = entry.get('sources', {})
                    new_sources = updated_existing[key].get('sources', {})
                    existing_sources.update(new_sources)
                    entry['sources'] = existing_sources
                    # Merge types
                    existing_types = set(entry.get('types', []))
                    new_types = set(updated_existing[key].get('types', []))
                    entry['types'] = sorted(list(existing_types | new_types))
                existing_list.append(entry)
            
            # Combine with new data
            all_data = existing_list + new_cleaned_data
            logger.info(f"  Updated {len(updated_existing)} existing entries with new sources")
            logger.info(f"  Merged {len(existing_list)} existing + {len(new_cleaned_data)} new = {len(all_data)} total entries")
        else:
            all_data = new_cleaned_data
            logger.info(f"  Created {len(all_data)} new entries (no existing data)")

    # == Save data ============================================================
    if all_data:
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        # JSON
        json_path = f"data/arbaminch_tourism_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved JSON -> {json_path}")

        # CSV - flatten the sources structure for easier viewing
        csv_rows = []
        for rec in all_data:
            row = {
                'name': rec.get('name', ''),
                'types': ', '.join(rec.get('types', [])),
                'categories': ', '.join(rec.get('categories', [])) if rec.get('categories') else '',
            }
            # Flatten sources into columns
            sources = rec.get('sources', {})
            for src_name, src_info in sources.items():
                prefix = src_name.replace('.', '').replace(' ', '_')
                row[f'{prefix}_link'] = src_info.get('link', '')
                row[f'{prefix}_rating'] = src_info.get('rating', '')
                if src_info.get('price'):
                    row[f'{prefix}_price'] = src_info['price']
                if src_info.get('review_score'):
                    row[f'{prefix}_review_score'] = src_info['review_score']
                if src_info.get('address'):
                    row[f'{prefix}_address'] = src_info['address']
            csv_rows.append(row)
        
        df = pd.DataFrame(csv_rows)
        csv_path = f"data/arbaminch_tourism_{timestamp}.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8')
        logger.info(f"Saved CSV  -> {csv_path}")

        logger.info("=" * 60)
        logger.info(f"DONE! Total records scraped: {len(all_data)}")
        logger.info("=" * 60)
    else:
        logger.warning("No data was scraped!")


if __name__ == "__main__":
    main()
