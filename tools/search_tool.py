import os
from crewai_tools import SerperDevTool
from config.settings import SERPER_API_KEY
from config.logger import get_logger

logger = get_logger("search_tool")

os.environ["SERPER_API_KEY"] = SERPER_API_KEY

logger.info("Serper search tool initialized")
web_search_tool = SerperDevTool()