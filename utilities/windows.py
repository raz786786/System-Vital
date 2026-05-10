"""
Windows-specific fix utilities
"""

import subprocess
import os


def _reset_icon_cache():
    """Reset Windows icon cache to fix broken icons"""
    try:
        cache_dir = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Explorer')
        if os.path.exists(cache_dir):
            # Kill explorer
            subprocess.run(['taskkill', '/f', '/im', 'explorer.exe'],
                           capture_output=True, creationflags=0x08000000)
            # Delete icon cache files
            import glob
            for f in glob.glob(os.path.join(cache_dir, 'iconcache*')):
                try:
                    os.remove(f)
                except Exception:
                    pass
            # Restart explorer
            subprocess.Popen(['explorer.exe'])
            return {'success': True, 'message': 'Icon cache cleared and explorer restarted. Icons should refresh.'}
        return {'success': True, 'message': 'Icon cache directory not found'}
    except Exception as e:
        subprocess.Popen(['explorer.exe'])
        return {'success': False, 'message': str(e)}


def _rebuild_search_index():
    """Reset Windows Search index"""
    try:
        subprocess.Popen(
            ['powershell', '-Command',
             'Start-Process cmd -ArgumentList \'/k net stop WSearch & del /f /q "%ProgramData%\\Microsoft\\Search\\Data\\Applications\\Windows\\Windows.edb" & net start WSearch & echo Search index rebuilt!\' -Verb RunAs'],
            creationflags=0x08000000
        )
        return {'success': True, 'message': 'Windows Search index rebuild started in Admin window.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _fix_store():
    """Reset Windows Store and fix app installs"""
    try:
        subprocess.Popen(
            ['powershell', '-Command',
             'Start-Process cmd -ArgumentList \'/k wsreset.exe\' -Verb RunAs'],
            creationflags=0x08000000
        )
        return {'success': True, 'message': 'Windows Store cache cleared (wsreset). Store should restart.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _fix_taskbar():
    """Re-register taskbar and Start menu shell"""
    try:
        subprocess.Popen(
            ['powershell', '-Command',
             'Start-Process powershell -ArgumentList \'-Command Get-AppXPackage -AllUsers | Foreach {Add-AppxPackage -DisableDevelopmentMode -Register "$($_.InstallLocation)\\AppXManifest.xml"}\' -Verb RunAs'],
            creationflags=0x08000000
        )
        return {'success': True, 'message': 'Taskbar/Start re-registration started. Wait for it to complete, then restart.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _fix_time_sync():
    """Force NTP time synchronization"""
    try:
        subprocess.Popen(
            ['powershell', '-Command',
             'Start-Process cmd -ArgumentList \'/k net stop w32time & net start w32time & w32tm /resync /force & echo Time synced!\' -Verb RunAs'],
            creationflags=0x08000000
        )
        return {'success': True, 'message': 'Time sync initiated. Clock should be corrected shortly.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _clear_notification_cache():
    """Clear Windows notification center cache"""
    try:
        cache_path = os.path.join(os.environ.get('LOCALAPPDATA', ''),
                                   'Microsoft', 'Windows', 'Notifications')
        if os.path.exists(cache_path):
            import shutil
            for item in os.listdir(cache_path):
                try:
                    fp = os.path.join(cache_path, item)
                    if os.path.isfile(fp):
                        os.remove(fp)
                except Exception:
                    pass
            return {'success': True, 'message': 'Notification cache cleared. Restart may be needed.'}
        return {'success': True, 'message': 'Notification cache not found'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _reset_network_discovery():
    """Enable network discovery and file sharing"""
    try:
        subprocess.Popen(
            ['powershell', '-Command',
             'Start-Process cmd -ArgumentList \'/k netsh advfirewall firewall set rule group="Network Discovery" new enable=Yes & netsh advfirewall firewall set rule group="File and Printer Sharing" new enable=Yes & echo Network Discovery enabled!\' -Verb RunAs'],
            creationflags=0x08000000
        )
        return {'success': True, 'message': 'Network Discovery and File Sharing enabled.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


WINDOWS_UTILITIES = [
    {'id': 'icon_cache', 'name': 'Icon Cache Reset', 'desc': 'Fix broken/blank icons', 'category': 'windows', 'icon': '🖼️', 'color': '#06b6d4', 'run': _reset_icon_cache},
    {'id': 'search_idx', 'name': 'Search Index Rebuild', 'desc': 'Reset Windows Search index', 'category': 'windows', 'icon': '🔍', 'color': '#3b82f6', 'run': _rebuild_search_index},
    {'id': 'store_fix', 'name': 'Store Cache Reset', 'desc': 'wsreset to fix Store issues', 'category': 'windows', 'icon': '🏪', 'color': '#22c55e', 'run': _fix_store},
    {'id': 'taskbar_fix', 'name': 'Taskbar/Start Fix', 'desc': 'Re-register shell components', 'category': 'windows', 'icon': '📌', 'color': '#a855f7', 'run': _fix_taskbar},
    {'id': 'time_sync', 'name': 'Time Sync Fix', 'desc': 'Force NTP clock sync', 'category': 'windows', 'icon': '🕐', 'color': '#eab308', 'run': _fix_time_sync},
    {'id': 'notif_cache', 'name': 'Notification Clearer', 'desc': 'Clear notification cache', 'category': 'windows', 'icon': '🔔', 'color': '#f97316', 'run': _clear_notification_cache},
    {'id': 'net_discover', 'name': 'Network Discovery', 'desc': 'Enable discovery + sharing', 'category': 'windows', 'icon': '🔎', 'color': '#06b6d4', 'run': _reset_network_discovery},
]
