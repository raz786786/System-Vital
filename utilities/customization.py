"""
Customization Utilities — Windows appearance and behavior tweaks
"""

import subprocess

def _dark_mode_on():
    """Enable Windows Dark Mode"""
    try:
        subprocess.run(
            ['reg', 'add', r'HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize', '/v', 'AppsUseLightTheme', '/t', 'REG_DWORD', '/d', '0', '/f'],
            capture_output=True, creationflags=0x08000000
        )
        subprocess.run(
            ['reg', 'add', r'HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize', '/v', 'SystemUsesLightTheme', '/t', 'REG_DWORD', '/d', '0', '/f'],
            capture_output=True, creationflags=0x08000000
        )
        return {'success': True, 'message': 'Dark Mode enabled.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _light_mode_on():
    """Enable Windows Light Mode"""
    try:
        subprocess.run(
            ['reg', 'add', r'HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize', '/v', 'AppsUseLightTheme', '/t', 'REG_DWORD', '/d', '1', '/f'],
            capture_output=True, creationflags=0x08000000
        )
        subprocess.run(
            ['reg', 'add', r'HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize', '/v', 'SystemUsesLightTheme', '/t', 'REG_DWORD', '/d', '1', '/f'],
            capture_output=True, creationflags=0x08000000
        )
        return {'success': True, 'message': 'Light Mode enabled.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _show_hidden_files():
    """Show hidden files in Explorer"""
    try:
        subprocess.run(
            ['reg', 'add', r'HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced', '/v', 'Hidden', '/t', 'REG_DWORD', '/d', '1', '/f'],
            capture_output=True, creationflags=0x08000000
        )
        return {'success': True, 'message': 'Hidden files are now visible.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _show_file_extensions():
    """Show file extensions in Explorer"""
    try:
        subprocess.run(
            ['reg', 'add', r'HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced', '/v', 'HideFileExt', '/t', 'REG_DWORD', '/d', '0', '/f'],
            capture_output=True, creationflags=0x08000000
        )
        return {'success': True, 'message': 'File extensions are now visible.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _taskbar_left():
    """Align Windows 11 taskbar to the left"""
    try:
        subprocess.run(
            ['reg', 'add', r'HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced', '/v', 'TaskbarAl', '/t', 'REG_DWORD', '/d', '0', '/f'],
            capture_output=True, creationflags=0x08000000
        )
        return {'success': True, 'message': 'Taskbar aligned to Left (Restart Explorer to apply).'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _taskbar_center():
    """Align Windows 11 taskbar to the center"""
    try:
        subprocess.run(
            ['reg', 'add', r'HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced', '/v', 'TaskbarAl', '/t', 'REG_DWORD', '/d', '1', '/f'],
            capture_output=True, creationflags=0x08000000
        )
        return {'success': True, 'message': 'Taskbar aligned to Center (Restart Explorer to apply).'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

CUSTOMIZATION_UTILITIES = [
    {'id': 'dark_mode', 'name': 'Dark Mode On', 'desc': 'Enable system dark theme', 'category': 'customization', 'icon': '🌙', 'color': '#a855f7', 'run': _dark_mode_on},
    {'id': 'light_mode', 'name': 'Light Mode On', 'desc': 'Enable system light theme', 'category': 'customization', 'icon': '☀️', 'color': '#eab308', 'run': _light_mode_on},
    {'id': 'show_hidden', 'name': 'Show Hidden Files', 'desc': 'Show hidden items in Explorer', 'category': 'customization', 'icon': '👁️', 'color': '#3b82f6', 'run': _show_hidden_files},
    {'id': 'show_ext', 'name': 'Show Extensions', 'desc': 'Show file name extensions', 'category': 'customization', 'icon': '📄', 'color': '#10b981', 'run': _show_file_extensions},
    {'id': 'taskbar_left', 'name': 'Taskbar Left', 'desc': 'Win11 Taskbar to Left', 'category': 'customization', 'icon': '⬅️', 'color': '#f97316', 'run': _taskbar_left},
    {'id': 'taskbar_center', 'name': 'Taskbar Center', 'desc': 'Win11 Taskbar to Center', 'category': 'customization', 'icon': '↔️', 'color': '#ec4899', 'run': _taskbar_center},
]
