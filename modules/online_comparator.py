import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import json
import os
from typing import Dict, Optional, List
from utils.logger import setup_logger
from utils.helpers import clean_component_name
import config

logger = setup_logger(__name__)

class OnlineComparator:
    """Compare hardware with online databases and local reference benchmarks."""
    
    def __init__(self):
        self.db_path = config.DATABASE_PATH
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': config.USER_AGENT})
        self.reference_data = self._load_reference_data()
        self._init_database()
        logger.info("Online Comparator initialized")
    
    def _load_reference_data(self) -> Dict:
        """Load the local reference hardware database."""
        try:
            ref_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "reference_scores.json")
            if os.path.exists(ref_path):
                with open(ref_path, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading reference data: {e}")
        return {}

    def _init_database(self):
        """Initialize local database for caching"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cpus (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model TEXT UNIQUE,
                    passmark_score INTEGER,
                    last_updated INTEGER
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS gpus (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model TEXT UNIQUE,
                    passmark_score INTEGER,
                    last_updated INTEGER
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")

    def get_global_standing(self, component: str, score: int) -> Dict:
        """
        Determine where a score stands relative to the global reference data.
        """
        comp_type = component.replace("_Extended", "").upper()
        if comp_type not in self.reference_data:
            return {"percentile": 50, "tier": "Unknown", "rank": "N/A"}

        ref = self.reference_data[comp_type]
        tiers = ref.get("tiers", {})
        
        # Find tier
        current_tier = "Legacy"
        for t_name, limits in tiers.items():
            if limits["min"] <= score <= limits["max"]:
                current_tier = t_name
                break
        else:
            if score > 75000: current_tier = "Flagship"

        # Calculate percentile (approximate)
        percentile = min(99, int((score / 100000) * 100))
        
        # Get flagship comparison
        flagships = [name for name, d in ref.get("reference_hardware", {}).items() if d.get("score", 0) > 85000]
        flagship_name = flagships[0] if flagships else "Flagship"
        flagship_score = ref.get("reference_hardware", {}).get(flagship_name, {}).get("score", 100000)
        
        perf_vs_flagship = (score / flagship_score) * 100

        return {
            "percentile": percentile,
            "tier": current_tier,
            "vs_flagship": round(perf_vs_flagship, 1),
            "flagship_name": flagship_name,
            "examples": tiers.get(current_tier, {}).get("examples", [])
        }

    def compare_to_flagship(self, component: str, score: int) -> Dict:
        """Specific comparison against the top-tier hardware in our database."""
        standing = self.get_global_standing(component, score)
        return {
            "status": f"{standing['vs_flagship']}% of {standing['flagship_name']}",
            "severity": "ok" if standing["vs_flagship"] > 70 else "warning",
            "advice": f"Your hardware is in the {standing['tier']} tier. " + 
                      (f"It performs at {standing['vs_flagship']}% of a {standing['flagship_name']}." if standing['vs_flagship'] < 90 else "Top-tier performance detected!")
        }

    def get_ranking_data(self, component: str) -> List[Dict]:
        """Returns a list of reference hardware for comparison charts."""
        comp_type = component.replace("_Extended", "").upper()
        if comp_type not in self.reference_data:
            return []
            
        ref_hw = self.reference_data[comp_type].get("reference_hardware", {})
        return [{"name": name, "score": d["score"]} for name, d in ref_hw.items()]
