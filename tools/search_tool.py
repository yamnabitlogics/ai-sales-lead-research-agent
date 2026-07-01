"""
tools/search_tool.py
──────────────────────
Wraps CrewAI's built-in Serper search tool so agents can look up
real, current information (people, news, public profiles) on the web.
"""

from crewai_tools import SerperDevTool
from config.settings import SERPER_API_KEY
import os


os.environ["SERPER_API_KEY"] = SERPER_API_KEY

web_search_tool = SerperDevTool()