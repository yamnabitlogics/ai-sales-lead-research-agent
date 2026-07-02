"""
tests/test_phase2.py
─────────────────────
Tests for Phase 2 browser tools.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_browser_tool_importable():
    from tools.browser_tool import WebsiteScraperTool
    tool = WebsiteScraperTool()
    assert tool.name == "Website Scraper"


def test_tech_detector_importable():
    from tools.tech_detector import TechStackDetectorTool
    tool = TechStackDetectorTool()
    assert tool.name == "Technology Stack Detector"


def test_browser_tool_handles_bad_url():
    from tools.browser_tool import WebsiteScraperTool
    tool = WebsiteScraperTool()
    result = tool._run("https://this-url-does-not-exist-xyz123.com")
    assert "Error" in result or "error" in result.lower()


def test_tech_detector_handles_bad_url():
    from tools.tech_detector import TechStackDetectorTool
    tool = TechStackDetectorTool()
    result = tool._run("https://this-url-does-not-exist-xyz123.com")
    assert "Error" in result or "error" in result.lower()