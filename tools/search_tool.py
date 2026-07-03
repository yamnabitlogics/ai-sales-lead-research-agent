import os

from crewai.tools import BaseTool

from config.settings import SERPER_API_KEY
from config.logger import get_logger

logger = get_logger("search_tool")


class _UnavailableSearchTool(BaseTool):
    name: str = "Web Search"
    description: str = "Search the web for company and leadership information."

    def _run(self, query: str = "", **kwargs) -> str:
        return "ERROR: Web search unavailable. SERPER_API_KEY is not configured in .env"


if SERPER_API_KEY:
    from crewai_tools import SerperDevTool

    os.environ["SERPER_API_KEY"] = SERPER_API_KEY
    logger.info("Serper search tool initialized")
    web_search_tool = SerperDevTool()
else:
    logger.warning("SERPER_API_KEY not set — web search will fail until configured")
    web_search_tool = _UnavailableSearchTool()
