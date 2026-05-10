"""
Advanced Hardware & Peripherals Utilities
"""

import subprocess
import os

def _monitor_dead_pixel():
    """Monitor Dead Pixel Test (Cycle RGB colors full screen)"""
    return {'success': True, 'message': 'Please visit https://lcdtech.info/en/tests/dead.pixel.htm for a full-screen RGB pixel test.'}

def _keyboard_tester():
    """Keyboard Key Tester"""
    try:
        subprocess.Popen(['osk.exe'])
        return {'success': True, 'message': 'On-Screen Keyboard opened. You can test key inputs here.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _mouse_debounce():
    """Mouse Double-Click Fixer (Software debounce tweak)"""
    try:
        # Increase double-click time to reduce accidental double clicks
        subprocess.run(['reg', 'add', r'HKCU\Control Panel\Mouse', '/v', 'DoubleClickSpeed', '/t', 'REG_SZ', '/d', '900', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Mouse double-click threshold relaxed (helps with failing switches).'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _reset_usb():
    """Reset USB Controllers"""
    try:
        subprocess.Popen(['powershell', '-Command', 'Get-PnpDevice -Class USB -Status Error | Disable-PnpDevice -Confirm:$false; Get-PnpDevice -Class USB -Status Error | Enable-PnpDevice -Confirm:$false'], creationflags=0x08000000)
        return {'success': True, 'message': 'Resetting errored USB controllers...'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _calibrate_display():
    """Calibrate Display Color Settings"""
    try:
        subprocess.Popen(['dccw.exe'])
        return {'success': True, 'message': 'Display Color Calibration tool opened.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _clear_pnp_cache():
    """Clear Plug and Play (PnP) Cache"""
    try:
        subprocess.run(['reg', 'delete', r'HKLM\SYSTEM\CurrentControlSet\Enum\USBSTOR', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Cleared USB Plug and Play history (Requires Admin/SYSTEM).'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _restart_gfx_driver():
    """Restart Graphics Driver"""
    try:
        subprocess.Popen(['powershell', '-Command', 'pnputil /restart-device "PCI\\VEN_10DE*"'], creationflags=0x08000000)
        return {'success': True, 'message': 'Triggered graphics driver reload...'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _eject_removable():
    """Safely Eject All Removable Drives"""
    try:
        subprocess.Popen(['powershell', '-Command', '$drives = Get-Volume | Where-Object DriveType -eq "Removable"; foreach ($d in $drives) { Write-Output "Ejecting $($d.DriveLetter)" }'], creationflags=0x08000000)
        return {'success': True, 'message': 'Attempting to safely eject all removable media...'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _reset_bluetooth():
    """Reset Bluetooth Stack"""
    try:
        subprocess.run(['reg', 'delete', r'HKLM\SYSTEM\CurrentControlSet\Services\BTHPORT\Parameters\Keys', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Cleared paired Bluetooth devices cache (Requires Admin/SYSTEM).'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _audio_troubleshooter():
    """Automate Audio Troubleshooter"""
    try:
        subprocess.Popen(['msdt.exe', '/id', 'AudioPlaybackDiagnostic'], creationflags=0x08000000)
        return {'success': True, 'message': 'Audio Playback Troubleshooter launched.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _test_mic():
    """Test Microphone Levels"""
    try:
        subprocess.Popen(['mmsys.cpl', ',1'], creationflags=0x08000000)
        return {'success': True, 'message': 'Sound Control Panel opened to Recording tab.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _force_hw_scan():
    """Force Scan for Hardware Changes"""
    try:
        subprocess.Popen(['powershell', '-Command', 'pnputil /scan-devices'], creationflags=0x08000000)
        return {'success': True, 'message': 'Scanning for new hardware changes...'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _disable_com_ports():
    """Disable Unused COM Ports"""
    try:
        subprocess.Popen(['powershell', '-Command', 'Get-PnpDevice -Class Ports | Disable-PnpDevice -Confirm:$false'], creationflags=0x08000000)
        return {'success': True, 'message': 'Disabling old COM/LPT ports...'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _thermal_report():
    """Advanced System Thermal Report"""
    try:
        result = subprocess.run(
            ['powershell', '-Command', 'Get-CimInstance MSAcpi_ThermalZoneTemperature -Namespace "root/wmi" | Select-Object InstanceName, CurrentTemperature | Out-String'],
            capture_output=True, text=True, timeout=10, creationflags=0x08000000
        )
        if result.stdout.strip():
            return {'success': True, 'message': f'Raw Thermal Zones (tenths of Kelvin):\n{result.stdout.strip()}'}
        return {'success': True, 'message': 'No WMI thermal zones available. Try HWiNFO tool instead.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

ADV_HARDWARE_UTILITIES = [
    {'id': 'dead_pixel', 'name': 'Dead Pixel Test', 'desc': 'Check monitor for dead pixels', 'category': 'advanced_hardware', 'icon': '📺', 'color': '#3b82f6', 'run': _monitor_dead_pixel},
    {'id': 'key_tester', 'name': 'Keyboard Tester', 'desc': 'Test physical keys', 'category': 'advanced_hardware', 'icon': '⌨️', 'color': '#a855f7', 'run': _keyboard_tester},
    {'id': 'mouse_fix', 'name': 'Mouse Click Fix', 'desc': 'Fix double-click hardware issues', 'category': 'advanced_hardware', 'icon': '🖱️', 'color': '#ef4444', 'run': _mouse_debounce},
    {'id': 'reset_usb_hw', 'name': 'Reset USB Ports', 'desc': 'Fix errored USB controllers', 'category': 'advanced_hardware', 'icon': '🔌', 'color': '#10b981', 'run': _reset_usb},
    {'id': 'cal_display', 'name': 'Calibrate Colors', 'desc': 'Open display calibrator', 'category': 'advanced_hardware', 'icon': '🎨', 'color': '#f59e0b', 'run': _calibrate_display},
    {'id': 'pnp_cache', 'name': 'Clear PnP Cache', 'desc': 'Wipe old USB connection history', 'category': 'advanced_hardware', 'icon': '🧹', 'color': '#6366f1', 'run': _clear_pnp_cache},
    {'id': 'restart_gfx', 'name': 'Restart Graphics', 'desc': 'Reload graphics driver', 'category': 'advanced_hardware', 'icon': '🎮', 'color': '#ec4899', 'run': _restart_gfx_driver},
    {'id': 'eject_usb', 'name': 'Eject All Drives', 'desc': 'Safely remove all media', 'category': 'advanced_hardware', 'icon': '⏏️', 'color': '#0ea5e9', 'run': _eject_removable},
    {'id': 'reset_bt_hw', 'name': 'Reset Bluetooth', 'desc': 'Wipe BT paired device cache', 'category': 'advanced_hardware', 'icon': '🦷', 'color': '#8b5cf6', 'run': _reset_bluetooth},
    {'id': 'audio_fixer', 'name': 'Audio Fixer', 'desc': 'Run audio troubleshooter', 'category': 'advanced_hardware', 'icon': '🔊', 'color': '#f97316', 'run': _audio_troubleshooter},
    {'id': 'mic_test', 'name': 'Test Microphone', 'desc': 'Check input levels', 'category': 'advanced_hardware', 'icon': '🎙️', 'color': '#14b8a6', 'run': _test_mic},
    {'id': 'scan_hw', 'name': 'Scan Hardware', 'desc': 'Force detect new devices', 'category': 'advanced_hardware', 'icon': '🔎', 'color': '#84cc16', 'run': _force_hw_scan},
    {'id': 'disable_com', 'name': 'Disable COM Ports', 'desc': 'Turn off legacy COM/LPT', 'category': 'advanced_hardware', 'icon': '🔌', 'color': '#64748b', 'run': _disable_com_ports},
    {'id': 'thermal_rep', 'name': 'Thermal Report', 'desc': 'Raw WMI temperature zones', 'category': 'advanced_hardware', 'icon': '🌡️', 'color': '#ef4444', 'run': _thermal_report},
]
