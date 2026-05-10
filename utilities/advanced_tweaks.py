"""
Advanced OS Tweaks & Workarounds
"""

import subprocess
import os

def _enable_god_mode():
    """Enable God Mode folder on Desktop"""
    try:
        path = os.path.join(os.environ.get('USERPROFILE', 'C:\\'), 'Desktop', 'GodMode.{ED7BA470-8E54-465E-825C-99712043E01C}')
        os.makedirs(path, exist_ok=True)
        return {'success': True, 'message': 'God Mode folder created on your Desktop.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _disable_lock_screen():
    """Disable Lock Screen"""
    try:
        subprocess.run(['reg', 'add', r'HKLM\SOFTWARE\Policies\Microsoft\Windows\Personalization', '/v', 'NoLockScreen', '/t', 'REG_DWORD', '/d', '1', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Lock screen disabled (boots straight to login).'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _disable_startup_sound():
    """Turn Off Windows Startup Sound"""
    try:
        subprocess.run(['reg', 'add', r'HKCU\AppEvents\EventLabels\WindowsLogon', '/v', 'ExcludeFromCPL', '/t', 'REG_DWORD', '/d', '1', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Startup sound disabled.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _verbose_boot():
    """Enable Verbose Boot Messages"""
    try:
        subprocess.run(['reg', 'add', r'HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System', '/v', 'verbosestatus', '/t', 'REG_DWORD', '/d', '1', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Verbose boot messages enabled.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _disable_fast_startup():
    """Disable Fast Startup"""
    try:
        subprocess.run(['reg', 'add', r'HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Power', '/v', 'HiberbootEnabled', '/t', 'REG_DWORD', '/d', '0', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Fast Startup disabled (helps fix dual boot/power issues).'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _force_hibernation():
    """Force Enable Hibernation Feature"""
    try:
        subprocess.Popen(['powercfg', '/hibernate', 'on'], creationflags=0x08000000)
        return {'success': True, 'message': 'Hibernation feature enabled.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _disable_aero_shake():
    """Turn Off Aero Shake"""
    try:
        subprocess.run(['reg', 'add', r'HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced', '/v', 'DisallowShaking', '/t', 'REG_DWORD', '/d', '1', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Aero Shake window minimizing disabled.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _disable_cortana():
    """Disable Cortana Completely"""
    try:
        subprocess.run(['reg', 'add', r'HKLM\SOFTWARE\Policies\Microsoft\Windows\Windows Search', '/v', 'AllowCortana', '/t', 'REG_DWORD', '/d', '0', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Cortana completely disabled via Group Policy.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _stop_driver_updates():
    """Stop Windows from Auto-Updating Drivers"""
    try:
        subprocess.run(['reg', 'add', r'HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate', '/v', 'ExcludeWUDriversInQualityUpdate', '/t', 'REG_DWORD', '/d', '1', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Windows Update will no longer automatically update drivers.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _remove_bloat_apps():
    """Remove Default Windows Bloat Apps"""
    try:
        subprocess.Popen(['powershell', '-Command', 'Get-AppxPackage *bing* | Remove-AppxPackage; Get-AppxPackage *zune* | Remove-AppxPackage; Get-AppxPackage *people* | Remove-AppxPackage'], creationflags=0x08000000)
        return {'success': True, 'message': 'Removing default bloat apps (Bing, Music, People) in background.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _reinstall_default_apps():
    """Reinstall Default Windows Apps"""
    try:
        subprocess.Popen(['powershell', '-Command', 'Get-AppxPackage -AllUsers| Foreach {Add-AppxPackage -DisableDevelopmentMode -Register "$($_.InstallLocation)\\AppXManifest.xml"}'], creationflags=0x08000000)
        return {'success': True, 'message': 'Re-registering all default Windows apps (This takes a while).'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _disable_ink():
    """Disable Windows Ink Workspace"""
    try:
        subprocess.run(['reg', 'add', r'HKLM\SOFTWARE\Policies\Microsoft\WindowsInkWorkspace', '/v', 'AllowWindowsInkWorkspace', '/t', 'REG_DWORD', '/d', '0', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Windows Ink Workspace disabled.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _clear_taskbar_cache():
    """Clear Taskbar Pinned Icon Cache"""
    try:
        subprocess.Popen(['cmd', '/c', r'DEL /F /S /Q /A "%AppData%\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\*"'], creationflags=0x08000000)
        return {'success': True, 'message': 'Taskbar icon cache cleared (you may need to re-pin apps).'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _reset_action_center():
    """Reset Windows Action Center"""
    try:
        subprocess.run(['reg', 'delete', r'HKCU\Software\Microsoft\Windows\CurrentVersion\ActionCenter', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Action Center registry reset. Restart Explorer to apply.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _clear_volume_history():
    """Clear Volume Control History"""
    try:
        subprocess.run(['reg', 'delete', r'HKCU\Software\Microsoft\Internet Explorer\LowRegistry\Audio\PolicyConfig\PropertyStore', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Volume control history for apps cleared.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

ADVANCED_TWEAKS_UTILITIES = [
    {'id': 'god_mode', 'name': 'Enable God Mode', 'desc': 'Create God Mode folder', 'category': 'advanced_tweaks', 'icon': '⚡', 'color': '#f59e0b', 'run': _enable_god_mode},
    {'id': 'no_lock_screen', 'name': 'No Lock Screen', 'desc': 'Skip lock screen on boot', 'category': 'advanced_tweaks', 'icon': '🔓', 'color': '#3b82f6', 'run': _disable_lock_screen},
    {'id': 'no_startup_snd', 'name': 'No Startup Sound', 'desc': 'Mute boot sound', 'category': 'advanced_tweaks', 'icon': '🔇', 'color': '#ef4444', 'run': _disable_startup_sound},
    {'id': 'verbose_boot', 'name': 'Verbose Boot', 'desc': 'Show detailed boot msgs', 'category': 'advanced_tweaks', 'icon': '📝', 'color': '#10b981', 'run': _verbose_boot},
    {'id': 'no_fast_boot', 'name': 'No Fast Startup', 'desc': 'Fix hybrid sleep issues', 'category': 'advanced_tweaks', 'icon': '🐢', 'color': '#8b5cf6', 'run': _disable_fast_startup},
    {'id': 'force_hiber', 'name': 'Force Hibernate', 'desc': 'Enable hibernation', 'category': 'advanced_tweaks', 'icon': '💤', 'color': '#0ea5e9', 'run': _force_hibernation},
    {'id': 'no_aero_shake', 'name': 'No Aero Shake', 'desc': 'Disable window shake', 'category': 'advanced_tweaks', 'icon': '🪟', 'color': '#ec4899', 'run': _disable_aero_shake},
    {'id': 'no_cortana', 'name': 'Disable Cortana', 'desc': 'Turn off Cortana completely', 'category': 'advanced_tweaks', 'icon': '🎙️', 'color': '#6366f1', 'run': _disable_cortana},
    {'id': 'no_driver_up', 'name': 'Stop Driver Updates', 'desc': 'Stop WU driver updates', 'category': 'advanced_tweaks', 'icon': '🛑', 'color': '#ef4444', 'run': _stop_driver_updates},
    {'id': 'rm_bloat', 'name': 'Remove Bloat Apps', 'desc': 'Uninstall default apps', 'category': 'advanced_tweaks', 'icon': '🗑️', 'color': '#14b8a6', 'run': _remove_bloat_apps},
    {'id': 'reinstall_apps', 'name': 'Reinstall Apps', 'desc': 'Fix missing default apps', 'category': 'advanced_tweaks', 'icon': '🔄', 'color': '#f97316', 'run': _reinstall_default_apps},
    {'id': 'no_ink', 'name': 'Disable Win Ink', 'desc': 'Turn off Ink Workspace', 'category': 'advanced_tweaks', 'icon': '✒️', 'color': '#84cc16', 'run': _disable_ink},
    {'id': 'clr_taskbar', 'name': 'Clear Taskbar Icons', 'desc': 'Wipe pinned icons', 'category': 'advanced_tweaks', 'icon': '🧹', 'color': '#64748b', 'run': _clear_taskbar_cache},
    {'id': 'reset_action', 'name': 'Reset Action Center', 'desc': 'Fix broken notifications', 'category': 'advanced_tweaks', 'icon': '💬', 'color': '#3b82f6', 'run': _reset_action_center},
    {'id': 'clr_vol', 'name': 'Clear Vol History', 'desc': 'Reset app volume mixers', 'category': 'advanced_tweaks', 'icon': '🔊', 'color': '#a855f7', 'run': _clear_volume_history},
]
