"""
Scraper for Arba Minch Local Directory
"""
import logging
import time
import re
from typing import List, Dict
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base_scraper import BaseScraper

logger = logging.getLogger("LocalDirectoryScraper")


class LocalDirectoryScraper(BaseScraper):
    """Scrapes businesses from Arba Minch Local Directory using a shared Selenium driver."""

    BASE_URL = "https://arbaminchlocaldirectory.com"

    def scrape_specific_pages(self, urls: List[str]) -> List[Dict]:
        """Scrape specific pages from the local directory"""
        all_results = []
        
        for url in urls:
            logger.info(f"Scraping: {url}")
            try:
                # Extract category name from URL
                if '/hotels/' in url:
                    category_name = 'Hotel'
                    business_type = 'hotels'
                elif '/restaurants/' in url:
                    category_name = 'Restaurant'
                    business_type = 'restaurants'
                elif '/lodges-resorts/' in url:
                    category_name = 'Lodge/Resort'
                    business_type = 'resorts'
                elif '/guest-houses-pensions/' in url:
                    category_name = 'Guest House/Pension'
                    business_type = 'guest house'
                elif '/travel-agencies-tour-guides/' in url:
                    category_name = 'Tour Guide'
                    business_type = 'tour guide'
                elif '/auto-services/' in url:
                    category_name = 'Auto Services'
                    business_type = 'car rental'
                elif '/health-medical/' in url:
                    category_name = 'Health/Medical'
                    business_type = 'health'
                else:
                    category_name = 'Business'
                    business_type = 'business'
                
                results = self._scrape_page(url, category_name, business_type)
                all_results.extend(results)
                logger.info(f"  -> Got {len(results)} entries")
                time.sleep(2)
            except Exception as e:
                logger.error(f"  -> Error scraping {url}: {e}")

        return all_results

    def _scrape_page(self, url: str, category_name: str, business_type: str) -> List[Dict]:
        """Scrape a specific page from the directory"""
        logger.info(f"Loading: {url}")

        self.driver.get(url)
        time.sleep(4)

        results = []
        seen_names = set()

        # Wait for listings to load
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.entry, article, .listing, [class*="business"]'))
            )
        except Exception:
            logger.warning("Listings did not load in time. Trying to parse anyway.")

        # Try multiple selectors for business listings
        # The local directory uses headings (h2, h3) for business names
        listings = []
        selectors = [
            'h2',  # Main business headings
            'h3',  # Secondary headings
            '.entry',
            'article',
            '.listing',
            '[class*="business"]',
            '[class*="directory"]',
            '.post',
        ]
        for selector in selectors:
            listings = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if listings:
                logger.info(f"Found {len(listings)} listings using selector: {selector}")
                break

        for listing in listings:
            try:
                # Get the business name from the heading
                name = listing.text.strip()
                
                # Skip if it's a heading that's not a business name
                if not name or len(name) < 3:
                    continue
                
                # Skip navigation/header text
                if any(skip in name.lower() for skip in [
                    'home', 'about', 'contact', 'category', 'search',
                    'coming soon', 'add your business', 'questions or inquiries',
                    'return to home', 'community resources'
                ]):
                    continue
                
                # For headings, get the following content block
                # The structure is usually: <h2>Business Name</h2> followed by details
                try:
                    # Get the parent container that includes the heading and its content
                    parent = listing.find_element(By.XPATH, "./following-sibling::*[1] | ./parent::*")
                    content_text = parent.text if parent else listing.text
                except Exception:
                    content_text = listing.text
                
                # Extract name (first line, usually the heading text)
                name_lines = name.split('\n')
                name = name_lines[0].strip()
                
                # Clean name - remove bold markers if any
                name = re.sub(r'\*\*', '', name).strip()
                
                if not name or len(name) < 3 or name in seen_names:
                    continue
                
                seen_names.add(name)

                # Link - use the page URL as the link
                link = url

                # Extract additional info from the content
                phone = ""
                email = ""
                website = ""
                facebook = ""
                
                # Look for phone patterns (Ethiopian format: +251 XX XXX XXXX or 046-XXX-XXXX)
                phone_patterns = [
                    r'\+251[\s-]?\d{1,3}[\s-]?\d{1,4}[\s-]?\d{1,4}[\s-]?\d{1,4}',
                    r'0\d{2}[\s-]?\d{3}[\s-]?\d{4}',
                    r'\d{3}[\s-]?\d{3}[\s-]?\d{4}',
                ]
                for pattern in phone_patterns:
                    phone_match = re.search(pattern, content_text)
                    if phone_match:
                        phone = phone_match.group(0).strip()
                        break
                
                # Look for email
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', content_text)
                if email_match:
                    email = email_match.group(0).strip()
                
                # Look for website links
                try:
                    # Check if listing or its siblings have website links
                    all_links = listing.find_elements(By.CSS_SELECTOR, 'a[href*="http"]')
                    for link_elem in all_links:
                        href = link_elem.get_attribute("href")
                        if href:
                            if 'facebook' in href.lower():
                                facebook = href
                            elif 'wordpress' not in href.lower() and 'arbaminchlocaldirectory' not in href.lower():
                                website = href
                except Exception:
                    pass
                
                # Also check parent/siblings for links
                try:
                    parent = listing.find_element(By.XPATH, "./..")
                    parent_links = parent.find_elements(By.CSS_SELECTOR, 'a[href*="http"]')
                    for link_elem in parent_links:
                        href = link_elem.get_attribute("href")
                        if href:
                            if 'facebook' in href.lower() and not facebook:
                                facebook = href
                            elif 'wordpress' not in href.lower() and 'arbaminchlocaldirectory' not in href.lower() and not website:
                                website = href
                except Exception:
                    pass

                result_item = {
                    'name': name,
                    'type': business_type,
                    'category': category_name,
                    'link': link,
                    'source': 'Arba Minch Local Directory'
                }
                
                if phone:
                    result_item['phone'] = phone
                if email:
                    result_item['email'] = email
                if website:
                    result_item['website'] = website
                if facebook:
                    result_item['facebook'] = facebook

                results.append(result_item)
            except Exception as e:
                logger.debug(f"Error parsing listing: {e}")
                continue

        return results
