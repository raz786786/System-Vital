"""
SYSTEM VITAL TELEMETRY UTILITY
Provides real-time polling of hardware temperature, load, and clocks.
Optimized for low-overhead stress test monitoring.
"""

import os
import sys
import time
from typing import Optional, Dict

try:
    import psutil
except ImportError:
    psutil = None

try:
    import wmi
    WMI_OK = True
except ImportError:
    WMI_OK = False

try:
    import GPUtil
except ImportError:
    GPUtil = None

IS_WINDOWS = sys.platform == "win32"

class TelemetrySampler:
    def __init__(self):
        self._w = wmi.WMI(namespace="root\\wmi") if (IS_WINDOWS and WMI_OK) else None
        self._last_cpu_pct = 0
        
    def get_cpu_temp(self) -> Optional[float]:
        """Get max CPU temperature in Celsius."""
        if IS_WINDOWS and self._w:
            try:
                sensors = self._w.MSAcpi_ThermalZoneTemperature()
                if sensors:
                    return max((s.CurrentTemperature / 10.0) - 273.15 for s in sensors)
            except:
                pass
        
        if psutil and hasattr(psutil, "sensors_temperatures"):
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    # Look for common CPU temp keys
                    for key in ['coretemp', 'k10temp', 'cpu_thermal', 'pkg-temp-0']:
                        if key in temps:
                            return max(s.current for s in temps[key])
            except:
                pass
        return None

    def get_cpu_load(self) -> float:
        if psutil:
            return psutil.cpu_percent(interval=None)
        return 0.0

    def get_ram_usage(self) -> Dict[str, float]:
        if psutil:
            vm = psutil.virtual_memory()
            return {
                "used_gb": vm.used / (1024**3),
                "total_gb": vm.total / (1024**3),
                "percent": vm.percent
            }
        return {"used_gb": 0, "total_gb": 0, "percent": 0}

    def get_gpu_telemetry(self) -> Dict[str, any]:
        """Get GPU temp and load if available."""
        if GPUtil:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    g = gpus[0]
                    return {
                        "name": g.name,
                        "temp_c": g.temperature,
                        "load_pct": g.load * 100,
                        "vram_used_mb": g.memoryUsed
                    }
            except:
                pass
        return {}

    def get_all(self) -> Dict[str, any]:
        """Fetch all telemetry in one pass."""
        return {
            "cpu_temp": self.get_cpu_temp(),
            "cpu_load": self.get_cpu_load(),
            "ram": self.get_ram_usage(),
            "gpu": self.get_gpu_telemetry(),
            "timestamp": time.time()
        }
