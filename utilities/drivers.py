"""
Driver Utilities — Driver management tools
"""

import subprocess
import os


def _list_outdated_drivers():
    """List drivers with date older than 2 years"""
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-WmiObject Win32_PnPSignedDriver | '
             'Where-Object {$_.DriverDate -ne $null -and $_.DeviceName -ne $null} | '
             'Select-Object DeviceName, DriverVersion, @{N="Date";E={[DateTime]::ParseExact($_.DriverDate.Substring(0,8),"yyyyMMdd",$null).ToString("yyyy-MM-dd")}} | '
             'Sort-Object Date | '
             'Select-Object -First 15 | '
             'Format-Table -AutoSize | Out-String -Width 200'],
            capture_output=True, text=True, timeout=30, creationflags=0x08000000
        )
        if result.stdout.strip():
            return {'success': True, 'message': f'Oldest drivers (check for updates):\n{result.stdout.strip()[:1500]}'}
        return {'success': True, 'message': 'No driver date information available'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _export_driver_list():
    """Export full driver list to desktop"""
    try:
        desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        output_file = os.path.join(desktop, 'SYSTEM VITAL_drivers.txt')
        result = subprocess.run(
            ['driverquery', '/v', '/fo', 'csv'],
            capture_output=True, text=True, timeout=30, creationflags=0x08000000
        )
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
        return {'success': True, 'message': f'Driver list exported to:\n{output_file}'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _check_unsigned_drivers():
    """Find unsigned drivers that may cause issues"""
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-WmiObject Win32_PnPSignedDriver | '
             'Where-Object {$_.IsSigned -eq $false -and $_.DeviceName -ne $null} | '
             'Select-Object DeviceName, DriverVersion | '
             'Format-Table -AutoSize | Out-String -Width 200'],
            capture_output=True, text=True, timeout=20, creationflags=0x08000000
        )
        if result.stdout.strip():
            return {'success': True, 'message': f'Unsigned drivers found (potential risk):\n{result.stdout.strip()[:800]}'}
        return {'success': True, 'message': 'All drivers are signed. No unsigned drivers detected.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _check_driver_problems():
    """Find devices with driver problems (error codes)"""
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-WmiObject Win32_PnPEntity | '
             'Where-Object {$_.ConfigManagerErrorCode -ne 0} | '
             'Select-Object Name, ConfigManagerErrorCode, Status | '
             'Format-Table -AutoSize | Out-String -Width 200'],
            capture_output=True, text=True, timeout=20, creationflags=0x08000000
        )
        if result.stdout.strip():
            return {'success': True, 'message': f'Devices with driver problems:\n{result.stdout.strip()[:800]}'}
        return {'success': True, 'message': 'No device driver errors found. All devices are healthy.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _update_drivers_via_wu():
    """Trigger Windows Update driver check"""
    try:
        subprocess.Popen(
            ['powershell', '-Command', 'Start-Process ms-settings:windowsupdate-optionalupdates'],
            creationflags=0x08000000
        )
        return {'success': True, 'message': 'Opened Windows Update > Optional updates.\nCheck for driver updates there.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


DRIVER_UTILITIES = [
    {'id': 'drv_old', 'name': 'Outdated Driver Finder', 'desc': 'List drivers by age', 'category': 'drivers', 'icon': '📅', 'color': '#f97316', 'run': _list_outdated_drivers},
    {'id': 'drv_export', 'name': 'Driver List Export', 'desc': 'Export all drivers to file', 'category': 'drivers', 'icon': '📄', 'color': '#3b82f6', 'run': _export_driver_list},
    {'id': 'drv_unsigned', 'name': 'Unsigned Driver Check', 'desc': 'Find unsigned drivers', 'category': 'drivers', 'icon': '🔓', 'color': '#ef4444', 'run': _check_unsigned_drivers},
    {'id': 'drv_problems', 'name': 'Problem Device Scan', 'desc': 'Devices with error codes', 'category': 'drivers', 'icon': '⚠️', 'color': '#eab308', 'run': _check_driver_problems},
    {'id': 'drv_update', 'name': 'Driver Update Check', 'desc': 'Open Windows Update drivers', 'category': 'drivers', 'icon': '🔄', 'color': '#22c55e', 'run': _update_drivers_via_wu},
]
