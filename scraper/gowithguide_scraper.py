"""
Scraper for GoWithGuide tour guides in Arba Minch
"""
import logging
import time
import re
from typing import List, Dict
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base_scraper import BaseScraper

logger = logging.getLogger("GoWithGuideScraper")


class GoWithGuideScraper(BaseScraper):
    """Scrapes tour guides from GoWithGuide using a shared Selenium driver."""

    def scrape_arbaminch_guides(self) -> List[Dict]:
        """Scrape tour guides in Arba Minch from GoWithGuide"""
        url = "https://gowithguide.com/ethiopia/arba-minch/tours"
        logger.info(f"Loading GoWithGuide: {url}")

        self.driver.get(url)
        time.sleep(5)

        # Wait for guide/tour listings
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.tour-card, [class*="tour"], [class*="guide"], article'))
            )
        except Exception:
            logger.warning("Listings did not load in time. Trying to parse anyway.")

        results = []
        seen_names = set()

        # Try multiple selectors for tour/guide cards
        cards = []
        selectors = [
            '.tour-card',
            '[class*="tour-card"]',
            '[class*="tour-item"]',
            '.tour',
            'article',
            '[class*="guide-card"]',
        ]
        for selector in selectors:
            cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if cards:
                logger.info(f"Found {len(cards)} cards using selector: {selector}")
                break

        if not cards:
            # Fallback: look for any links that might be tour/guide profiles
            cards = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/tour/"], a[href*="/guide/"]')
            logger.info(f"Fallback: Found {len(cards)} potential tour/guide links")

        for card in cards:
            try:
                # Name - try multiple approaches
                name = None
                name_selectors = [
                    'h2', 'h3', 'h4',
                    '[class*="title"]',
                    '[class*="name"]',
                    '.tour-title',
                    'strong',
                    'a',
                ]
                for sel in name_selectors:
                    try:
                        name_elem = card.find_element(By.CSS_SELECTOR, sel)
                        name = name_elem.text.strip()
                        if name and len(name) > 2:
                            break
                    except Exception:
                        continue

                if not name:
                    text = card.text.strip()
                    lines = text.split('\n')
                    if lines:
                        name = lines[0].strip()

                if not name or len(name) < 3 or name in seen_names:
                    continue

                # Skip common non-name text
                if any(skip in name.lower() for skip in ['loading', 'load more', 'from', 'per person', 'book', 'tour']):
                    continue

                seen_names.add(name)

                # Link
                link = ""
                try:
                    if card.tag_name == 'a':
                        link = card.get_attribute("href")
                    else:
                        link_elem = card.find_element(By.CSS_SELECTOR, 'a')
                        link = link_elem.get_attribute("href")
                    if link and not link.startswith('http'):
                        link = "https://gowithguide.com" + link
                except Exception:
                    pass

                # Price
                price = "N/A"
                try:
                    price_text = card.text
                    price_match = re.search(r'\$([\d,]+)', price_text)
                    if price_match:
                        price = f"${price_match.group(1)}"
                except Exception:
                    pass

                # Guide name (if available)
                guide_name = ""
                try:
                    guide_elem = card.find_element(By.CSS_SELECTOR, '[class*="guide-name"], [class*="guide"]')
                    guide_name = guide_elem.text.strip() if guide_elem else ""
                except Exception:
                    pass

                results.append({
                    'name': name,
                    'type': 'tour guide',
                    'rating': 'N/A',
                    'price': price,
                    'guide_name': guide_name,
                    'link': link,
                    'source': 'GoWithGuide'
                })
            except Exception as e:
                logger.debug(f"Error parsing card: {e}")
                continue

        logger.info(f"Scraped {len(results)} tour guides from GoWithGuide")
        return results
