"""
Deep Privacy & Security Utilities
"""

import subprocess
import os

def _disable_location():
    """Disable Windows Location Tracking"""
    try:
        subprocess.run(['reg', 'add', r'HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location', '/v', 'Value', '/t', 'REG_SZ', '/d', 'Deny', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Global location tracking disabled.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _disable_ad_id():
    """Disable Advertising ID Tracking"""
    try:
        subprocess.run(['reg', 'add', r'HKCU\Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo', '/v', 'Enabled', '/t', 'REG_DWORD', '/d', '0', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Advertising ID disabled.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _disable_feedback():
    """Disable App Feedback Requests"""
    try:
        subprocess.run(['reg', 'add', r'HKCU\Software\Microsoft\Siuf\Rules', '/v', 'NumberOfSIUFInPeriod', '/t', 'REG_DWORD', '/d', '0', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Windows feedback requests disabled.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _disable_timeline():
    """Turn Off Activity Timeline History"""
    try:
        subprocess.run(['reg', 'add', r'HKLM\SOFTWARE\Policies\Microsoft\Windows\System', '/v', 'EnableActivityFeed', '/t', 'REG_DWORD', '/d', '0', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Activity Timeline and history tracking disabled.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _restrict_bg_apps():
    """Restrict Background Apps Globally"""
    try:
        subprocess.run(['reg', 'add', r'HKCU\Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications', '/v', 'GlobalUserDisabled', '/t', 'REG_DWORD', '/d', '1', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'UWP background apps globally restricted.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _disable_camera():
    """Turn Off Camera Access Globally"""
    try:
        subprocess.run(['reg', 'add', r'HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\webcam', '/v', 'Value', '/t', 'REG_SZ', '/d', 'Deny', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Global webcam access disabled for all apps.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _disable_mic():
    """Turn Off Microphone Access Globally"""
    try:
        subprocess.run(['reg', 'add', r'HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone', '/v', 'Value', '/t', 'REG_SZ', '/d', 'Deny', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Global microphone access disabled for all apps.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _clear_defender_history():
    """Clear Windows Defender Scan History"""
    try:
        subprocess.Popen(['powershell', '-Command', 'Remove-Item -Path "C:\\ProgramData\\Microsoft\\Windows Defender\\Scans\\History\\Service\\*" -Recurse -Force -ErrorAction SilentlyContinue'], creationflags=0x08000000)
        return {'success': True, 'message': 'Windows Defender Protection History cleared.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _enable_ransomware_prot():
    """Enable Ransomware Protection (Controlled Folder Access)"""
    try:
        subprocess.Popen(['powershell', '-Command', 'Set-MpPreference -EnableControlledFolderAccess Enabled'], creationflags=0x08000000)
        return {'success': True, 'message': 'Controlled Folder Access (Ransomware protection) enabled.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _offline_rootkit_scan():
    """Schedule Offline Rootkit Scan"""
    try:
        subprocess.Popen(['powershell', '-Command', 'Start-MpWDOScan'], creationflags=0x08000000)
        return {'success': True, 'message': 'Windows Defender Offline Scan triggered (System will restart shortly).'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


PRIVACY_DEEP_UTILITIES = [
    {'id': 'loc_off', 'name': 'Disable Location', 'desc': 'Turn off location tracking', 'category': 'privacy_deep', 'icon': '📍', 'color': '#ef4444', 'run': _disable_location},
    {'id': 'ad_id_off', 'name': 'Disable Ad ID', 'desc': 'Stop personalized ads', 'category': 'privacy_deep', 'icon': '🎯', 'color': '#f97316', 'run': _disable_ad_id},
    {'id': 'feedback_off', 'name': 'Disable Feedback', 'desc': 'Stop nagging feedback popups', 'category': 'privacy_deep', 'icon': '💬', 'color': '#3b82f6', 'run': _disable_feedback},
    {'id': 'timeline_off', 'name': 'Disable Timeline', 'desc': 'Turn off activity history', 'category': 'privacy_deep', 'icon': '⏳', 'color': '#8b5cf6', 'run': _disable_timeline},
    {'id': 'bg_apps_off', 'name': 'Stop BG Apps', 'desc': 'Block UWP apps in bg', 'category': 'privacy_deep', 'icon': '🛑', 'color': '#ec4899', 'run': _restrict_bg_apps},
    {'id': 'cam_off', 'name': 'Disable Camera', 'desc': 'Deny webcam to all apps', 'category': 'privacy_deep', 'icon': '📷', 'color': '#14b8a6', 'run': _disable_camera},
    {'id': 'mic_off', 'name': 'Disable Mic', 'desc': 'Deny mic to all apps', 'category': 'privacy_deep', 'icon': '🎙️', 'color': '#f59e0b', 'run': _disable_mic},
    {'id': 'clr_defender', 'name': 'Clear Defender', 'desc': 'Wipe protection history', 'category': 'privacy_deep', 'icon': '🛡️', 'color': '#10b981', 'run': _clear_defender_history},
    {'id': 'ransom_prot', 'name': 'Ransomware Prot.', 'desc': 'Enable Controlled Folders', 'category': 'privacy_deep', 'icon': '🔐', 'color': '#6366f1', 'run': _enable_ransomware_prot},
    {'id': 'rootkit_scan', 'name': 'Offline Scan', 'desc': 'Restart for deep rootkit scan', 'category': 'privacy_deep', 'icon': '☣️', 'color': '#ef4444', 'run': _offline_rootkit_scan},
]
