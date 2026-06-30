import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY", "")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_MODEL    = os.getenv("LLM_MODEL", "gpt-4o-mini")

DB_PATH      = os.getenv("DB_PATH", "database/sales_leads.db")
REPORTS_DIR  = os.getenv("REPORTS_DIR", "reports/output")

HEADLESS_BROWSER = os.getenv("HEADLESS_BROWSER", "true").lower() == "true"
BROWSER_TIMEOUT  = int(os.getenv("BROWSER_TIMEOUT", "30000"))

MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "10"))
VERBOSE        = os.getenv("VERBOSE", "true").lower() == "true"