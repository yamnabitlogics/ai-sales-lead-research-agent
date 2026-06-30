"""
tools/browser_tool.py
──────────────────────
A custom CrewAI tool that uses Playwright to visit a real website
and extract its text content for agents to analyze.
"""

from crewai.tools import BaseTool
from playwright.sync_api import sync_playwright
from config.settings import HEADLESS_BROWSER, BROWSER_TIMEOUT


class WebsiteScraperTool(BaseTool):
    name: str = "Website Scraper"
    description: str = (
        "Visits a given website URL using a real browser and returns the "
        "visible text content of the page. Use this to research a company's "
        "actual website instead of guessing. Input should be a full URL "
        "starting with http:// or https://"
    )

    def _run(self, url: str) -> str:
        if not url.startswith("http"):
            url = "https://" + url

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=HEADLESS_BROWSER)
                page = browser.new_page()
                page.goto(url, timeout=BROWSER_TIMEOUT)
                page.wait_for_load_state("networkidle", timeout=BROWSER_TIMEOUT)

                text = page.inner_text("body")
                title = page.title()

                browser.close()

                # Trim to avoid overwhelming the LLM with huge pages
                max_chars = 6000
                if len(text) > max_chars:
                    text = text[:max_chars] + "... [content trimmed]"

                return f"Page title: {title}\n\nContent:\n{text}"

        except Exception as e:
            return f"Error scraping {url}: {str(e)}"