import logging
import time
from typing import List, Dict
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base_scraper import BaseScraper

logger = logging.getLogger("GoogleMapsScraper")


class GoogleMapsScraper(BaseScraper):
    """Scrapes business listings from Google Maps using a shared Selenium driver."""

    def search_arbaminch_services(self, service_type: str, max_results: int = 20) -> List[Dict]:
        """
        Search for services in Arba Minch on Google Maps.
        Forces English via hl=en parameter.
        """
        query = f"{service_type} in Arba Minch, Ethiopia"
        url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}?hl=en"

        logger.info(f"Navigating to {url}")
        self.driver.get(url)
        time.sleep(4)

        # Wait for the results feed to appear
        try:
            wait = WebDriverWait(self.driver, 15)
            scrollable_div = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed']"))
            )
        except Exception:
            logger.error("Could not find the results list. Google Maps structure might have changed.")
            return []

        results = []
        unique_links = set()

        # Scroll to load more results
        last_height = self.driver.execute_script("return arguments[0].scrollHeight", scrollable_div)

        for scroll_attempt in range(10):
            # Find all anchor links to places
            place_links = scrollable_div.find_elements(By.CSS_SELECTOR, "a[href*='/maps/place/']")

            for link_el in place_links:
                if len(results) >= max_results:
                    break

                try:
                    link = link_el.get_attribute("href")
                    if not link or link in unique_links:
                        continue

                    unique_links.add(link)

                    # The aria-label of the <a> tag usually contains the business name
                    name = link_el.get_attribute("aria-label")
                    if not name:
                        name = link_el.text.split('\n')[0] if link_el.text else "Unknown"

                    # Try to get the surrounding text for rating/category
                    parent = link_el.find_element(By.XPATH, "./..")
                    text_lines = parent.text.split('\n') if parent.text else []

                    rating = "N/A"
                    category = service_type
                    address = "N/A"

                    for line in text_lines:
                        # Rating is typically like "4.2" or "4.2(123)"
                        if any(c.isdigit() for c in line) and '.' in line and len(line) < 20:
                            if rating == "N/A":
                                rating = line.strip()
                        # Category lines are short text without digits
                        elif not any(c.isdigit() for c in line) and len(line) < 40 and line != name:
                            if category == service_type:
                                category = line.strip()

                    results.append({
                        'name': name,
                        'type': service_type,
                        'category': category,
                        'rating': rating,
                        'link': link,
                        'source': 'Google Maps'
                    })
                except Exception:
                    continue

            if len(results) >= max_results:
                break

            # Scroll down
            self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
            time.sleep(2)

            new_height = self.driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
            if new_height == last_height:
                logger.info("Reached the end of the list.")
                break
            last_height = new_height

        logger.info(f"Found {len(results)} {service_type} in Arba Minch")
        return results
