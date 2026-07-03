"""
tools/browser_tool.py
---------------------
A custom CrewAI tool that uses Playwright to visit a real website
and extract its text content for agents to analyze.
"""

import re

from crewai.tools import BaseTool
from playwright.sync_api import sync_playwright

from config.settings import HEADLESS_BROWSER, BROWSER_TIMEOUT
from config.logger import get_logger
from utils.validation import normalize_website
from utils.errors import ValidationError

logger = get_logger("browser_tool")


class WebsiteScraperTool(BaseTool):
    name: str = "Website Scraper"
    description: str = (
        "Visits a given website URL using a real browser and returns the "
        "visible text content of the page. Use this to research a company's "
        "actual website instead of guessing. Input should be a full URL "
        "starting with http:// or https://"
    )

    def _run(self, url: str = "", **kwargs) -> str:
        if not url:
            url = kwargs.get("url", "")
        if not url and kwargs:
            url = str(next(iter(kwargs.values()), ""))

        url = url.strip()
        if not url:
            return (
                "ERROR: No website URL provided. "
                "Use web search to find company information instead."
            )

        try:
            url = normalize_website(url)
        except ValidationError as exc:
            return f"ERROR: Invalid website URL — {exc.message}"

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=HEADLESS_BROWSER)
                page = browser.new_page()
                response = page.goto(url, timeout=BROWSER_TIMEOUT, wait_until="domcontentloaded")
                if response and response.status >= 400:
                    browser.close()
                    return (
                        f"ERROR: Website returned HTTP {response.status} for {url}. "
                        "The site may be down or the URL may be incorrect."
                    )
                try:
                    page.wait_for_load_state("networkidle", timeout=BROWSER_TIMEOUT)
                except Exception:
                    pass
                text = page.inner_text("body")
                title = page.title()
                browser.close()

                if not text or len(text.strip()) < 50:
                    return (
                        f"ERROR: Website at {url} returned very little content. "
                        "The page may require JavaScript login or be blocking scrapers."
                    )

                max_chars = 6000
                if len(text) > max_chars:
                    text = text[:max_chars] + "... [content trimmed]"
                return f"Page title: {title}\nURL: {url}\n\nContent:\n{text}"
        except Exception as e:
            logger.warning(f"Scrape failed for {url}: {e}")
            error_msg = str(e)
            if "timeout" in error_msg.lower():
                return (
                    f"ERROR: Timed out loading {url}. "
                    "The website may be slow or unreachable."
                )
            if "net::" in error_msg or "ERR_" in error_msg:
                return (
                    f"ERROR: Could not reach {url}. "
                    "Please verify the website URL is correct and publicly accessible."
                )
            return f"ERROR scraping {url}: {error_msg}"
