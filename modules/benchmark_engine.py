"""
Benchmark Engine Module
Handles Geekbench 6 CLI integration and custom benchmarks
"""

import subprocess
import json
import time
import multiprocessing
from typing import Dict, Optional
from utils.logger import setup_logger
import config

logger = setup_logger(__name__)

class BenchmarkEngine:
    """Benchmark engine for performance testing"""
    
    def __init__(self):
        self.results = {}
        logger.info("Benchmark Engine initialized")
    
    def run_userbenchmark(self, custom_path: Optional[str] = None) -> bool:
        """
        Launch UserBenchmark executable
        
        Args:
            custom_path: Optional path to UserBenchMark.exe
            
        Returns:
            bool: True if launched successfully, False otherwise
        """
        import os
        path = custom_path or config.USERBENCHMARK_PATH
        
        if not path or not os.path.exists(path):
            logger.error(f"UserBenchmark not found at: {path}")
            return False
            
        try:
            logger.info(f"Launching UserBenchmark: {path}")
            # Launch and return immediately, don't wait as it opens a browser
            subprocess.Popen([path], cwd=os.path.dirname(path))
            return True
        except Exception as e:
            logger.error(f"Failed to launch UserBenchmark: {e}")
            return False

    def run_hwinfo(self, custom_path: Optional[str] = None) -> bool:
        """
        Launch HWiNFO64 executable
        
        Args:
            custom_path: Optional path to HWiNFO64.exe
            
        Returns:
            bool: True if launched successfully, False otherwise
        """
        import os
        path = custom_path or config.HWINFO_PATH
        
        if not path or not os.path.exists(path):
            logger.error(f"HWiNFO not found at: {path}")
            return False
            
        try:
            logger.info(f"Launching HWiNFO: {path}")
            # Use os.startfile on Windows to trigger UAC prompt correctly
            if os.name == 'nt':
                os.startfile(path)
            else:
                subprocess.Popen([path], cwd=os.path.dirname(path))
            return True
        except Exception as e:
            logger.error(f"Failed to launch HWiNFO: {e}")
            return False

    def run_novabench(self, custom_path: Optional[str] = None) -> bool:
        """
        Launch Novabench executable
        
        Args:
            custom_path: Optional path to Novabench.exe
            
        Returns:
            bool: True if launched successfully, False otherwise
        """
        import os
        path = custom_path or config.NOVABENCH_PATH
        
        if not path or not os.path.exists(path):
            logger.error(f"Novabench not found at: {path}")
            return False
            
        try:
            logger.info(f"Launching Novabench: {path}")
            if os.name == 'nt':
                os.startfile(path)
            else:
                subprocess.Popen([path], cwd=os.path.dirname(path))
            return True
        except Exception as e:
            logger.error(f"Failed to launch Novabench: {e}")
            return False

