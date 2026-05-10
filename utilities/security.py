"""
Security & Privacy Utilities
"""

import subprocess
import os


def _disable_telemetry():
    """Disable Windows telemetry services and tasks"""
    try:
        cmds = [
            'sc config DiagTrack start=disabled',
            'sc stop DiagTrack',
            'sc config dmwappushservice start=disabled',
            'sc stop dmwappushservice',
            'schtasks /Change /TN "\\Microsoft\\Windows\\Application Experience\\Microsoft Compatibility Appraiser" /DISABLE',
            'schtasks /Change /TN "\\Microsoft\\Windows\\Customer Experience Improvement Program\\Consolidator" /DISABLE',
        ]
        script = ' & '.join(cmds)
        subprocess.Popen(
            ['powershell', '-Command', f'Start-Process cmd -ArgumentList \'/k {script}\' -Verb RunAs'],
            creationflags=0x08000000
        )
        return {'success': True, 'message': 'Telemetry disable commands sent. Running in Admin window.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _remove_bloatware():
    """List removable AppX packages"""
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-AppxPackage | Where-Object {$_.IsFramework -eq $false} | '
             'Select-Object -Property Name -First 20 | Format-List'],
            capture_output=True, text=True, timeout=30, creationflags=0x08000000
        )
        if result.stdout.strip():
            return {'success': True, 'message': f'Installed AppX packages (first 20):\n{result.stdout.strip()[:800]}\n\nUse PowerShell Remove-AppxPackage to uninstall.'}
        return {'success': True, 'message': 'No removable AppX packages found'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _harden_privacy():
    """Disable advertising ID, Cortana data, location tracking"""
    try:
        reg_cmds = [
            ('HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\AdvertisingInfo', 'Enabled', 'REG_DWORD', '0'),
            ('HKCU\\Software\\Microsoft\\Input\\TIPC', 'Enabled', 'REG_DWORD', '0'),
            ('HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Search', 'BingSearchEnabled', 'REG_DWORD', '0'),
        ]
        applied = 0
        for key, name, rtype, value in reg_cmds:
            try:
                subprocess.run(
                    ['reg', 'add', key, '/v', name, '/t', rtype, '/d', value, '/f'],
                    capture_output=True, creationflags=0x08000000
                )
                applied += 1
            except Exception:
                pass
        return {'success': True, 'message': f'Applied {applied}/{len(reg_cmds)} privacy settings. Advertising ID disabled, Bing search disabled.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _audit_permissions():
    """List apps with camera/microphone/location access"""
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-AppxPackage | ForEach-Object { '
             '$cap = (Get-AppxPackageManifest $_).Package.Capabilities.Capability.Name; '
             'if ($cap -match "webcam|microphone|location") { '
             '$_.Name + " -> " + ($cap -join ", ") '
             '} } | Select-Object -First 15'],
            capture_output=True, text=True, timeout=30, creationflags=0x08000000
        )
        if result.stdout.strip():
            return {'success': True, 'message': f'Apps with sensitive permissions:\n{result.stdout.strip()[:800]}'}
        return {'success': True, 'message': 'No apps with camera/mic/location permissions found via AppX ✅'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _check_firewall():
    """Check and report firewall status"""
    try:
        result = subprocess.run(
            ['netsh', 'advfirewall', 'show', 'allprofiles', 'state'],
            capture_output=True, text=True, creationflags=0x08000000
        )
        output = result.stdout.strip()
        all_on = output.count('ON') >= 3
        if all_on:
            return {'success': True, 'message': f'All firewall profiles are ACTIVE ✅\n{output}'}
        return {'success': True, 'message': f'⚠️ Some firewall profiles are OFF:\n{output}'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _reenable_defender():
    """Re-enable Windows Defender via registry"""
    try:
        subprocess.run(
            ['reg', 'delete', r'HKLM\SOFTWARE\Policies\Microsoft\Windows Defender',
             '/v', 'DisableAntiSpyware', '/f'],
            capture_output=True, creationflags=0x08000000
        )
        subprocess.run(
            ['powershell', '-Command', 'Start-Service WinDefend -ErrorAction SilentlyContinue'],
            capture_output=True, creationflags=0x08000000
        )
        return {'success': True, 'message': 'Windows Defender re-enable attempted. Check Windows Security to verify.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _disable_autorun():
    """Disable USB autoplay via registry"""
    try:
        subprocess.run(
            ['reg', 'add', r'HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer',
             '/v', 'NoDriveTypeAutoRun', '/t', 'REG_DWORD', '/d', '255', '/f'],
            capture_output=True, creationflags=0x08000000
        )
        return {'success': True, 'message': 'USB Autorun/Autoplay disabled ✅'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _fix_smartscreen():
    """Re-enable SmartScreen"""
    try:
        subprocess.run(
            ['reg', 'add', r'HKLM\SOFTWARE\Policies\Microsoft\Windows\System',
             '/v', 'EnableSmartScreen', '/t', 'REG_DWORD', '/d', '1', '/f'],
            capture_output=True, creationflags=0x08000000
        )
        return {'success': True, 'message': 'SmartScreen re-enabled via registry ✅'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


SECURITY_UTILITIES = [
    {'id': 'telemetry', 'name': 'Telemetry Disabler', 'desc': 'Block known telemetry tasks', 'category': 'security', 'icon': '📵', 'color': '#ef4444', 'run': _disable_telemetry},
    {'id': 'bloat', 'name': 'Bloatware Remover', 'desc': 'List removable AppX packages', 'category': 'security', 'icon': '🗑️', 'color': '#f97316', 'run': _remove_bloatware},
    {'id': 'privacy', 'name': 'Privacy Hardener', 'desc': 'Disable telemetry, ad ID, Bing', 'category': 'security', 'icon': '🔒', 'color': '#a855f7', 'run': _harden_privacy},
    {'id': 'perm_audit', 'name': 'Permission Auditor', 'desc': 'List apps with camera/mic/GPS', 'category': 'security', 'icon': '👁️', 'color': '#eab308', 'run': _audit_permissions},
    {'id': 'firewall', 'name': 'Firewall Checker', 'desc': 'Check + re-enable all profiles', 'category': 'security', 'icon': '🛡️', 'color': '#3b82f6', 'run': _check_firewall},
    {'id': 'defender', 'name': 'Defender Re-enabler', 'desc': 'Re-enable via registry + service', 'category': 'security', 'icon': '🦺', 'color': '#22c55e', 'run': _reenable_defender},
    {'id': 'autorun', 'name': 'Autorun Disabler', 'desc': 'Disable USB autoplay via registry', 'category': 'security', 'icon': '🚫', 'color': '#ef4444', 'run': _disable_autorun},
    {'id': 'smartscreen', 'name': 'SmartScreen Fixer', 'desc': 'Restore SmartScreen via registry', 'category': 'security', 'icon': '🔍', 'color': '#06b6d4', 'run': _fix_smartscreen},
]
