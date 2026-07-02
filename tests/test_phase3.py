"""
tests/test_phase3.py
─────────────────────
Tests for Phase 3 search tool.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_search_tool_importable():
    from tools.search_tool import web_search_tool
    assert web_search_tool is not None


def test_serper_key_configured():
    from config.settings import SERPER_API_KEY
    assert SERPER_API_KEY != "", "SERPER_API_KEY is not set in .env"


def test_decision_maker_agent_has_search_tool():
    from agents.definitions import decision_maker_agent
    tool_names = [t.name for t in decision_maker_agent.tools]
    assert any("search" in name.lower() or "serper" in name.lower()
               for name in tool_names)


def test_opportunity_agent_has_search_tool():
    from agents.definitions import opportunity_agent
    tool_names = [t.name for t in opportunity_agent.tools]
    assert any("search" in name.lower() or "serper" in name.lower()
               for name in tool_names)