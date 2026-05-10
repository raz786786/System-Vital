"""
AI Chat Engine — Handles multi-provider integration and dynamic tool recommendation.
"""

import re
import json
import config
from utils.logger import setup_logger
from engine.ai_providers import get_provider, AI_PROVIDERS

logger = setup_logger(__name__)

class AIChatEngine:
    def __init__(self, hardware_data=None):
        self.hardware_data = hardware_data or {}
        self.history = []  # Generic format: [{"role": "user", "parts": [{"text": "..."}]}]
        self.current_provider_id = config.CHAT_PROVIDER
        self.current_model_id = config.CHAT_MODEL
        self._init_history()

    def _init_history(self):
        sys_prompt = self._build_system_prompt()
        self.history = [
            {"role": "user", "parts": [{"text": sys_prompt}]},
            {"role": "model", "parts": [{"text": "Understood. I am System Vital AI, ready to assist."}]},
        ]

    def _build_system_prompt(self) -> str:
        from utilities import ALL_UTILITIES
        tools_list = [
            {"id": u["id"], "name": u["name"], "desc": u["desc"], "category": u["category"]}
            for u in ALL_UTILITIES
        ]
        
        hw_str = "Unknown"
        if self.hardware_data:
            cpu = self.hardware_data.get("cpu", {}).get("name", "Unknown CPU")
            ram = f'{self.hardware_data.get("ram", {}).get("total_gb", 0):.1f} GB'
            gpu = " / ".join(g.get("name", "") for g in self.hardware_data.get("gpu", []))
            os_v = self.hardware_data.get("os", {}).get("version", "Unknown OS")
            hw_str = f"OS: {os_v}\nCPU: {cpu}\nRAM: {ram}\nGPU: {gpu}"

        return f"""
You are System Vital AI, an expert Windows hardware diagnostic and optimisation assistant.

USER HARDWARE CONTEXT:
{hw_str}

AVAILABLE TOOLS (one-click utilities built into this app):
{json.dumps(tools_list, indent=2)}

INSTRUCTIONS:
1. Be concise, helpful, and technically accurate.
2. When the user's problem can be solved by an AVAILABLE TOOL, recommend it
   by placing its ID on its own line wrapped in a tag: [TOOL:tool_id]
3. If the user attaches a file (available only on Gemini), analyse it carefully.
"""

    def send_message(self, text: str, file_path: str = None, provider_id=None, model_id=None) -> dict:
        p_id = provider_id or config.CHAT_PROVIDER
        m_id = model_id or config.CHAT_MODEL
        
        provider = get_provider(p_id)
        if not provider:
            return {"response": "❌ Error: Invalid AI Provider selected.", "tools": []}

        try:
            parts = []
            if file_path and p_id == "gemini":
                # Special handling for Gemini file uploads
                from google import genai
                client = genai.Client(api_key=config.GEMINI_API_KEY)
                uploaded = client.files.upload(file=file_path)
                parts.append(uploaded)
            
            if text:
                parts.append({"text": text})
            
            self.history.append({"role": "user", "parts": parts})
            
            logger.info("Sending message to %s (%s)…", p_id, m_id)
            resp_text = provider.chat(self.history, m_id)
            
            self.history.append({"role": "model", "parts": [{"text": resp_text}]})
            clean_text, tools = self._parse_tools(resp_text)
            
            return {"response": clean_text.strip(), "tools": tools}

        except Exception as exc:
            logger.error(f"AI Engine Error ({p_id}): {exc}")
            if self.history and self.history[-1].get("role") == "user":
                self.history.pop()
            return {"response": f"❌ AI error: {exc}", "tools": []}

    def _parse_tools(self, text: str):
        from utilities import get_utility_by_id
        pattern = r"\[TOOL:(.*?)\]"
        tools = []
        for m in re.finditer(pattern, text):
            util = get_utility_by_id(m.group(1).strip())
            if util:
                tools.append(util)
        clean = re.sub(pattern, "", text)
        return clean, tools

    def clear_history(self):
        self._init_history()

def validate_provider_key(provider_id, api_key):
    from engine.ai_providers import GeminiProvider, OpenAICompatProvider, AI_PROVIDERS
    p_meta = AI_PROVIDERS.get(provider_id)
    if not p_meta: return False, "Invalid provider"
    
    if provider_id == "gemini":
        prov = GeminiProvider(api_key)
    elif "base_url" in p_meta:
        prov = OpenAICompatProvider(p_meta["base_url"], api_key)
    else:
        return False, "Provider validation not implemented for this type"
        
    return prov.validate_key(api_key)
