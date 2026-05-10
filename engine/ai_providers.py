"""
System Vital AI Provider Registry
Handles multiple providers (Gemini, Groq, OpenRouter, NVIDIA, Nova)
using a unified adapter pattern.
"""

import os
import json
import config
from utils.logger import setup_logger

logger = setup_logger(__name__)

# --- Provider Metadata ---
AI_PROVIDERS = {
    "gemini": {
        "name": "Google Gemini",
        "get_key_url": "https://aistudio.google.com/apikey",
        "models": [
            {"id": "gemini-2.0-flash",      "label": "Gemini 2.0 Flash",      "tag": "Free"},
            {"id": "gemini-2.0-flash-lite", "label": "Gemini 2.0 Flash Lite", "tag": "Free"},
        ],
    },
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "get_key_url": "https://console.groq.com/keys",
        "models": [
            {"id": "llama-3.3-70b-versatile",  "label": "Llama 3.3 70B", "tag": "Free"},
            {"id": "llama-3.1-8b-instant",      "label": "Llama 3.1 8B",    "tag": "Free"},
            {"id": "qwen-qwq-32b",              "label": "Qwen QwQ 32B",            "tag": "Free"},
        ],
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "get_key_url": "https://openrouter.ai/keys",
        "models": [
            {"id": "google/gemma-3-27b-it:free",              "label": "Gemma 3 27B",    "tag": "Free"},
            {"id": "meta-llama/llama-3.2-3b-instruct:free",   "label": "Llama 3.2 3B",   "tag": "Free"},
            {"id": "openrouter/auto",                         "label": "Auto (Free)",    "tag": "Free"},
        ],
    },
    "nvidia": {
        "name": "NVIDIA NIM API",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "get_key_url": "https://build.nvidia.com/models",
        "models": [
            {"id": "nvidia/llama-3.1-nemotron-nano-vl-8b-v1",     "label": "Nemotron Nano 8B",  "tag": "Free"},
            {"id": "meta/llama-3.1-8b-instruct",                   "label": "Llama 3.1 8B",      "tag": "Free"},
            {"id": "deepseek-ai/deepseek-r1-distill-llama-8b",     "label": "DeepSeek R1 8B",    "tag": "Free"},
        ],
    },
    "nova": {
        "name": "Amazon Nova",
        "base_url": "https://api.nova.amazon.com/v1",
        "get_key_url": "https://api.nova.amazon.com",
        "models": [
            {"id": "nova-lite-v1",  "label": "Nova Lite",  "tag": "Free"},
            {"id": "nova-micro-v1", "label": "Nova Micro", "tag": "Free"},
        ],
    },
}

# --- Adapters ---

class BaseProvider:
    def chat(self, messages, model):
        raise NotImplementedError
    def validate_key(self, key):
        raise NotImplementedError

class OpenAICompatProvider(BaseProvider):
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key
        self._client = None

    def _get_client(self):
        if not self._client:
            from openai import OpenAI
            self._client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        return self._client

    def chat(self, messages, model):
        try:
            client = self._get_client()
            # Convert Gemini format (role: user/model) to OpenAI format (role: user/assistant)
            oa_messages = []
            for m in messages:
                role = "assistant" if m["role"] == "model" else m["role"]
                # Handle parts or text
                content = ""
                if "parts" in m:
                    content = " ".join(p.get("text", "") for p in m["parts"] if isinstance(p, dict))
                else:
                    content = m.get("content", "")
                oa_messages.append({"role": role, "content": content})

            response = client.chat.completions.create(
                model=model,
                messages=oa_messages,
                temperature=0.7,
                max_tokens=2048
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI Compat Error ({self.base_url}): {e}")
            return f"❌ Error: {str(e)}"

    def validate_key(self, key):
        try:
            from openai import OpenAI
            client = OpenAI(base_url=self.base_url, api_key=key)
            # Just try to list models or do a tiny completion
            client.models.list()
            return True, "✅ Key validated successfully!"
        except Exception as e:
            return False, f"❌ Validation failed: {str(e)}"

class GeminiProvider(BaseProvider):
    def __init__(self, api_key):
        self.api_key = api_key
        self._client = None

    def _get_client(self):
        if not self._client:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def chat(self, messages, model):
        try:
            client = self._get_client()
            # Gemini SDK takes history directly
            response = client.models.generate_content(
                model=model,
                contents=messages
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini Error: {e}")
            return f"❌ Error: {str(e)}"

    def validate_key(self, key):
        try:
            from google import genai
            client = genai.Client(api_key=key)
            client.models.generate_content(model="gemini-2.0-flash", contents="Say OK")
            return True, "✅ Key validated successfully!"
        except Exception as e:
            return False, f"❌ Validation failed: {str(e)}"

# --- Factory ---

def get_provider(provider_id):
    if provider_id == "gemini":
        return GeminiProvider(config.GEMINI_API_KEY)
    elif provider_id in AI_PROVIDERS:
        p_meta = AI_PROVIDERS[provider_id]
        if "base_url" in p_meta:
            key = getattr(config, f"{provider_id.upper()}_API_KEY", "")
            return OpenAICompatProvider(p_meta["base_url"], key)
    return None
