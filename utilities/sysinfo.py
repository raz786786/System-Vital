"""
System Info Utilities — Information gathering tools
"""

import subprocess
import os
import platform
import psutil
import time


def _list_installed_apps():
    """List installed applications with version"""
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | '
             'Select-Object DisplayName, DisplayVersion, Publisher | '
             'Where-Object {$_.DisplayName -ne $null} | '
             'Sort-Object DisplayName | '
             'Format-Table -AutoSize | Out-String -Width 200'],
            capture_output=True, text=True, timeout=30, creationflags=0x08000000
        )
        if result.stdout.strip():
            lines = result.stdout.strip().splitlines()
            count = len([l for l in lines if l.strip() and not l.startswith('-') and 'DisplayName' not in l])
            return {'success': True, 'message': f'{count} apps installed:\n{result.stdout.strip()[:2000]}'}
        return {'success': True, 'message': 'No installed apps found (unusual)'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _driver_report():
    """List all drivers with version and date"""
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-WmiObject Win32_PnPSignedDriver | '
             'Where-Object {$_.DeviceName -ne $null} | '
             'Select-Object DeviceName, DriverVersion, DriverDate | '
             'Sort-Object DeviceName | '
             'Format-Table -AutoSize | Out-String -Width 200'],
            capture_output=True, text=True, timeout=30, creationflags=0x08000000
        )
        if result.stdout.strip():
            lines = result.stdout.strip().splitlines()
            count = len([l for l in lines if l.strip() and not l.startswith('-') and 'DeviceName' not in l])
            return {'success': True, 'message': f'{count} drivers found:\n{result.stdout.strip()[:2000]}'}
        return {'success': True, 'message': 'No drivers found'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _windows_license():
    """Show Windows product key info"""
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             '(Get-WmiObject -query "select * from SoftwareLicensingService").OA3xOriginalProductKey'],
            capture_output=True, text=True, timeout=10, creationflags=0x08000000
        )
        key = result.stdout.strip()

        # Get activation status
        status_result = subprocess.run(
            ['powershell', '-Command',
             '(Get-CimInstance -ClassName SoftwareLicensingProduct -Filter "ApplicationID=\'55c92734-d682-4d71-983e-d6ec3f16059f\' AND PartialProductKey IS NOT NULL").LicenseStatus'],
            capture_output=True, text=True, timeout=10, creationflags=0x08000000
        )
        status_code = status_result.stdout.strip()
        status_map = {'0': 'Unlicensed', '1': 'Licensed ✅', '2': 'OOBGrace', '3': 'OOTGrace', '4': 'NonGenuine', '5': 'Notification'}
        status = status_map.get(status_code, f'Unknown ({status_code})')

        edition = platform.platform()

        msg = f"Windows Edition: {edition}\n"
        msg += f"Product Key: {key if key else 'Not available (OEM/Digital)'}\n"
        msg += f"Activation Status: {status}"

        return {'success': True, 'message': msg}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _hardware_summary():
    """Generate a full hardware summary"""
    try:
        cpu = platform.processor() or 'Unknown'
        mem = psutil.virtual_memory()
        disk_partitions = psutil.disk_partitions()

        msg = f"=== HARDWARE SUMMARY ===\n\n"
        msg += f"OS: {platform.system()} {platform.release()} ({platform.version()})\n"
        msg += f"Architecture: {platform.machine()}\n"
        msg += f"CPU: {cpu}\n"
        msg += f"Cores: {psutil.cpu_count(logical=False)} physical, {psutil.cpu_count()} logical\n"
        msg += f"RAM: {mem.total / (1024**3):.1f} GB total, {mem.available / (1024**3):.1f} GB available\n\n"

        msg += "Disks:\n"
        for part in disk_partitions:
            try:
                usage = psutil.disk_usage(part.mountpoint)
                msg += f"  {part.device} ({part.fstype}): {usage.total / (1024**3):.1f} GB total, {usage.percent}% used\n"
            except Exception:
                msg += f"  {part.device}: (not accessible)\n"

        return {'success': True, 'message': msg}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _uptime_boot_log():
    """Show system uptime and boot time"""
    try:
        boot_time = psutil.boot_time()
        boot_dt = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(boot_time))
        uptime_seconds = time.time() - boot_time
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)

        msg = f"Last Boot: {boot_dt}\n"
        msg += f"Uptime: {days}d {hours}h {minutes}m\n"

        if days > 7:
            msg += "\n⚠️ System has been running for over a week. Consider restarting."
        elif days > 3:
            msg += "\n💡 Consider restarting soon for optimal performance."
        else:
            msg += "\n✅ Uptime is healthy."

        return {'success': True, 'message': msg}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _bios_info():
    """Display BIOS/UEFI firmware info"""
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-WmiObject Win32_BIOS | Format-List Manufacturer, Name, Version, ReleaseDate, SMBIOSBIOSVersion, SerialNumber'],
            capture_output=True, text=True, timeout=10, creationflags=0x08000000
        )
        if result.stdout.strip():
            return {'success': True, 'message': f'BIOS Information:\n{result.stdout.strip()}'}
        return {'success': True, 'message': 'Could not retrieve BIOS information'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


SYSINFO_UTILITIES = [
    {'id': 'apps', 'name': 'Installed Apps List', 'desc': 'Full list with version & publisher', 'category': 'sysinfo', 'icon': '📦', 'color': '#3b82f6', 'run': _list_installed_apps},
    {'id': 'drivers', 'name': 'Driver Version Report', 'desc': 'All drivers with date & version', 'category': 'sysinfo', 'icon': '🔌', 'color': '#a855f7', 'run': _driver_report},
    {'id': 'license', 'name': 'Windows License Info', 'desc': 'Show product key & activation', 'category': 'sysinfo', 'icon': '🔑', 'color': '#22c55e', 'run': _windows_license},
    {'id': 'hw_export', 'name': 'Hardware Summary', 'desc': 'Full specs overview', 'category': 'sysinfo', 'icon': '💻', 'color': '#f97316', 'run': _hardware_summary},
    {'id': 'uptime_log', 'name': 'Uptime & Boot Log', 'desc': 'Boot time and uptime info', 'category': 'sysinfo', 'icon': '⏱️', 'color': '#06b6d4', 'run': _uptime_boot_log},
    {'id': 'bios', 'name': 'BIOS Version Info', 'desc': 'Display BIOS/UEFI firmware info', 'category': 'sysinfo', 'icon': '🖥️', 'color': '#eab308', 'run': _bios_info},
]
