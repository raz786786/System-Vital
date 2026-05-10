"""
Novabench Installation Manager
Handles detection, download, and path management for Novabench
"""

import os
import sys
import json
import subprocess
import webbrowser
import winreg
from typing import Optional
from pathlib import Path

# Download URL for Novabench installer
NOVABENCH_DOWNLOAD_URL = "https://cdn.novabench.net/novabench.msi"


class NovabenchManager:
    """Manages Novabench installation detection and launching"""
    
    def __init__(self, config_file: str):
        """
        Initialize the Novabench Manager
        
        Args:
            config_file: Path to the JSON config file for storing Novabench path
        """
        self.config_file = config_file
        
    def detect_installation(self) -> Optional[str]:
        """
        Detect if Novabench is installed and return its path
        
        Returns:
            Path to Novabench.exe if found, None otherwise
        """
        # 1. Check saved config first
        saved_path = self.load_installation_path()
        if saved_path and os.path.exists(saved_path):
            return saved_path
        
        # 2. Check registry
        registry_path = self._check_registry()
        if registry_path:
            self.save_installation_path(registry_path)
            return registry_path
        
        # 3. Check common installation paths
        common_path = self._check_common_paths()
        if common_path:
            self.save_installation_path(common_path)
            return common_path
        
        return None
    
    def _check_registry(self) -> Optional[str]:
        """Check Windows registry for Novabench installation"""
        registry_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Novabench"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Novabench"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Novabench"),
        ]
        
        for hkey, subkey in registry_keys:
            try:
                with winreg.OpenKey(hkey, subkey) as key:
                    install_path, _ = winreg.QueryValueEx(key, "InstallPath")
                    exe_path = os.path.join(install_path, "Novabench.exe")
                    if os.path.exists(exe_path):
                        return exe_path
            except (FileNotFoundError, OSError):
                continue
        
        return None
    
    def _check_common_paths(self) -> Optional[str]:
        """Check common installation directories for Novabench"""
        common_dirs = [
            r"C:\Program Files\Novabench",
            r"C:\Program Files (x86)\Novabench",
            os.path.expanduser(r"~\AppData\Local\Programs\Novabench"),
        ]
        
        for directory in common_dirs:
            exe_path = os.path.join(directory, "Novabench.exe")
            if os.path.exists(exe_path):
                return exe_path
        
        return None
    
    def open_download_page(self) -> bool:
        """
        Open the Novabench download URL in the default browser
        
        Returns:
            True if the URL was opened successfully, False otherwise
        """
        try:
            webbrowser.open(NOVABENCH_DOWNLOAD_URL)
            return True
        except Exception:
            return False
    
    def get_installation_path(self) -> Optional[str]:
        """
        Get the current Novabench installation path
        
        Returns:
            Path to Novabench.exe if found, None otherwise
        """
        return self.detect_installation()
    
    def save_installation_path(self, path: str) -> None:
        """
        Save the Novabench installation path to config file
        
        Args:
            path: Full path to Novabench.exe
        """
        from datetime import datetime
        
        config_data = {
            "installation_path": path,
            "last_checked": datetime.now().isoformat(),
            "is_installed": True
        }
        
        # Ensure config directory exists
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def load_installation_path(self) -> Optional[str]:
        """
        Load the saved Novabench installation path from config file
        
        Returns:
            Saved path if exists and valid, None otherwise
        """
        if not os.path.exists(self.config_file):
            return None
        
        try:
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
                path = config_data.get("installation_path")
                if path and os.path.exists(path):
                    return path
        except (json.JSONDecodeError, KeyError):
            pass
        
        return None
    
    def launch_novabench(self) -> bool:
        """
        Launch Novabench application
        
        Returns:
            True if launch succeeded, False otherwise
        """
        path = self.get_installation_path()
        if not path:
            return False
        
        try:
            subprocess.Popen(path)
            return True
        except Exception:
            return False
