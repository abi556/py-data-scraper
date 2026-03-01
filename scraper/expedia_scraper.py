"""
Scraper for Expedia hotels in Arba Minch
"""
import logging
import time
import re
from typing import List, Dict
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base_scraper import BaseScraper

logger = logging.getLogger("ExpediaScraper")


class ExpediaScraper(BaseScraper):
    """Scrapes hotels from Expedia using a shared Selenium driver."""

    def scrape_arbaminch_hotels(self) -> List[Dict]:
        """Scrape hotels in Arba Minch from Expedia"""
        # Dynamic dates: 2 weeks from now, 1 night
        checkin = datetime.now() + timedelta(days=14)
        checkout = checkin + timedelta(days=1)

        url = (
            f"https://www.expedia.com/Hotel-Search"
            f"?startDate={checkin.strftime('%Y-%m-%d')}"
            f"&endDate={checkout.strftime('%Y-%m-%d')}"
            f"&regionId=373"
            f"&adults=2"
            f"&sort=RECOMMENDED"
            f"&destination=Arba%20Minch%2C%20Southern%20Nations%2C%20Nationalities%2C%20and%20Peoples%27%20Region%2C%20Ethiopia"
        )

        logger.info(f"Loading Expedia: {url}")
        self.driver.get(url)
        time.sleep(5)

        # Wait for hotel listings to load
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-stid="property-listing"]'))
            )
        except Exception:
            logger.warning("Hotel listings did not load in time. Trying to parse anyway.")

        results = []
        seen_names = set()

        # Find all hotel listings
        hotel_cards = self.driver.find_elements(By.CSS_SELECTOR, '[data-stid="property-listing"]')
        logger.info(f"Found {len(hotel_cards)} hotel cards on Expedia")

        for card in hotel_cards:
            try:
                # Name
                name_elem = card.find_element(By.CSS_SELECTOR, '[data-stid="content-hotel-title"]')
                name = name_elem.text.strip() if name_elem else "Unknown"

                if not name or name in seen_names or len(name) < 3:
                    continue
                seen_names.add(name)

                # Link
                link_elem = card.find_element(By.CSS_SELECTOR, 'a[data-stid="open-hotel-information"]')
                link = link_elem.get_attribute("href") if link_elem else ""
                if link and not link.startswith('http'):
                    link = "https://www.expedia.com" + link

                # Rating
                rating = "N/A"
                try:
                    rating_elem = card.find_element(By.CSS_SELECTOR, '[data-stid="content-hotel-guest-rating"]')
                    rating = rating_elem.text.strip() if rating_elem else "N/A"
                except Exception:
                    pass

                # Price
                price = "N/A"
                try:
                    price_elem = card.find_element(By.CSS_SELECTOR, '[data-stid="price-lockup-text"]')
                    price = price_elem.text.strip() if price_elem else "N/A"
                except Exception:
                    pass

                # Address
                address = "Arba Minch"
                try:
                    addr_elem = card.find_element(By.CSS_SELECTOR, '[data-stid="content-hotel-neighborhood"]')
                    address = addr_elem.text.strip() if addr_elem else "Arba Minch"
                except Exception:
                    pass

                results.append({
                    'name': name,
                    'type': 'accommodation',
                    'rating': rating,
                    'price': price,
                    'address': address,
                    'link': link,
                    'source': 'Expedia'
                })
            except Exception as e:
                logger.debug(f"Error parsing hotel card: {e}")
                continue

        logger.info(f"Scraped {len(results)} hotels from Expedia")
        return results
