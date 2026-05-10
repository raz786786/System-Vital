"""
Configuration file for System Vital
"""

import os
import sys

# Application Settings
APP_NAME = "System Vital"
APP_VERSION = "1.0.0"
APP_AUTHOR = 'made by "AHMED ZUBAIR RAO raoa87442@gamil.com" "SHAYAN HUMAYUN shanooo773@gmail.com" "MUHAMMAD AHMAD ahmadrind20@gmail.com"'

# Paths - Handle both normal and PyInstaller bundled execution
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
    RESOURCE_DIR = getattr(sys, '_MEIPASS', APP_DIR)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    RESOURCE_DIR = APP_DIR

BASE_DIR = APP_DIR

def get_resource_path(relative_path: str) -> str:
    path = os.path.join(APP_DIR, relative_path)
    if os.path.exists(path):
        return path
    return os.path.join(RESOURCE_DIR, relative_path)
    
DATA_DIR = os.path.join(APP_DIR, "data")
ASSETS_DIR = get_resource_path("assets")
LOG_DIR = os.path.join(APP_DIR, "logs")

# Database
DATABASE_PATH = os.path.join(DATA_DIR, "hardware_db.sqlite")

# AI Provider Configuration
CHAT_PROVIDER = "gemini"
CHAT_MODEL = "gemini-2.0-flash"
ENABLED_PROVIDERS = ["gemini", "groq", "openrouter", "nvidia", "nova"]
AI_PROVIDER = "gemini" # Legacy/Fallback

# API Keys
GEMINI_API_KEY = ""
GROQ_API_KEY = ""
OPENROUTER_API_KEY = ""
NVIDIA_API_KEY = ""
NOVA_API_KEY = ""

# Model Defaults
GEMINI_MODEL_NAME = "gemini-2.0-flash"
NOVA_MODEL_NAME = "amazon.nova-lite-v1:0"
NOVA_API_BASE_URL = "https://api.nova.amazon.com/v1"

# Benchmark Settings
HWINFO_PATH = os.path.join(get_resource_path("hwinfo"), "HWiNFO64.exe")
NOVABENCH_CONFIG_FILE = os.path.join(DATA_DIR, "novabench_config.json")
ENABLE_CLIPBOARD_MONITOR = True
CLIPBOARD_CHECK_INTERVAL = 1000

# Hardware Detection Settings
ENABLE_DEEP_SCAN = True
SCAN_INTERVAL = 2

# Temperature Thresholds (Celsius)
CPU_TEMP_WARNING = 80
CPU_TEMP_CRITICAL = 90
GPU_TEMP_WARNING = 80
GPU_TEMP_CRITICAL = 85

# Online Comparison Settings
ENABLE_ONLINE_COMPARISON = True
CACHE_EXPIRY_DAYS = 7
REQUEST_TIMEOUT = 10
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Benchmark URLs
PASSMARK_CPU_URL = "https://www.cpubenchmark.net/cpu.php?cpu="
PASSMARK_GPU_URL = "https://www.videocardbenchmark.net/gpu.php?gpu="
TECHPOWERUP_GPU_URL = "https://www.techpowerup.com/gpu-specs/"

# GUI Settings
THEME = "dark"
ACCENT_COLOR = "#3b82f6"
BG_COLOR_DARK = "#0f1117"
BG_COLOR_LIGHT = "#f8fafc"
TEXT_SECONDARY = "#8b90b8"
NAV_BG_COLOR = "#0f1117"
USER_PROFILE = "Power User"

# ── Theme-aware color helpers ──────────────────────────────
# These MUST be called (not read as variables) so they
# always resolve against the current value of THEME.
def get_card_bg():
    return "#1e2130" if THEME == "dark" else "#ffffff"

def get_text_color():
    return "#e8eaf6" if THEME == "dark" else "#1e293b"

def get_text_muted():
    return "#8b90b8" if THEME == "dark" else "#64748b"

def get_border_color():
    return "#2d3150" if THEME == "dark" else "#e2e8f0"

def get_bg_main():
    return BG_COLOR_DARK if THEME == "dark" else BG_COLOR_LIGHT
WINDOW_WIDTH = 1100
WINDOW_HEIGHT = 750

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = os.path.join(LOG_DIR, "hardware_diagnostic.log")

# Diagnostic Settings
RUN_DIAGNOSTICS_ON_STARTUP = True
ENABLE_AUTOMATED_FIXES = False

# Scoring Weights
SCORE_WEIGHTS = {
    "cpu": 0.30,
    "gpu": 0.35,
    "ram": 0.15,
    "storage": 0.10,
    "motherboard": 0.05,
    "overall_balance": 0.05
}

# Score Tiers
SCORE_TIER_BEST = 90
SCORE_TIER_AVERAGE = 60

# Dynamic Loading from user_settings.json
def load_user_settings():
    global CHAT_PROVIDER, CHAT_MODEL, ENABLED_PROVIDERS
    global GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY, NVIDIA_API_KEY, NOVA_API_KEY
    global ACCENT_COLOR, THEME, USER_PROFILE
    
    settings_path = os.path.join(DATA_DIR, "user_settings.json")
    if os.path.exists(settings_path):
        try:
            import json
            with open(settings_path, 'r') as f:
                data = json.load(f)
                CHAT_PROVIDER = data.get("CHAT_PROVIDER", CHAT_PROVIDER)
                CHAT_MODEL = data.get("CHAT_MODEL", CHAT_MODEL)
                ENABLED_PROVIDERS = data.get("ENABLED_PROVIDERS", ENABLED_PROVIDERS)
                
                GEMINI_API_KEY = data.get("GEMINI_API_KEY", GEMINI_API_KEY)
                GROQ_API_KEY = data.get("GROQ_API_KEY", GROQ_API_KEY)
                OPENROUTER_API_KEY = data.get("OPENROUTER_API_KEY", OPENROUTER_API_KEY)
                NVIDIA_API_KEY = data.get("NVIDIA_API_KEY", NVIDIA_API_KEY)
                NOVA_API_KEY = data.get("NOVA_API_KEY", NOVA_API_KEY)
                
                ACCENT_COLOR = data.get("ACCENT_COLOR", ACCENT_COLOR)
                THEME = data.get("THEME", THEME)
                USER_PROFILE = data.get("USER_PROFILE", USER_PROFILE)
        except:
            pass

# Create necessary directories
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

load_user_settings()
