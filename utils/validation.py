"""Input validation and configuration checks."""

import re
from urllib.parse import urlparse

from config.settings import (
    LLM_PROVIDER,
    ANTHROPIC_API_KEY,
    OPENAI_API_KEY,
    SERPER_API_KEY,
)
from utils.errors import ConfigurationError, ValidationError


_URL_RE = re.compile(
    r"^https?://"
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,63}\.?|"
    r"localhost|"
    r"\d{1,3}(?:\.\d{1,3}){3})"
    r"(?::\d+)?"
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)


def normalize_website(url: str) -> str:
    """Normalize and validate a website URL. Empty string is allowed."""
    url = (url or "").strip()
    if not url:
        return ""

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValidationError("Please enter a valid website URL (e.g. https://shopify.com).")

    if not _URL_RE.match(url):
        raise ValidationError("Website URL format is invalid. Use a full domain like https://example.com.")

    return url.rstrip("/")


def validate_company_name(name: str) -> str:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Company name is required.")
    if len(name) < 2:
        raise ValidationError("Company name must be at least 2 characters.")
    return name


def validate_api_configuration() -> None:
    """Ensure required API keys are present before starting a long pipeline run."""
    if LLM_PROVIDER == "anthropic":
        if not ANTHROPIC_API_KEY:
            raise ConfigurationError(
                "Anthropic API key is missing. Set ANTHROPIC_API_KEY in your .env file."
            )
    else:
        if not OPENAI_API_KEY:
            raise ConfigurationError(
                "OpenAI API key is missing. Set OPENAI_API_KEY in your .env file."
            )

    if not SERPER_API_KEY:
        raise ConfigurationError(
            "Serper API key is missing. Set SERPER_API_KEY in your .env file for web search."
        )
