"""
SYSTEM VITAL SYSTEM INFORMATION UTILITY
Deep hardware detection for CPU, GPU, RAM, and Motherboard.
"""

import wmi
import psutil
import cpuinfo
import GPUtil
import platform
from typing import Dict, List, Any

class DeepSystemInfo:
    def __init__(self):
        self._w = wmi.WMI()
        self._cpu_info = cpuinfo.get_cpu_info()
        
    def get_all(self) -> Dict[str, Any]:
        return {
            "cpu": self.get_cpu_details(),
            "gpu": self.get_gpu_details(),
            "ram": self.get_ram_details(),
            "motherboard": self.get_motherboard_details(),
            "os": self.get_os_details()
        }

    def get_cpu_details(self) -> Dict[str, Any]:
        """Deep CPU info including microcode and caches."""
        cpu = self._w.Win32_Processor()[0]
        return {
            "name": self._cpu_info.get("brand_raw", cpu.Name),
            "architecture": self._cpu_info.get("arch", "N/A"),
            "cores_physical": psutil.cpu_count(logical=False),
            "cores_logical": psutil.cpu_count(logical=True),
            "l2_cache": f"{cpu.L2CacheSize} KB" if hasattr(cpu, "L2CacheSize") else "N/A",
            "l3_cache": f"{cpu.L3CacheSize} KB" if hasattr(cpu, "L3CacheSize") else "N/A",
            "stepping": cpu.Stepping if hasattr(cpu, "Stepping") else "N/A",
            "voltage": f"{cpu.CurrentVoltage / 10 if cpu.CurrentVoltage else 0} V",
            "max_clock": f"{cpu.MaxClockSpeed} MHz",
        }

    def get_gpu_details(self) -> List[Dict[str, Any]]:
        """Deep GPU info including driver and VRAM details."""
        gpus = []
        # WMI for vendor info
        wmi_gpus = self._w.Win32_VideoController()
        # GPUtil for live telemetry
        try:
            gpu_stats = GPUtil.getGPUs()
        except:
            gpu_stats = []
            
        for i, wg in enumerate(wmi_gpus):
            g = {
                "name": wg.Name,
                "driver_version": wg.DriverVersion,
                "vram_total": f"{int(wg.AdapterRAM) / (1024**2):.0f} MB" if wg.AdapterRAM else "N/A",
                "refresh_rate": f"{wg.CurrentRefreshRate} Hz" if wg.CurrentRefreshRate else "N/A",
                "res": f"{wg.CurrentHorizontalResolution}x{wg.CurrentVerticalResolution}" if wg.CurrentHorizontalResolution else "N/A",
            }
            # Match with GPUtil if possible
            if i < len(gpu_stats):
                gs = gpu_stats[i]
                g["vram_free"] = f"{gs.memoryFree} MB"
                g["temp"] = f"{gs.temperature} °C"
                g["load"] = f"{gs.load * 100:.1f}%"
            gpus.append(g)
        return gpus

    def get_ram_details(self) -> Dict[str, Any]:
        """Deep RAM info including speed and slot population."""
        try:
            sticks = self._w.Win32_PhysicalMemory()
            total_capacity = sum(int(s.Capacity) for s in sticks) / (1024**3)
            
            stick_details = []
            for s in sticks:
                stick_details.append({
                    "capacity": f"{int(s.Capacity) / (1024**3):.1f} GB",
                    "speed": f"{s.Speed} MT/s",
                    "manufacturer": s.Manufacturer.strip(),
                    "part_number": s.PartNumber.strip(),
                    "configured_voltage": f"{int(s.ConfiguredVoltage)/1000 if hasattr(s, 'ConfiguredVoltage') else 'N/A'} V"
                })
                
            return {
                "total_gb": round(total_capacity, 1),
                "count": len(sticks),
                "sticks": stick_details,
                "virtual_mem": f"{psutil.virtual_memory().total / (1024**3):.1f} GB"
            }
        except Exception as e:
            return {"error": str(e)}

    def get_motherboard_details(self) -> Dict[str, Any]:
        """BIOS and Board info."""
        board = self._w.Win32_BaseBoard()[0]
        bios = self._w.Win32_BIOS()[0]
        return {
            "manufacturer": board.Manufacturer,
            "product": board.Product,
            "version": board.Version,
            "bios_version": bios.SMBIOSBIOSVersion,
            "bios_date": bios.ReleaseDate[:8] if bios.ReleaseDate else "N/A"
        }

    def get_os_details(self) -> Dict[str, Any]:
        return {
            "caption": platform.system() + " " + platform.release(),
            "version": platform.version(),
            "build": platform.win32_ver()[1],
            "arch": platform.machine()
        }
