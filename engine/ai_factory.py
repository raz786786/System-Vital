"""
AI PROVIDER FACTORY
Unified entry point for AI analysis providers.
"""

from typing import Optional
from engine.ai_providers import get_provider as get_raw_provider

class BaseAIProvider:
    def generate_analysis(self, prompt: str) -> str:
        raise NotImplementedError

class UnifiedAIProvider(BaseAIProvider):
    def __init__(self, provider_id: str, model_id: str):
        self.provider_id = provider_id
        self.model_id = model_id
        
    def generate_analysis(self, prompt: str) -> str:
        provider = get_raw_provider(self.provider_id)
        if not provider:
            return "Error: AI Provider not configured."
        # Wrap prompt in message format
        messages = [{"role": "user", "parts": [{"text": prompt}]}]
        return provider.chat(messages, self.model_id)

class RuleBasedProvider(BaseAIProvider):
    def generate_analysis(self, prompt: str) -> str:
        return "Rule-based analysis active (Fallback)."

class AIFactory:
    @staticmethod
    def get_provider(provider_type: str, model_id: Optional[str] = None) -> BaseAIProvider:
        import config
        p_id = provider_type.lower()
        m_id = model_id or config.CHAT_MODEL
        
        if p_id in ["gemini", "groq", "openrouter", "nvidia", "nova"]:
            return UnifiedAIProvider(p_id, m_id)
            
        return RuleBasedProvider()
