"""
Separate scraper for specific sites only:
- Arba Minch Local Directory (specific pages)
- ToursByLocals
- GoWithGuide

This scraper does NOT scrape Google Maps, TripAdvisor, Booking.com, etc.
"""
import logging
import json
import os
import sys
import pandas as pd
import time
from scraper.base_scraper import create_driver
from scraper.local_directory_scraper import LocalDirectoryScraper
from scraper.toursbylocals_scraper import ToursByLocalsScraper
from scraper.gowithguide_scraper import GoWithGuideScraper
from scraper.post_process import deduplicate_and_filter, load_existing_cleaned_data

# Fix Windows console encoding for special characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper_specific.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SpecificScraper")


def main():
    logger.info("=" * 60)
    logger.info("Starting Specific Sites Scraper (Local Directory, ToursByLocals, GoWithGuide)")
    logger.info("=" * 60)

    # Create output directory
    os.makedirs("data", exist_ok=True)

    all_data = []

    # Create a SINGLE shared browser (English forced)
    logger.info("Launching Chrome browser (English)...")
    driver = create_driver(headless=False)

    try:
        # == 1. Arba Minch Local Directory ====================================
        logger.info("-" * 40)
        logger.info("PHASE 1: Arba Minch Local Directory")
        logger.info("-" * 40)

        try:
            local_dir_scraper = LocalDirectoryScraper(driver=driver)

            # Specific URLs to scrape
            local_dir_urls = [
                "https://arbaminchlocaldirectory.com/hotels/",
                "https://arbaminchlocaldirectory.com/restaurants/",
                "https://arbaminchlocaldirectory.com/lodges-resorts/",
                "https://arbaminchlocaldirectory.com/guest-houses-pensions/",
                "https://arbaminchlocaldirectory.com/travel-agencies-tour-guides/",
                "https://arbaminchlocaldirectory.com/auto-services/",
                "https://arbaminchlocaldirectory.com/health-medical/",
            ]

            logger.info("Scraping specific pages from Local Directory...")
            try:
                businesses = local_dir_scraper.scrape_specific_pages(local_dir_urls)
                all_data.extend(businesses)
                logger.info(f"  -> Got {len(businesses)} businesses")
            except Exception as e:
                logger.error(f"  -> Error scraping local directory: {e}")
        except Exception as e:
            logger.error(f"Error in Local Directory scraping phase: {e}")

        # == 2. ToursByLocals =================================================
        logger.info("-" * 40)
        logger.info("PHASE 2: ToursByLocals")
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

        # == 3. GoWithGuide ====================================================
        logger.info("-" * 40)
        logger.info("PHASE 3: GoWithGuide")
        logger.info("-" * 40)

        try:
            gwg_scraper = GoWithGuideScraper(driver=driver)

            logger.info("Scraping tour guides from GoWithGuide...")
            try:
                guides = gwg_scraper.scrape_arbaminch_guides()
                all_data.extend(guides)
                logger.info(f"  -> Got {len(guides)} tour guides")
            except Exception as e:
                logger.error(f"  -> Error scraping tour guides: {e}")
        except Exception as e:
            logger.error(f"Error in GoWithGuide scraping phase: {e}")

    finally:
        logger.info("Closing browser...")
        driver.quit()

    # == Post-process: deduplicate & filter ====================================
    if all_data:
        logger.info("-" * 40)
        logger.info("POST-PROCESSING")
        logger.info("-" * 40)
        
        # Load existing cleaned data and merge with new data
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
        json_path = f"data/arbaminch_specific_sites_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved JSON -> {json_path}")

        # Also update the cleaned JSON
        cleaned_json_path = "data/arbaminch_tourism_cleaned.json"
        with open(cleaned_json_path, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Updated cleaned JSON -> {cleaned_json_path}")

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
            # Add extra fields from local directory (phone, email, etc.)
            for field in ['phone', 'email', 'website', 'facebook', 'guide_name']:
                if rec.get(field):
                    row[field] = rec[field]
            csv_rows.append(row)
        
        df = pd.DataFrame(csv_rows)
        csv_path = f"data/arbaminch_specific_sites_{timestamp}.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8')
        logger.info(f"Saved CSV  -> {csv_path}")

        logger.info("=" * 60)
        logger.info(f"DONE! Total records: {len(all_data)}")
        logger.info("=" * 60)
    else:
        logger.warning("No data was scraped!")


if __name__ == "__main__":
    main()
