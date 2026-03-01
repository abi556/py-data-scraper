"""
Scraper for TripAdvisor tour guides in Arba Minch
"""
import logging
import time
import re
from typing import List, Dict
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base_scraper import BaseScraper

logger = logging.getLogger("TripAdvisorGuideScraper")


class TripAdvisorGuideScraper(BaseScraper):
    """Scrapes tour guides from TripAdvisor search using a shared Selenium driver."""

    BASE_URL = "https://www.tripadvisor.com"
    ARBA_MINCH_GEO = "g776853"

    def scrape_arbaminch_guides(self) -> List[Dict]:
        """Scrape tour guides in Arba Minch from TripAdvisor search"""
        url = (
            f"{self.BASE_URL}/Search"
            f"?q=tour+guide+around+arba+minch%2C+ethiopia"
            f"&geo={self.ARBA_MINCH_GEO}"
            f"&ssrc=A"
        )
        logger.info(f"Loading TripAdvisor guide search: {url}")

        self.driver.get(url)
        time.sleep(5)

        results = []
        seen_names = set()

        # Wait for search results
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid*="result"], .result, [class*="result"]'))
            )
        except Exception:
            logger.warning("Search results did not load in time. Trying to parse anyway.")

        # Find all result items
        result_items = []
        selectors = [
            '[data-testid*="result"]',
            '.result',
            '[class*="result-item"]',
            '[class*="search-result"]',
            'article',
        ]
        for selector in selectors:
            result_items = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if result_items:
                logger.info(f"Found {len(result_items)} results using selector: {selector}")
                break

        for item in result_items:
            try:
                # Name
                name = None
                name_selectors = [
                    'h2', 'h3', 'h4',
                    '[class*="title"]',
                    '[class*="name"]',
                    'a',
                ]
                for sel in name_selectors:
                    try:
                        name_elem = item.find_element(By.CSS_SELECTOR, sel)
                        name = name_elem.text.strip()
                        if name and len(name) > 2:
                            break
                    except Exception:
                        continue

                if not name:
                    text = item.text.strip()
                    lines = text.split('\n')
                    if lines:
                        name = lines[0].strip()

                if not name or len(name) < 3 or name in seen_names:
                    continue

                # Skip non-name text
                if any(skip in name.lower() for skip in ['review', 'read all', 'write a', 'see all', 'search']):
                    continue
                if len(name) > 80 or name.count('.') >= 2:
                    continue

                # Strip leading numbers
                name = re.sub(r'^\d+\.\s*', '', name).strip()
                if not name:
                    continue

                seen_names.add(name)

                # Link
                link = ""
                try:
                    link_elem = item.find_element(By.CSS_SELECTOR, 'a')
                    link = link_elem.get_attribute("href")
                    if link and not link.startswith('http'):
                        link = self.BASE_URL + link
                except Exception:
                    pass

                # Rating
                rating = "N/A"
                try:
                    rating_elem = item.find_element(By.CSS_SELECTOR, 'svg[aria-label*="bubble"], [class*="rating"]')
                    rating = rating_elem.get_attribute("aria-label") if rating_elem else "N/A"
                except Exception:
                    pass

                results.append({
                    'name': name,
                    'type': 'tour guide',
                    'rating': rating,
                    'link': link,
                    'source': 'TripAdvisor'
                })
            except Exception as e:
                logger.debug(f"Error parsing result item: {e}")
                continue

        logger.info(f"Scraped {len(results)} tour guides from TripAdvisor")
        return results
