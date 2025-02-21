import time
import json
import sys

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import Error as PlaywrightError
from pricestream.client import get_redis_client
import os
from datetime import date, datetime, time, timedelta
from functools import wraps
from time import time as timer


logger.remove()
logger.add(sys.stdout, level="INFO")

# Define credentials
TRADOVATE_USERNAME = os.getenv("TRADOVATE_USERNAME")
TRADOVATE_PASSWORD = os.getenv("TRADOVATE_PASSWORD")

client = get_redis_client()


def timeit(func):
    """Calculates the execution time of the function on top of which the decorator is assigned"""

    @wraps(func)
    def wrap_func(*args, **kwargs):
        tic = timer()
        result = func(*args, **kwargs)
        tac = timer()
        logger.debug(f"Function {func.__name__!r} executed in {(tac - tic):.4f}s")
        return result

    return wrap_func


def login(page):
    """Attempts to log in to the website with retries."""
    kickoff_url: str = "https://trader.tradovate.com/welcome"
    logger.info(f"Navigating to {kickoff_url}")
    page.goto(kickoff_url)
    page.set_viewport_size({"width": 1280, "height": 800})
    page.wait_for_timeout(5000)
    logger.info(f"Attempting login using demo account: {TRADOVATE_USERNAME}")
    page.fill("#name-input", TRADOVATE_USERNAME)
    page.fill("#password-input", TRADOVATE_PASSWORD)
    page.wait_for_timeout(2000)
    page.click("button.MuiButton-containedPrimary")
    page.wait_for_timeout(5000)

    # Click Launch button if available
    try:
        launch_button_selector = "button.MuiButtonBase-root.MuiButton-root"
        logger.info("Clicking on `Launch` to navigate to price stream")
        page.click(launch_button_selector)
        page.wait_for_timeout(5000)
    except Exception as e:
        logger.warning(f"Launch button not found or error occurred: {e}")


@timeit
def get_prices(page):
    prices = {}
    info_columns = page.query_selector_all(".info-column")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    if not info_columns:
        logger.warning("No info-column elements found.")
        raise Exception("No info columns found")

    for column in info_columns:
        # Extract the symbol name if this is the symbol column
        symbol_elem = column.query_selector("div > span")
        symbol = symbol_elem.inner_text().strip() if symbol_elem else None
        label_elem = column.query_selector("small.text-muted")
        price_elem = column.query_selector(".number")

        if not label_elem or not price_elem:
            continue  # Skip this iteration if elements are missing

        label = label_elem.inner_text().strip()
        price = column.query_selector(".number").inner_text().strip()
        if label in ["ASK", "BID", "LAST"]:
            prices[label] = price

    return prices, timestamp, symbol


@timeit
def scrape_data(page, writer):
    """Scrapes last price data and writes it to CSV with retries."""
    prices, timestamp, _ = get_prices(page)
    price_data = {
        "TIMESTAMP": timestamp,
        "LAST": prices.get("LAST", None),
        "BID": prices.get("BID", None),
        "ASK": prices.get("ASK", None) 
    }
    logger.debug(f"Price data scrapped: {price_data}")
    client.publish("NQH5_PRICESTREAM", json.dumps(price_data))
    logger.debug(f"Published message to redis: {price_data}")


from tenacity import (
    retry, stop_after_attempt, wait_exponential, retry_if_exception_type
)
from playwright.sync_api import sync_playwright, Error as PlaywrightError


@retry(
    stop=stop_after_attempt(5),  # Max 5 retries
    wait=wait_exponential(multiplier=1, min=1, max=10),  # Exponential backoff
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        try:
            login(page)  # Assume this function logs in
            logger.debug("Login successful, starting scraping loop.")
            first_success_logged = False
            while True:
                try:
                    scrape_data(page, writer=None)
                    if not first_success_logged:
                        logger.success("✅ Scraping is connected and streaming price data")
                        first_success_logged = True
                    run.retry.statistics.clear()  # Reset retry counter on success
                except PlaywrightError as e:
                    logger.error(f"Playwright error: {e}. Restarting Playwright...")
                    raise  # Trigger retry
                except Exception as e:
                    logger.error(f"Unexpected error: {e}. Restarting Playwright...")
                    raise  # Trigger retry
                except KeyboardInterrupt:
                    logger.warning("Scraping manually stopped by user.")
                    return  # Clean exit

        except Exception as e:
            logger.error(f"Error in main run loop: {e}")
            raise
        finally:
            logger.info("Closing browser...")
            browser.close()
            logger.info("Browser closed.")


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        logger.warning("Process terminated by user. Exiting gracefully.")
    except Exception:
        logger.error("Max retries reached. Exiting...")