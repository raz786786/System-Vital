"""
Hardware Detection Module
Provides deep-level hardware detection for CPU, GPU, RAM, Storage, Motherboard, and more
"""

import platform
import psutil
from typing import Dict, List, Optional
from utils.logger import setup_logger
from utils.helpers import format_bytes, format_frequency, clean_component_name

logger = setup_logger(__name__)

class HardwareDetector:
    """Main hardware detection class"""
    
    def __init__(self):
        self.system_info = {}
        logger.info("Hardware Detector initialized")
    
    def get_all_hardware(self) -> Dict:
        """
        Get all hardware information
        
        Returns:
            Dict: Complete hardware information
        """
        logger.info("Starting comprehensive hardware detection...")
        
        self.system_info = {
            'cpu': self.get_cpu_info(),
            'gpu': self.get_gpu_info(),
            'ram': self.get_ram_info(),
            'storage': self.get_storage_info(),
            'motherboard': self.get_motherboard_info(),
            'system': self.get_system_info(),
            'network': self.get_network_info(),
        }
        
        logger.info("Hardware detection completed")
        return self.system_info
    
    def get_cpu_info(self) -> Dict:
        """Get detailed CPU information"""
        logger.info("Detecting CPU...")
        
        try:
            # Get CPU info from cpuinfo library
            import cpuinfo
            cpu_data = cpuinfo.get_cpu_info()
            
            # Get additional info from psutil
            cpu_freq = psutil.cpu_freq()
            cpu_count = psutil.cpu_count(logical=False)
            cpu_threads = psutil.cpu_count(logical=True)
            
            # Try to get temperature (may not work on all systems)
            temps = psutil.sensors_temperatures() if hasattr(psutil, 'sensors_temperatures') else {}
            cpu_temp = None
            if temps and 'coretemp' in temps:
                cpu_temp = max([t.current for t in temps['coretemp']])
            
            info = {
                'name': cpu_data.get('brand_raw', 'Unknown CPU'),
                'clean_name': clean_component_name(cpu_data.get('brand_raw', 'Unknown CPU')),
                'architecture': cpu_data.get('arch', 'Unknown'),
                'cores': cpu_count,
                'threads': cpu_threads,
                'base_frequency': cpu_freq.current if cpu_freq else 0,
                'max_frequency': cpu_freq.max if cpu_freq else 0,
                'current_frequency': cpu_freq.current if cpu_freq else 0,
                'l2_cache': cpu_data.get('l2_cache_size', 0),
                'l3_cache': cpu_data.get('l3_cache_size', 0),
                'flags': cpu_data.get('flags', []),
                'temperature': cpu_temp,
                'usage_percent': psutil.cpu_percent(interval=1),
                'usage_per_core': psutil.cpu_percent(interval=1, percpu=True),
            }
            
            logger.info(f"CPU detected: {info['name']}")
            return info
            
        except Exception as e:
            logger.error(f"Error detecting CPU: {e}")
            return {'name': 'Unknown', 'error': str(e)}
    
    def get_gpu_info(self) -> List[Dict]:
        """Get detailed GPU information"""
        logger.info("Detecting GPU(s)...")
        
        gpus = []
        
        try:
            # Try WMI first (Windows)
            if platform.system() == 'Windows':
                import wmi
                try:
                    import pythoncom
                    pythoncom.CoInitialize()
                except:
                    pass
                
                c = wmi.WMI()
                wmi_gpus = c.Win32_VideoController()
                
                if wmi_gpus:
                    for gpu in wmi_gpus:
                        name = getattr(gpu, 'Name', None) or getattr(gpu, 'Caption', None) or getattr(gpu, 'Description', None)
                        if not name or 'Unknown' in name:
                            continue
                            
                        vram_val = getattr(gpu, 'AdapterRAM', 0)
                        if vram_val:
                            vram_val = int(vram_val) & 0xFFFFFFFF
                        else:
                            vram_val = 0
                            
                        gpu_info = {
                            'name': name,
                            'clean_name': clean_component_name(name),
                            'driver_version': getattr(gpu, 'DriverVersion', 'Unknown'),
                            'driver_date': getattr(gpu, 'DriverDate', None),
                            'vram': vram_val,
                            'vram_formatted': format_bytes(vram_val) if vram_val > 0 else 'Unknown VRAM',
                            'status': getattr(gpu, 'Status', 'Unknown'),
                            'video_processor': getattr(gpu, 'VideoProcessor', 'Unknown'),
                        }
                        
                        # NVIDIA specifics... (keep existing logic)
                        try:
                            import pynvml
                            pynvml.nvmlInit()
                            device_count = pynvml.nvmlDeviceGetCount()
                            for i in range(device_count):
                                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                                nv_name = pynvml.nvmlDeviceGetName(handle)
                                if isinstance(nv_name, bytes): nv_name = nv_name.decode('utf-8')
                                
                                if clean_component_name(name) in clean_component_name(nv_name) or clean_component_name(nv_name) in clean_component_name(name):
                                    gpu_info.update({
                                        'temperature': pynvml.nvmlDeviceGetTemperature(handle, 0),
                                        'utilization': pynvml.nvmlDeviceGetUtilizationRates(handle).gpu,
                                        'memory_utilization': pynvml.nvmlDeviceGetUtilizationRates(handle).memory,
                                        'power_usage': pynvml.nvmlDeviceGetPowerUsage(handle) / 1000,
                                        'manufacturer': 'NVIDIA',
                                    })
                                    break
                            pynvml.nvmlShutdown()
                        except:
                            pass
                        
                        gpus.append(gpu_info)
                        logger.info(f"GPU detected via WMI: {name}")
                
                try:
                    import pythoncom
                    pythoncom.CoUninitialize()
                except:
                    pass
            
            # Fallback to WMIC command line if gpus list is still empty or contains errors
            if not gpus or any('Unknown' in g.get('name', '') for g in gpus):
                try:
                    import subprocess
                    cmd = 'wmic path Win32_VideoController get Name,AdapterRAM,DriverVersion /format:list'
                    result = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT)
                    
                    current_gpu = {}
                    for line in result.splitlines():
                        if '=' in line:
                            k, v = line.split('=', 1)
                            k, v = k.strip(), v.strip()
                            if k == 'Name' and v: current_gpu['name'] = v
                            if k == 'AdapterRAM' and v: current_gpu['vram'] = int(v) & 0xFFFFFFFF
                            if k == 'DriverVersion' and v: current_gpu['driver_version'] = v
                        elif not line.strip() and current_gpu.get('name'):
                            # Process the collected GPU info
                            vram = current_gpu.get('vram', 0)
                            gpus.append({
                                'name': current_gpu['name'],
                                'clean_name': clean_component_name(current_gpu['name']),
                                'vram': vram,
                                'vram_formatted': format_bytes(vram) if vram > 0 else 'Unknown VRAM',
                                'driver_version': current_gpu.get('driver_version', 'Unknown'),
                            })
                            current_gpu = {}
                    
                    # Add last one if exists
                    if current_gpu.get('name'):
                        vram = current_gpu.get('vram', 0)
                        gpus.append({
                            'name': current_gpu['name'],
                            'clean_name': clean_component_name(current_gpu['name']),
                            'vram': vram,
                            'vram_formatted': format_bytes(vram) if vram > 0 else 'Unknown VRAM',
                            'driver_version': current_gpu.get('driver_version', 'Unknown'),
                        })
                except Exception as e:
                    logger.warning(f"WMIC fallback failed: {e}")

            # Fallback to GPUtil (mostly NVIDIA)
            if not gpus or all('Unknown' in g.get('name', '') for g in gpus):
                try:
                    import GPUtil
                    gpu_list = GPUtil.getGPUs()
                    for gpu in gpu_list:
                        gpus.append({
                            'name': gpu.name,
                            'clean_name': clean_component_name(gpu.name),
                            'vram': gpu.memoryTotal * 1024 * 1024,
                            'vram_formatted': f"{gpu.memoryTotal} MB",
                            'temperature': gpu.temperature,
                            'utilization': gpu.load * 100,
                            'memory_utilization': gpu.memoryUtil * 100,
                        })
                except:
                    pass
            
        except Exception as e:
            logger.error(f"Error detecting GPU: {e}")
            gpus.append({'name': 'Unknown', 'error': str(e)})
        
        # Filter out "Unknown" entries if better ones exist
        valid_gpus = [g for g in gpus if 'Unknown' not in g.get('name', '')]
        if valid_gpus: gpus = valid_gpus
        
        logger.info(f"Final GPU detection results: {len(gpus)} found")
        
        if not gpus or (len(gpus) == 1 and 'No GPU detected' in gpus[0].get('name', '')):
            return [{'name': 'Basic Display Adapter', 'vram': 0, 'vram_formatted': 'Internal'}]
        return gpus
    
    def get_ram_info(self) -> Dict:
        """Get detailed RAM information"""
        logger.info("Detecting RAM...")
        
        try:
            mem = psutil.virtual_memory()
            
            info = {
                'total': mem.total,
                'total_formatted': format_bytes(mem.total),
                'available': mem.available,
                'available_formatted': format_bytes(mem.available),
                'used': mem.used,
                'used_formatted': format_bytes(mem.used),
                'percent_used': mem.percent,
                'modules': [],
            }
            
            # Get detailed module info on Windows
            if platform.system() == 'Windows':
                try:
                    import wmi
                    c = wmi.WMI()
                    
                    for mem_module in c.Win32_PhysicalMemory():
                        module_info = {
                            'capacity': int(mem_module.Capacity) if mem_module.Capacity else 0,
                            'capacity_formatted': format_bytes(int(mem_module.Capacity)) if mem_module.Capacity else 'Unknown',
                            'speed': int(mem_module.Speed) if mem_module.Speed else 0,
                            'speed_formatted': f"{mem_module.Speed} MHz" if mem_module.Speed else 'Unknown',
                            'manufacturer': mem_module.Manufacturer if mem_module.Manufacturer else 'Unknown',
                            'part_number': mem_module.PartNumber.strip() if mem_module.PartNumber else 'Unknown',
                            'type': self._get_memory_type(mem_module.SMBIOSMemoryType),
                        }
                        info['modules'].append(module_info)
                except Exception as e:
                    logger.warning(f"Could not get detailed RAM module info: {e}")
            
            logger.info(f"RAM detected: {info['total_formatted']}")
            return info
            
        except Exception as e:
            logger.error(f"Error detecting RAM: {e}")
            return {'total': 0, 'error': str(e)}
    
    def get_storage_info(self) -> List[Dict]:
        """Get detailed storage information"""
        logger.info("Detecting storage devices...")
        
        devices = []
        
        try:
            partitions = psutil.disk_partitions()
            
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    
                    device_info = {
                        'device': partition.device,
                        'mountpoint': partition.mountpoint,
                        'filesystem': partition.fstype,
                        'total': usage.total,
                        'total_formatted': format_bytes(usage.total),
                        'used': usage.used,
                        'used_formatted': format_bytes(usage.used),
                        'free': usage.free,
                        'free_formatted': format_bytes(usage.free),
                        'percent_used': usage.percent,
                        'type': 'Unknown',  # Will try to determine
                    }
                    
                    # Try to get SMART data
                    try:
                        from pySMART import Device
                        smart_device = Device(partition.device)
                        if smart_device:
                            device_info.update({
                                'smart_health': smart_device.assessment,
                                'smart_enabled': smart_device.smart_enabled,
                                'temperature': smart_device.temperature,
                                'model': smart_device.model,
                                'serial': smart_device.serial,
                            })
                    except:
                        pass  # SMART not available
                    
                    devices.append(device_info)
                    logger.info(f"Storage detected: {device_info['device']} ({device_info['total_formatted']})")
                    
                except PermissionError:
                    continue  # Skip inaccessible drives
                    
        except Exception as e:
            logger.error(f"Error detecting storage: {e}")
            devices.append({'device': 'Unknown', 'error': str(e)})
        
        return devices
    
    def get_motherboard_info(self) -> Dict:
        """Get motherboard information"""
        logger.info("Detecting motherboard...")
        
        try:
            if platform.system() == 'Windows':
                import wmi
                c = wmi.WMI()
                
                # Get baseboard info
                for board in c.Win32_BaseBoard():
                    info = {
                        'manufacturer': board.Manufacturer,
                        'product': board.Product,
                        'version': board.Version,
                        'serial': board.SerialNumber,
                    }
                    
                    # Get BIOS info
                    for bios in c.Win32_BIOS():
                        info.update({
                            'bios_manufacturer': bios.Manufacturer,
                            'bios_version': bios.SMBIOSBIOSVersion,
                            'bios_date': bios.ReleaseDate,
                        })
                    
                    logger.info(f"Motherboard detected: {info['manufacturer']} {info['product']}")
                    return info
            
        except Exception as e:
            logger.error(f"Error detecting motherboard: {e}")
        
        return {'manufacturer': 'Unknown', 'product': 'Unknown'}
    
    def get_system_info(self) -> Dict:
        """Get general system information"""
        logger.info("Detecting system info...")
        
        try:
            info = {
                'os': platform.system(),
                'os_version': platform.version(),
                'os_release': platform.release(),
                'architecture': platform.machine(),
                'hostname': platform.node(),
                'boot_time': psutil.boot_time(),
            }
            
            logger.info(f"System: {info['os']} {info['os_release']}")
            return info
            
        except Exception as e:
            logger.error(f"Error detecting system info: {e}")
            return {'os': 'Unknown', 'error': str(e)}
    
    def get_network_info(self) -> List[Dict]:
        """Get network adapter information"""
        logger.info("Detecting network adapters...")
        
        adapters = []
        
        try:
            if_addrs = psutil.net_if_addrs()
            if_stats = psutil.net_if_stats()
            
            for interface_name, addresses in if_addrs.items():
                adapter_info = {
                    'name': interface_name,
                    'addresses': [],
                    'is_up': if_stats[interface_name].isup if interface_name in if_stats else False,
                    'speed': if_stats[interface_name].speed if interface_name in if_stats else 0,
                }
                
                for addr in addresses:
                    adapter_info['addresses'].append({
                        'family': str(addr.family),
                        'address': addr.address,
                        'netmask': addr.netmask,
                    })
                
                adapters.append(adapter_info)
            
            logger.info(f"Network adapters detected: {len(adapters)}")
            
        except Exception as e:
            logger.error(f"Error detecting network adapters: {e}")
        
        return adapters
    
    def _get_memory_type(self, type_code: int) -> str:
        """Convert memory type code to readable string"""
        types = {
            20: 'DDR',
            21: 'DDR2',
            24: 'DDR3',
            26: 'DDR4',
            34: 'DDR5',
        }
        return types.get(type_code, f'Unknown ({type_code})')

# Convenience function
def detect_hardware() -> Dict:
    """
    Convenience function to detect all hardware
    
    Returns:
        Dict: Complete hardware information
    """
    detector = HardwareDetector()
    return detector.get_all_hardware()
