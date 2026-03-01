import logging
import time
from typing import List, Dict
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base_scraper import BaseScraper

logger = logging.getLogger("TripAdvisorScraper")


class TripAdvisorScraper(BaseScraper):
    """Scrapes hotels and restaurants from TripAdvisor using a shared Selenium driver."""

    BASE_URL = "https://www.tripadvisor.com"
    # Correct geo ID for Arba Minch, Ethiopia
    ARBA_MINCH_GEO = "g776853"

    def scrape_arbaminch_hotels(self) -> List[Dict]:
        """Scrape hotels in Arba Minch from TripAdvisor"""
        url = f"{self.BASE_URL}/Hotels-{self.ARBA_MINCH_GEO}-Arba_Minch-Hotels.html"
        logger.info(f"Loading TripAdvisor hotels page: {url}")

        self.driver.get(url)
        time.sleep(5)

        results = []
        seen_names = set()

        # Extract hotel links from the rendered page using Selenium
        hotel_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="Hotel_Review"]')
        logger.info(f"Found {len(hotel_links)} Hotel_Review link elements")

        for link_el in hotel_links:
            try:
                name = link_el.text.strip()
                href = link_el.get_attribute("href") or ""

                # Skip empty names, very short names, or duplicates
                if not name or len(name) < 3 or name in seen_names:
                    continue
                # Skip non-name text like "Read all reviews", "reviews"
                if any(skip in name.lower() for skip in ['review', 'read all', 'write a', 'see all']):
                    continue

                seen_names.add(name)

                # Try to get rating from nearby elements
                rating = "N/A"
                try:
                    parent = link_el.find_element(By.XPATH, "./ancestor::div[contains(@class,'listing') or contains(@class,'card') or contains(@class,'property')]")
                    bubble = parent.find_element(By.CSS_SELECTOR, 'svg[aria-label*="bubble"]')
                    rating = bubble.get_attribute("aria-label")
                except Exception:
                    pass

                results.append({
                    'name': name,
                    'type': 'hotel',
                    'rating': rating,
                    'link': href,
                    'source': 'TripAdvisor'
                })
            except Exception as e:
                continue

        logger.info(f"Scraped {len(results)} hotels from TripAdvisor")
        return results

    def scrape_arbaminch_restaurants(self) -> List[Dict]:
        """Scrape restaurants in Arba Minch from TripAdvisor"""
        url = f"{self.BASE_URL}/Restaurants-{self.ARBA_MINCH_GEO}-Arba_Minch.html"
        logger.info(f"Loading TripAdvisor restaurants page: {url}")

        self.driver.get(url)
        time.sleep(5)

        results = []
        seen_names = set()

        restaurant_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="Restaurant_Review"]')
        logger.info(f"Found {len(restaurant_links)} Restaurant_Review link elements")

        for link_el in restaurant_links:
            try:
                name = link_el.text.strip()
                href = link_el.get_attribute("href") or ""

                if not name or len(name) < 3 or name in seen_names:
                    continue
                if any(skip in name.lower() for skip in ['review', 'read all', 'write a', 'see all']):
                    continue

                seen_names.add(name)

                rating = "N/A"
                try:
                    parent = link_el.find_element(By.XPATH, "./ancestor::div[contains(@class,'listing') or contains(@class,'card') or contains(@class,'restaurant')]")
                    bubble = parent.find_element(By.CSS_SELECTOR, 'svg[aria-label*="bubble"]')
                    rating = bubble.get_attribute("aria-label")
                except Exception:
                    pass

                results.append({
                    'name': name,
                    'type': 'restaurant',
                    'rating': rating,
                    'link': href,
                    'source': 'TripAdvisor'
                })
            except Exception as e:
                continue

        logger.info(f"Scraped {len(results)} restaurants from TripAdvisor")
        return results

    def scrape_arbaminch_things_to_do(self) -> List[Dict]:
        """Scrape things to do / attractions in Arba Minch from TripAdvisor"""
        url = f"{self.BASE_URL}/Attractions-{self.ARBA_MINCH_GEO}-Activities-Arba_Minch.html"
        logger.info(f"Loading TripAdvisor attractions page: {url}")

        self.driver.get(url)
        time.sleep(5)

        results = []
        seen_names = set()

        attraction_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="Attraction_Review"]')
        logger.info(f"Found {len(attraction_links)} Attraction_Review link elements")

        for link_el in attraction_links:
            try:
                name = link_el.text.strip()
                href = link_el.get_attribute("href") or ""

                if not name or len(name) < 3 or name in seen_names:
                    continue
                if any(skip in name.lower() for skip in ['review', 'read all', 'write a', 'see all']):
                    continue

                seen_names.add(name)

                results.append({
                    'name': name,
                    'type': 'attraction',
                    'rating': 'N/A',
                    'link': href,
                    'source': 'TripAdvisor'
                })
            except Exception:
                continue

        logger.info(f"Scraped {len(results)} attractions from TripAdvisor")
        return results
