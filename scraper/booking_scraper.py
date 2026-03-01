import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base_scraper import BaseScraper

logger = logging.getLogger("BookingScraper")


class BookingScraper(BaseScraper):
    """Scrapes accommodations from Booking.com using a shared Selenium driver."""

    def scrape_arbaminch_accommodations(self) -> List[Dict]:
        """Scrape accommodations in Arba Minch from Booking.com"""

        # Dynamic dates: 2 weeks from now, 1 night
        checkin = datetime.now() + timedelta(days=14)
        checkout = checkin + timedelta(days=1)

        url = (
            f"https://www.booking.com/searchresults.html"
            f"?ss=Arba+Minch%2C+Ethiopia"
            f"&checkin={checkin.strftime('%Y-%m-%d')}"
            f"&checkout={checkout.strftime('%Y-%m-%d')}"
            f"&group_adults=2&no_rooms=1&group_children=0"
        )

        logger.info(f"Loading Booking.com: {url}")
        self.driver.get(url)
        time.sleep(5)  # Booking.com needs time to render

        # Sometimes Booking.com shows a CAPTCHA or cookie banner — try to dismiss it
        try:
            cookie_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            cookie_btn.click()
            time.sleep(1)
        except Exception:
            pass  # No cookie banner

        # Wait for property cards to load
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="property-card"]'))
            )
        except Exception:
            logger.warning("Property cards did not load in time. Trying to parse anyway.")

        # Parse the page source with BeautifulSoup
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(self.driver.page_source, 'lxml')

        results = []
        properties = soup.find_all('div', {'data-testid': 'property-card'})

        if not properties:
            logger.warning("No property cards found via BeautifulSoup. Trying Selenium fallback.")
            return self._extract_selenium_fallback()

        logger.info(f"Found {len(properties)} properties on Booking.com")

        for prop in properties:
            try:
                # Name
                name_elem = prop.find('div', {'data-testid': 'title'})
                name = name_elem.get_text(strip=True) if name_elem else "Unknown Property"

                # Link
                link_elem = prop.find('a', {'data-testid': 'title-link'})
                link = link_elem['href'] if link_elem and link_elem.get('href') else ""
                if link and not link.startswith('http'):
                    link = "https://www.booking.com" + link

                # Rating (Stars)
                rating_elem = prop.find('div', {'data-testid': 'rating-stars'})
                rating = len(rating_elem.find_all('span')) if rating_elem else "N/A"

                # Review Score
                score_text = "N/A"
                score_elem = prop.find('div', {'data-testid': 'review-score'})
                if score_elem:
                    score_div = score_elem.find('div', {'aria-label': True})
                    if score_div:
                        score_text = score_div.get('aria-label', 'N/A')

                # Price
                price_elem = prop.find('span', {'data-testid': 'price-and-discounted-price'})
                price = price_elem.get_text(strip=True) if price_elem else "N/A"

                # Address
                addr_elem = prop.find('span', {'data-testid': 'address'})
                address = addr_elem.get_text(strip=True) if addr_elem else "Arba Minch"

                results.append({
                    'name': name,
                    'type': 'accommodation',
                    'rating': rating,
                    'review_score': score_text,
                    'price': price,
                    'address': address,
                    'link': link,
                    'source': 'Booking.com'
                })
            except Exception as e:
                logger.warning(f"Error parsing property: {e}")
                continue

        logger.info(f"Scraped {len(results)} properties from Booking.com")
        return results

    def _extract_selenium_fallback(self) -> List[Dict]:
        """Fallback: extract property info directly from Selenium elements"""
        results = []
        seen = set()
        try:
            cards = self.driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="property-card"]')
            if not cards:
                # Try broader selector
                cards = self.driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="title"]')

            for card in cards:
                try:
                    text = card.text.strip()
                    lines = text.split('\n')
                    name = lines[0] if lines else "Unknown"

                    if name in seen or len(name) < 3:
                        continue
                    seen.add(name)

                    results.append({
                        'name': name,
                        'type': 'accommodation',
                        'rating': 'N/A',
                        'review_score': 'N/A',
                        'price': 'N/A',
                        'address': 'Arba Minch',
                        'link': '',
                        'source': 'Booking.com'
                    })
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Selenium fallback failed: {e}")
        return results
