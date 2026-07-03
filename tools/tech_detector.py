"""
tools/tech_detector.py
----------------------
A custom CrewAI tool that inspects a website's HTML/headers to
detect technologies in use (frameworks, analytics, CMS, etc.)
"""

from crewai.tools import BaseTool
from playwright.sync_api import sync_playwright

from config.settings import HEADLESS_BROWSER, BROWSER_TIMEOUT
from config.logger import get_logger
from utils.validation import normalize_website
from utils.errors import ValidationError

logger = get_logger("tech_detector")


KNOWN_SIGNATURES = {
    "React": ["react", "_reactRootContainer", "__react"],
    "Next.js": ["__NEXT_DATA__", "_next/static"],
    "Vue.js": ["__vue__", "vue.js"],
    "WordPress": ["wp-content", "wp-includes"],
    "Shopify": ["cdn.shopify.com", "Shopify.theme"],
    "Webflow": ["webflow.js", "wf-page"],
    "Google Analytics": ["googletagmanager.com", "gtag("],
    "HubSpot": ["js.hs-scripts.com", "hubspot"],
    "Cloudflare": ["cloudflare"],
    "Tailwind CSS": ["tailwind"],
    "Bootstrap": ["bootstrap.min.css", "bootstrap.bundle"],
}


class TechStackDetectorTool(BaseTool):
    name: str = "Technology Stack Detector"
    description: str = (
        "Visits a website and inspects its HTML source code to detect "
        "technologies in use (React, WordPress, Shopify, analytics tools, etc). "
        "Input should be a full URL starting with http:// or https://"
    )

    def _run(self, url: str = "", **kwargs) -> str:
        if not url:
            url = kwargs.get("url", "")
        if not url and kwargs:
            url = str(next(iter(kwargs.values()), ""))

        url = url.strip()
        if not url:
            return "ERROR: No website URL provided for technology detection."

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
                    return f"ERROR: Website returned HTTP {response.status} for {url}."
                try:
                    page.wait_for_load_state("networkidle", timeout=BROWSER_TIMEOUT)
                except Exception:
                    pass

                html = page.content()
                headers = response.headers if response else {}
                browser.close()

            detected = []
            for tech, signatures in KNOWN_SIGNATURES.items():
                for sig in signatures:
                    if sig.lower() in html.lower():
                        detected.append(tech)
                        break

            server_header = headers.get("server", "unknown")
            result = f"URL: {url}\nServer header: {server_header}\n"
            if detected:
                result += f"Detected technologies: {', '.join(detected)}"
            else:
                result += (
                    "Detected technologies: None from HTML signatures. "
                    "Inspect page content and headers for additional clues."
                )
            return result

        except Exception as e:
            logger.warning(f"Tech detection failed for {url}: {e}")
            return f"ERROR detecting tech stack for {url}: {str(e)}"
