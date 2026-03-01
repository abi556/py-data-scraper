"""
Scraper for Agoda hotels in Arba Minch
"""
import logging
import time
from typing import List, Dict
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base_scraper import BaseScraper

logger = logging.getLogger("AgodaScraper")


class AgodaScraper(BaseScraper):
    """Scrapes hotels from Agoda using a shared Selenium driver."""

    def scrape_arbaminch_hotels(self) -> List[Dict]:
        """Scrape hotels in Arba Minch from Agoda"""
        # Dynamic dates: 2 weeks from now, 1 night
        checkin = datetime.now() + timedelta(days=14)
        checkout = checkin + timedelta(days=1)

        url = (
            f"https://www.agoda.com/search"
            f"?city=373"
            f"&checkIn={checkin.strftime('%Y-%m-%d')}"
            f"&checkOut={checkout.strftime('%Y-%m-%d')}"
            f"&adults=2"
            f"&children=0"
            f"&rooms=1"
        )

        logger.info(f"Loading Agoda: {url}")
        self.driver.get(url)
        time.sleep(5)

        # Wait for hotel listings
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-selenium="hotel-item"]'))
            )
        except Exception:
            logger.warning("Hotel listings did not load in time. Trying to parse anyway.")

        results = []
        seen_names = set()

        # Find all hotel listings
        hotel_cards = self.driver.find_elements(By.CSS_SELECTOR, '[data-selenium="hotel-item"]')
        logger.info(f"Found {len(hotel_cards)} hotel cards on Agoda")

        for card in hotel_cards:
            try:
                # Name
                name_elem = card.find_element(By.CSS_SELECTOR, '[data-selenium="hotel-name"]')
                name = name_elem.text.strip() if name_elem else "Unknown"

                if not name or name in seen_names or len(name) < 3:
                    continue
                seen_names.add(name)

                # Link
                link_elem = card.find_element(By.CSS_SELECTOR, 'a[data-selenium="hotel-name-link"]')
                link = link_elem.get_attribute("href") if link_elem else ""
                if link and not link.startswith('http'):
                    link = "https://www.agoda.com" + link

                # Rating
                rating = "N/A"
                try:
                    rating_elem = card.find_element(By.CSS_SELECTOR, '[data-selenium="review-score"]')
                    rating = rating_elem.text.strip() if rating_elem else "N/A"
                except Exception:
                    pass

                # Price
                price = "N/A"
                try:
                    price_elem = card.find_element(By.CSS_SELECTOR, '[data-selenium="final-price"]')
                    price = price_elem.text.strip() if price_elem else "N/A"
                except Exception:
                    pass

                results.append({
                    'name': name,
                    'type': 'accommodation',
                    'rating': rating,
                    'price': price,
                    'address': 'Arba Minch',
                    'link': link,
                    'source': 'Agoda'
                })
            except Exception as e:
                logger.debug(f"Error parsing hotel card: {e}")
                continue

        logger.info(f"Scraped {len(results)} hotels from Agoda")
        return results
