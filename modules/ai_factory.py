"""
AI Analyzer Factory
Returns the active AI analyzer based on config.AI_PROVIDER setting
"""

import config
from utils.logger import setup_logger

logger = setup_logger(__name__)


def get_analyzer():
    """
    Return the active AI analyzer based on config.AI_PROVIDER
    
    Returns:
        GeminiAnalyzer or NovaAnalyzer instance
    """
    provider = getattr(config, 'AI_PROVIDER', 'nova').lower()
    
    if provider == "gemini":
        from modules.gemini_analyzer import GeminiAnalyzer
        logger.info("Using Google Gemini AI provider")
        return GeminiAnalyzer()
    else:
        from modules.nova_analyzer import NovaAnalyzer
        logger.info("Using Amazon Nova AI provider")
        return NovaAnalyzer()


def get_provider_display_name() -> str:
    """Return a human-readable name for the current AI provider"""
    provider = getattr(config, 'AI_PROVIDER', 'nova').lower()
    if provider == "gemini":
        return "Google Gemini"
    else:
        return "Amazon Nova"
