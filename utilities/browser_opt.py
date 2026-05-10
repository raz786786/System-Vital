"""
Web & Browser Optimization Utilities
"""

import subprocess
import os

def _clear_chrome_cache():
    """Clear Google Chrome Full Cache"""
    try:
        path = os.path.join(os.environ.get('LOCALAPPDATA', 'C:\\'), r'Google\Chrome\User Data\Default\Cache')
        subprocess.Popen(['powershell', '-Command', f'Remove-Item -Path "{path}\\*" -Recurse -Force -ErrorAction SilentlyContinue'], creationflags=0x08000000)
        return {'success': True, 'message': 'Chrome cache cleared.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _clear_edge_cache():
    """Clear Microsoft Edge Full Cache"""
    try:
        path = os.path.join(os.environ.get('LOCALAPPDATA', 'C:\\'), r'Microsoft\Edge\User Data\Default\Cache')
        subprocess.Popen(['powershell', '-Command', f'Remove-Item -Path "{path}\\*" -Recurse -Force -ErrorAction SilentlyContinue'], creationflags=0x08000000)
        return {'success': True, 'message': 'Edge cache cleared.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _clear_firefox_cache():
    """Clear Mozilla Firefox Full Cache"""
    try:
        path = os.path.join(os.environ.get('LOCALAPPDATA', 'C:\\'), r'Mozilla\Firefox\Profiles')
        subprocess.Popen(['powershell', '-Command', f'Get-ChildItem -Path "{path}" -Directory | ForEach-Object {{ Remove-Item -Path "$($_.FullName)\\cache2\\*" -Recurse -Force -ErrorAction SilentlyContinue }}'], creationflags=0x08000000)
        return {'success': True, 'message': 'Firefox cache cleared.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _disable_edge_bg():
    """Disable Edge Background Extensions"""
    try:
        subprocess.run(['reg', 'add', r'HKCU\Software\Policies\Microsoft\Edge', '/v', 'BackgroundModeEnabled', '/t', 'REG_DWORD', '/d', '0', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Edge background mode disabled.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _deep_reset_tcp():
    """Deep Reset TCP/IP Stack"""
    try:
        subprocess.Popen(['cmd', '/c', 'netsh int ip reset & netsh winsock reset'], creationflags=0x08000000)
        return {'success': True, 'message': 'TCP/IP and Winsock stack reset (Restart required).'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _reset_proxy():
    """Reset Network Proxy Settings"""
    try:
        subprocess.run(['reg', 'add', r'HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings', '/v', 'ProxyEnable', '/t', 'REG_DWORD', '/d', '0', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Network proxy settings reset/disabled.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _block_tracking_cookies():
    """Block Third-Party Tracking Cookies (IE/Edge Legacy)"""
    try:
        subprocess.run(['reg', 'add', r'HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings\Zones\3', '/v', '1A10', '/t', 'REG_DWORD', '/d', '3', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Third-party cookies blocked in Windows Internet settings.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _optimize_network_mtu():
    """Optimize Browser Network Settings (MTU auto-tuning)"""
    try:
        subprocess.Popen(['cmd', '/c', 'netsh int tcp set global autotuninglevel=normal'], creationflags=0x08000000)
        return {'success': True, 'message': 'TCP auto-tuning set to normal for optimal browser speed.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _remove_adware_ext():
    """Remove Unknown/Adware Extensions (Chrome policies)"""
    try:
        subprocess.run(['reg', 'delete', r'HKLM\Software\Policies\Google\Chrome\ExtensionInstallForcelist', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Cleared forced Chrome extension policies.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _deep_clean_hosts():
    """Deep Clean Hosts File"""
    try:
        hosts_path = r'C:\Windows\System32\drivers\etc\hosts'
        default_content = "# Default Windows Hosts file\\n127.0.0.1 localhost\\n::1 localhost"
        subprocess.Popen(['powershell', '-Command', f'Set-Content -Path "{hosts_path}" -Value "{default_content}" -Force'], creationflags=0x08000000)
        return {'success': True, 'message': 'Hosts file reset to absolute default.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

BROWSER_OPT_UTILITIES = [
    {'id': 'chrome_cache', 'name': 'Clear Chrome Cache', 'desc': 'Wipe Google Chrome cache', 'category': 'browser_opt', 'icon': '🌐', 'color': '#ef4444', 'run': _clear_chrome_cache},
    {'id': 'edge_cache', 'name': 'Clear Edge Cache', 'desc': 'Wipe Microsoft Edge cache', 'category': 'browser_opt', 'icon': '🌊', 'color': '#3b82f6', 'run': _clear_edge_cache},
    {'id': 'firefox_cache', 'name': 'Clear Firefox Cache', 'desc': 'Wipe Mozilla Firefox cache', 'category': 'browser_opt', 'icon': '🦊', 'color': '#f97316', 'run': _clear_firefox_cache},
    {'id': 'edge_bg_off', 'name': 'Edge Background Off', 'desc': 'Stop Edge from running in bg', 'category': 'browser_opt', 'icon': '🛑', 'color': '#8b5cf6', 'run': _disable_edge_bg},
    {'id': 'deep_tcp', 'name': 'Deep TCP/IP Reset', 'desc': 'Full reset of network stack', 'category': 'browser_opt', 'icon': '🔌', 'color': '#10b981', 'run': _deep_reset_tcp},
    {'id': 'reset_proxy_full', 'name': 'Reset Proxy', 'desc': 'Clear all proxy settings', 'category': 'browser_opt', 'icon': '🛡️', 'color': '#f59e0b', 'run': _reset_proxy},
    {'id': 'block_cookies', 'name': 'Block Tracking', 'desc': 'Block 3rd party cookies (IE)', 'category': 'browser_opt', 'icon': '🍪', 'color': '#ec4899', 'run': _block_tracking_cookies},
    {'id': 'opt_mtu', 'name': 'Optimize TCP Tuning', 'desc': 'Fix slow browsing speeds', 'category': 'browser_opt', 'icon': '🚀', 'color': '#0ea5e9', 'run': _optimize_network_mtu},
    {'id': 'clear_policies', 'name': 'Clear Ext Policies', 'desc': 'Remove forced extensions', 'category': 'browser_opt', 'icon': '🧹', 'color': '#6366f1', 'run': _remove_adware_ext},
    {'id': 'clean_hosts', 'name': 'Deep Clean Hosts', 'desc': 'Wipe all hosts file entries', 'category': 'browser_opt', 'icon': '📝', 'color': '#14b8a6', 'run': _deep_clean_hosts},
]
