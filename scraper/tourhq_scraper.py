"""
Scraper for tourHQ tour guides in Arba Minch
"""
import logging
import time
import re
from typing import List, Dict
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base_scraper import BaseScraper

logger = logging.getLogger("TourHQScraper")


class TourHQScraper(BaseScraper):
    """Scrapes tour guides from tourHQ using a shared Selenium driver."""

    def scrape_arbaminch_guides(self) -> List[Dict]:
        """Scrape tour guides in Arba Minch from tourHQ"""
        url = "https://www.tourhq.com/ethiopia/arba-minch/tour-guides"
        logger.info(f"Loading tourHQ: {url}")

        self.driver.get(url)
        time.sleep(5)

        # Wait for guide listings
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.guide-card, [class*="guide"], .guide-item'))
            )
        except Exception:
            logger.warning("Guide listings did not load in time. Trying to parse anyway.")

        results = []
        seen_names = set()

        # Try multiple selectors for guide cards
        guide_cards = []
        selectors = [
            '.guide-card',
            '[class*="guide-card"]',
            '[class*="guide-item"]',
            '.guide',
            'article[class*="guide"]',
        ]
        for selector in selectors:
            guide_cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if guide_cards:
                logger.info(f"Found {len(guide_cards)} guide cards using selector: {selector}")
                break

        if not guide_cards:
            # Fallback: look for any links that might be guide profiles
            guide_cards = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/guide/"], a[href*="/tour-guide"]')
            logger.info(f"Fallback: Found {len(guide_cards)} potential guide links")

        for card in guide_cards:
            try:
                # Name - try multiple approaches
                name = None
                name_selectors = [
                    'h2', 'h3', 'h4',
                    '[class*="name"]',
                    '[class*="title"]',
                    '.guide-name',
                    'strong',
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
                    # Try getting text from the card itself
                    text = card.text.strip()
                    lines = text.split('\n')
                    if lines:
                        name = lines[0].strip()

                if not name or len(name) < 3 or name in seen_names:
                    continue

                # Skip common non-name text
                if any(skip in name.lower() for skip in ['loading', 'load more', 'review', 'rating', 'welcome']):
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
                        link = "https://www.tourhq.com" + link
                except Exception:
                    pass

                # Rating/Reviews
                rating = "N/A"
                try:
                    rating_text = card.text
                    # Look for patterns like "4.5" or "5 stars" or "36 Reviews"
                    rating_match = re.search(r'(\d+\.?\d*)\s*(?:stars?|reviews?)', rating_text, re.IGNORECASE)
                    if rating_match:
                        rating = rating_match.group(1)
                    reviews_match = re.search(r'(\d+)\s*reviews?', rating_text, re.IGNORECASE)
                    if reviews_match:
                        rating = f"{rating}({reviews_match.group(1)})" if rating != "N/A" else f"N/A({reviews_match.group(1)})"
                except Exception:
                    pass

                results.append({
                    'name': name,
                    'type': 'tour guide',
                    'rating': rating,
                    'link': link,
                    'source': 'tourHQ'
                })
            except Exception as e:
                logger.debug(f"Error parsing guide card: {e}")
                continue

        logger.info(f"Scraped {len(results)} tour guides from tourHQ")
        return results
