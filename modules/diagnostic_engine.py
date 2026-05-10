"""
Diagnostic Engine Module
Detects hardware issues and provides fixes
"""

import psutil
import platform
import time
import subprocess
from typing import Dict, List
from utils.logger import setup_logger
import config

logger = setup_logger(__name__)

class DiagnosticEngine:
    """Comprehensive hardware diagnostics and issue detection"""
    
    def __init__(self):
        self.issues = []
        self.fixes = []
        logger.info("Diagnostic Engine initialized")
    
    def run_all_diagnostics(self, hardware_info: Dict = None) -> Dict:
        """
        Run all diagnostic checks
        
        Args:
            hardware_info: Hardware information from HardwareDetector
        
        Returns:
            Dict: Issues and fixes
        """
        logger.info("Running comprehensive diagnostics...")
        
        self.issues = []
        self.fixes = []
        
        # Run all checks
        self.check_thermal_issues(hardware_info)
        self.check_driver_issues(hardware_info)
        self.check_storage_health(hardware_info)
        self.check_memory_issues(hardware_info)
        self.check_bottlenecks(hardware_info)
        self.check_system_stability()
        self.check_power_settings()
        self.check_startup_apps()
        self.check_system_uptime()
        self.check_pagefile_settings()
        
        logger.info(f"Diagnostics completed: {len(self.issues)} issues found")
        
        return {
            'issues': self.issues,
            'fixes': self.fixes,
            'summary': self._generate_summary()
        }
    
    def check_thermal_issues(self, hardware_info: Dict = None):
        """Check for thermal issues"""
        logger.info("Checking thermal issues...")
        
        try:
            # Check CPU temperature
            if hardware_info and 'cpu' in hardware_info:
                cpu_temp = hardware_info['cpu'].get('temperature')
                
                if cpu_temp:
                    if cpu_temp > config.CPU_TEMP_CRITICAL:
                        self.issues.append({
                            'severity': 'CRITICAL',
                            'component': 'CPU',
                            'issue': f'CPU overheating: {cpu_temp}°C',
                            'description': 'CPU temperature is dangerously high and may cause damage',
                            'fixes': [
                                '⚠️ URGENT: Shut down and check cooling immediately',
                                'Clean CPU cooler and reapply thermal paste',
                                'Verify CPU cooler is properly mounted',
                                'Check if CPU cooler is adequate for your CPU TDP',
                                'Improve case airflow (add/replace fans)',
                                'Reduce CPU overclock if applicable',
                            ],
                            'automated_fix': None,
                            'priority': 1
                        })
                    elif cpu_temp > config.CPU_TEMP_WARNING:
                        self.issues.append({
                            'severity': 'WARNING',
                            'component': 'CPU',
                            'issue': f'CPU running hot: {cpu_temp}°C',
                            'description': 'CPU temperature is higher than ideal',
                            'fixes': [
                                'Clean dust from CPU cooler and case fans',
                                'Verify case has adequate airflow',
                                'Consider upgrading CPU cooler',
                                'Check ambient room temperature',
                                'Ensure CPU cooler fan is spinning properly',
                            ],
                            'automated_fix': None,
                            'priority': 2
                        })
            
            # Check GPU temperature
            if hardware_info and 'gpu' in hardware_info:
                for gpu in hardware_info['gpu']:
                    gpu_temp = gpu.get('temperature')
                    
                    if gpu_temp:
                        if gpu_temp > config.GPU_TEMP_CRITICAL:
                            self.issues.append({
                                'severity': 'CRITICAL',
                                'component': 'GPU',
                                'issue': f'GPU overheating: {gpu_temp}°C',
                                'description': f'{gpu.get("name")} is running dangerously hot',
                                'fixes': [
                                    '⚠️ Stop intensive GPU tasks immediately',
                                    'Clean GPU fans and heatsink',
                                    'Replace thermal paste on GPU (advanced)',
                                    'Improve case airflow',
                                    'Increase GPU fan speed using MSI Afterburner',
                                    'Reduce GPU overclock if applicable',
                                ],
                                'automated_fix': None,
                                'priority': 1
                            })
                        elif gpu_temp > config.GPU_TEMP_WARNING:
                            self.issues.append({
                                'severity': 'WARNING',
                                'component': 'GPU',
                                'issue': f'GPU running hot: {gpu_temp}°C',
                                'description': f'{gpu.get("name")} temperature is elevated',
                                'fixes': [
                                    'Clean GPU fans and case',
                                    'Increase GPU fan curve using MSI Afterburner or similar',
                                    'Improve case airflow',
                                    'Check if GPU has adequate space for airflow',
                                ],
                                'automated_fix': None,
                                'priority': 2
                            })
        
        except Exception as e:
            logger.error(f"Error checking thermal issues: {e}")
    
    def check_driver_issues(self, hardware_info: Dict = None):
        """Check for driver issues"""
        logger.info("Checking driver issues...")
        
        try:
            if platform.system() == 'Windows' and hardware_info and 'gpu' in hardware_info:
                import wmi
                c = wmi.WMI()
                
                for gpu in hardware_info['gpu']:
                    gpu_name = gpu.get('name', '')
                    driver_version = gpu.get('driver_version', '')
                    
                    # Simplified check - in production, compare with known latest versions
                    if driver_version:
                        self.issues.append({
                            'severity': 'INFO',
                            'component': 'GPU',
                            'issue': f'GPU driver detected: {driver_version}',
                            'description': 'Consider checking for driver updates',
                            'fixes': [
                                'Check for latest drivers:',
                                '  • NVIDIA: GeForce Experience or nvidia.com/drivers',
                                '  • AMD: AMD Software or amd.com/support',
                                '  • Intel: Intel Driver & Support Assistant',
                                'Use DDU (Display Driver Uninstaller) for clean installation',
                                'Always download drivers from official manufacturer websites',
                            ],
                            'automated_fix': None,
                            'priority': 3
                        })
        
        except Exception as e:
            logger.error(f"Error checking driver issues: {e}")
    
    def check_storage_health(self, hardware_info: Dict = None):
        """Check storage health"""
        logger.info("Checking storage health...")
        
        try:
            if hardware_info and 'storage' in hardware_info:
                for device in hardware_info['storage']:
                    # Check disk usage
                    if device.get('percent_used', 0) > 90:
                        self.issues.append({
                            'severity': 'WARNING',
                            'component': 'Storage',
                            'issue': f'Drive {device.get("device")} is {device.get("percent_used")}% full',
                            'description': 'Low disk space can affect performance',
                            'fixes': [
                                'Delete unnecessary files',
                                'Use Disk Cleanup (cleanmgr.exe)',
                                'Uninstall unused programs',
                                'Move large files to external storage',
                                'Empty Recycle Bin',
                                'Clear browser cache and downloads',
                            ],
                            'automated_fix': 'cleanup_temp_files',
                            'priority': 2
                        })
                    
                    # Check SMART health
                    smart_health = device.get('smart_health')
                    if smart_health and smart_health != 'PASS':
                        self.issues.append({
                            'severity': 'CRITICAL',
                            'component': 'Storage',
                            'issue': f'Drive {device.get("device")} failing SMART test',
                            'description': '⚠️ Drive may fail soon - BACKUP IMMEDIATELY!',
                            'fixes': [
                                '🚨 BACKUP ALL IMPORTANT DATA IMMEDIATELY',
                                'Replace drive as soon as possible',
                                'Check SMART attributes for specific errors',
                                'Consider professional data recovery if needed',
                                'Do not use this drive for important data',
                            ],
                            'automated_fix': None,
                            'priority': 1
                        })
        
        except Exception as e:
            logger.error(f"Error checking storage health: {e}")
    
    def check_memory_issues(self, hardware_info: Dict = None):
        """Check memory issues"""
        logger.info("Checking memory issues...")
        
        try:
            mem = psutil.virtual_memory()
            
            # Check high memory usage
            if mem.percent > 90:
                self.issues.append({
                    'severity': 'WARNING',
                    'component': 'RAM',
                    'issue': f'High memory usage: {mem.percent}%',
                    'description': f'Using {mem.percent}% of available RAM',
                    'fixes': [
                        'Close unnecessary applications',
                        'Check Task Manager for memory-hungry processes',
                        'Restart your computer to clear memory leaks',
                        f'Consider upgrading RAM (current: {mem.total // (1024**3)}GB)',
                        'Disable startup programs you don\'t need',
                    ],
                    'automated_fix': None,
                    'priority': 2
                })
            
            # Check RAM speed mismatch
            if hardware_info and 'ram' in hardware_info:
                modules = hardware_info['ram'].get('modules', [])
                if modules:
                    speeds = [m.get('speed', 0) for m in modules if m.get('speed')]
                    
                    if len(set(speeds)) > 1:
                        self.issues.append({
                            'severity': 'WARNING',
                            'component': 'RAM',
                            'issue': 'RAM modules running at different speeds',
                            'description': f'Detected speeds: {speeds} MHz - all will run at slowest speed',
                            'fixes': [
                                'All RAM will run at the slowest module speed',
                                'For best performance, use matched RAM kits',
                                'Check if XMP/DOCP profile is enabled in BIOS',
                                'Consider replacing with matched speed modules',
                            ],
                            'automated_fix': None,
                            'priority': 3
                        })
        
        except Exception as e:
            logger.error(f"Error checking memory issues: {e}")
    
    def check_bottlenecks(self, hardware_info: Dict = None):
        """Check for system bottlenecks"""
        logger.info("Checking for bottlenecks...")
        
        try:
            # This is a simplified bottleneck check
            # In production, this would use actual benchmark scores
            
            if hardware_info:
                # Placeholder logic - would use actual scoring system
                self.issues.append({
                    'severity': 'INFO',
                    'component': 'System Balance',
                    'issue': 'System balance analysis',
                    'description': 'Check if components are well-balanced',
                    'fixes': [
                        'Run benchmarks to identify bottlenecks',
                        'For gaming: GPU should be the strongest component',
                        'For productivity: CPU and RAM are most important',
                        'Balanced systems perform better overall',
                    ],
                    'automated_fix': None,
                    'priority': 4
                })
        
        except Exception as e:
            logger.error(f"Error checking bottlenecks: {e}")
    
    def check_system_stability(self):
        """Check for system stability issues"""
        logger.info("Checking system stability...")
        
        try:
            self.issues.append({
                'severity': 'INFO',
                'component': 'System Maintenance',
                'issue': 'Recommended system maintenance',
                'description': 'Regular maintenance improves stability and performance',
                'fixes': [
                    'Run System File Checker: sfc /scannow (as Administrator)',
                    'Run DISM: DISM /Online /Cleanup-Image /RestoreHealth',
                    'Check disk for errors: chkdsk /f (requires restart)',
                    'Clean temporary files: Disk Cleanup',
                    'Update Windows: Check for Windows Updates',
                    'Defragment HDD (NOT SSD): defrag /O',
                ],
                'automated_fix': 'run_maintenance',
                'priority': 4
            })
        
        except Exception as e:
            logger.error(f"Error checking system stability: {e}")
    
    def check_power_settings(self):
        """Check power settings"""
        logger.info("Checking power settings...")
        
        try:
            if platform.system() == 'Windows':
                import subprocess
                
                # Check current power plan
                result = subprocess.run(
                    ['powercfg', '/getactivescheme'],
                    capture_output=True,
                    text=True
                )
                
                if 'High performance' not in result.stdout and 'Ultimate Performance' not in result.stdout:
                    self.issues.append({
                        'severity': 'INFO',
                        'component': 'Power Settings',
                        'issue': 'Not using high performance power plan',
                        'description': 'Power saving mode may reduce performance',
                        'fixes': [
                            'Switch to "High Performance" power plan for better performance',
                            'Go to: Control Panel > Power Options',
                            'Or run: powercfg /setactive SCHEME_MIN',
                            'Note: This will increase power consumption',
                        ],
                        'automated_fix': 'set_high_performance',
                        'priority': 3
                    })
        
        except Exception as e:
            logger.error(f"Error checking power settings: {e}")

    def check_startup_apps(self):
        """Check for excessive startup applications"""
        logger.info("Checking startup apps...")
        try:
            import winreg
            startup_apps = []
            
            # Check Registry (Current User)
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
                    for i in range(1024):
                        startup_apps.append(winreg.EnumValue(key, i)[0])
            except OSError: pass
            
            # Check Registry (Local Machine)
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
                    for i in range(1024):
                        startup_apps.append(winreg.EnumValue(key, i)[0])
            except OSError: pass
            
            if len(startup_apps) > 10:
                self.issues.append({
                    'severity': 'WARNING',
                    'component': 'System Performance',
                    'issue': f'Too many startup apps ({len(startup_apps)})',
                    'description': 'Excessive startup applications can significantly slow down your boot time and consume background resources.',
                    'fixes': [
                        'Disable unnecessary startup items in Task Manager (Ctrl+Shift+Esc > Startup)',
                        'Check "Startup" folder in Start Menu',
                        'Use a clean boot to troubleshoot performance issues'
                    ],
                    'automated_fix': None,
                    'priority': 3
                })
        except Exception as e:
            logger.error(f"Error checking startup apps: {e}")

    def check_system_uptime(self):
        """Check system uptime and suggest reboot if too high"""
        logger.info("Checking system uptime...")
        try:
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            uptime_days = uptime_seconds / (24 * 3600)
            
            if uptime_days > 7:
                self.issues.append({
                    'severity': 'WARNING',
                    'component': 'System Health',
                    'issue': f'Long system uptime: {int(uptime_days)} days',
                    'description': 'Computers should be restarted regularly to install updates, clear memory leaks, and prevent performance degradation.',
                    'fixes': [
                        'Restart your computer as soon as possible',
                        'Check for pending Windows Updates',
                        'Verify if "Fast Startup" is making system uptime persist across shutdowns'
                    ],
                    'automated_fix': None,
                    'priority': 2
                })
        except Exception as e:
            logger.error(f"Error checking uptime: {e}")

    def check_pagefile_settings(self):
        """Check for virtual memory / pagefile stability"""
        logger.info("Checking pagefile...")
        try:
            swap = psutil.swap_memory()
            if swap.total == 0:
                self.issues.append({
                    'severity': 'CRITICAL',
                    'component': 'Memory',
                    'issue': 'No Pagefile detected',
                    'description': 'A pagefile is required for system stability and preventing Crashes/Blue Screens when RAM is full.',
                    'fixes': [
                        'Enable "Automatically manage paging file size for all drives" in System Properties',
                        'Ensure you have at least 4-8GB of virtual memory allocated'
                    ],
                    'automated_fix': None,
                    'priority': 1
                })
        except Exception as e:
            logger.error(f"Error checking pagefile: {e}")
    
    def _generate_summary(self) -> Dict:
        """Generate diagnostic summary"""
        critical = sum(1 for i in self.issues if i['severity'] == 'CRITICAL')
        warnings = sum(1 for i in self.issues if i['severity'] == 'WARNING')
        info = sum(1 for i in self.issues if i['severity'] == 'INFO')
        
        return {
            'total_issues': len(self.issues),
            'critical': critical,
            'warnings': warnings,
            'info': info,
            'health_score': max(0, 100 - (critical * 30 + warnings * 10 + info * 2))
        }
    
    def apply_automated_fix(self, fix_id: str) -> Dict:
        """
        Apply automated fix
        
        Args:
            fix_id: Fix identifier
        
        Returns:
            Dict: Result of fix application
        """
        logger.info(f"Applying automated fix: {fix_id}")
        
        try:
            if fix_id == 'cleanup_temp_files':
                return self._cleanup_temp_files()
            elif fix_id == 'set_high_performance':
                return self._set_high_performance()
            elif fix_id == 'run_maintenance':
                return self._run_maintenance()
            elif fix_id == 'restart_explorer':
                return self._restart_explorer()
            elif fix_id == 'flush_dns':
                return self._flush_dns()
            elif fix_id == 'optimize_drives':
                return self._optimize_drives()
            elif fix_id == 'deep_clean_temp':
                return self._deep_clean_temp()
            else:
                return {'success': False, 'message': 'Unknown fix ID'}
        
        except Exception as e:
            logger.error(f"Error applying fix: {e}")
            return {'success': False, 'message': str(e)}
    
    def _cleanup_temp_files(self) -> Dict:
        """Clean temporary files"""
        import subprocess
        
        try:
            # Run Disk Cleanup
            subprocess.Popen(['cleanmgr', '/sagerun:1'])
            return {'success': True, 'message': 'Disk Cleanup started'}
        except:
            return {'success': False, 'message': 'Failed to start Disk Cleanup'}
    
    def _set_high_performance(self) -> Dict:
        """Set high performance power plan"""
        import subprocess
        
        try:
            subprocess.run(['powercfg', '/setactive', 'SCHEME_MIN'], check=True)
            return {'success': True, 'message': 'Power plan set to High Performance'}
        except:
            return {'success': False, 'message': 'Failed to change power plan'}
    
    def _run_maintenance(self) -> Dict:
        """Run system maintenance"""
        return {
            'success': True,
            'message': 'Please run maintenance commands manually with Administrator privileges'
        }

    def _restart_explorer(self) -> Dict:
        """Restart Windows Explorer"""
        import subprocess
        try:
            subprocess.run(['taskkill', '/f', '/im', 'explorer.exe'], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            subprocess.Popen(['explorer.exe'])
            return {'success': True, 'message': 'Explorer restarted successfully'}
        except Exception as e:
            logger.error(f"Failed to restart explorer: {e}")
            # Try to start explorer anyway if it's dead
            subprocess.Popen(['explorer.exe'])
            return {'success': False, 'message': f"Failed: {e}"}

    def _flush_dns(self) -> Dict:
        """Flush DNS Cache"""
        import subprocess
        try:
            subprocess.run(['ipconfig', '/flushdns'], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return {'success': True, 'message': 'DNS Cache flushed'}
        except Exception as e:
            return {'success': False, 'message': f"Failed: {e}"}

    def _optimize_drives(self) -> Dict:
        """Run TRIM on all SSDs"""
        import subprocess
        try:
            # Requires admin
            subprocess.Popen(['powershell', '-Command', 'Optimize-Volume -DriveLetter C -ReTrim -Verbose'], creationflags=subprocess.CREATE_NEW_CONSOLE)
            return {'success': True, 'message': 'Optimization started in new window'}
        except Exception as e:
            return {'success': False, 'message': f"Failed: {e}"}

    def _deep_clean_temp(self) -> Dict:
        """Comprehensive temp file cleaning"""
        import os
        import shutil
        import getpass
        
        cleaned_count = 0
        try:
            temp_paths = [
                os.environ.get('TEMP'),
                os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Temp')
            ]
            
            for path in temp_paths:
                if not path or not os.path.exists(path): continue
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    try:
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                            cleaned_count += 1
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path, ignore_errors=True)
                            cleaned_count += 1
                    except: pass
            
            return {'success': True, 'message': f'Cleaned {cleaned_count} temporary items'}
        except Exception as e:
            return {'success': False, 'message': f"Error: {e}"}

# Convenience function
def run_diagnostics(hardware_info: Dict = None) -> Dict:
    """
    Convenience function to run diagnostics
    
    Returns:
        Dict: Diagnostic results
    """
    engine = DiagnosticEngine()
    return engine.run_all_diagnostics(hardware_info)
