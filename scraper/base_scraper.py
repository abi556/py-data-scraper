import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
import time
import json
import logging
from typing import List, Dict, Optional
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BaseScraper")


def create_driver(headless: bool = False) -> webdriver.Chrome:
    """
    Create a shared Chrome WebDriver using Selenium's built-in driver manager.
    Forces English language so all scraped content is in English.
    """
    options = ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Force English language
    options.add_argument("--lang=en-US")
    options.add_experimental_option("prefs", {
        "intl.accept_languages": "en,en_US",
    })

    ua = UserAgent()
    options.add_argument(f"user-agent={ua.random}")

    driver = webdriver.Chrome(options=options)
    # Hide webdriver flag to avoid detection
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver


class BaseScraper:
    def __init__(self, output_dir: str = "data", driver: Optional[webdriver.Chrome] = None):
        self.ua = UserAgent()
        self.output_dir = output_dir
        self.driver = driver

        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def get_page_source_soup(self, url: str, wait_seconds: float = 3.0) -> Optional[BeautifulSoup]:
        """Navigate to a URL using Selenium and return a BeautifulSoup object of the page source"""
        if not self.driver:
            logger.error("No Selenium driver available")
            return None
        try:
            self.driver.get(url)
            time.sleep(wait_seconds)  # Let JS render
            return BeautifulSoup(self.driver.page_source, 'lxml')
        except Exception as e:
            logger.error(f"Error loading {url}: {e}")
            return None

    def save_data(self, data: List[Dict], filename: str):
        """Save data to JSON file"""
        filepath = os.path.join(self.output_dir, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Successfully saved {len(data)} items to {filepath}")
        except Exception as e:
            logger.error(f"Error saving data to {filepath}: {e}")
