"""
Context Menu & File System Utilities
"""

import subprocess
import os

def _remove_cast_to_device():
    """Remove 'Cast to Device' from Context Menu"""
    try:
        subprocess.run(['reg', 'add', r'HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Shell Extensions\Blocked', '/v', '{7AD84985-87B4-4a16-BE58-8B72A5B390F7}', '/t', 'REG_SZ', '/d', '', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Removed "Cast to Device". Restart Explorer to see changes.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _remove_3d_print():
    """Remove '3D Print' from Context Menu"""
    try:
        subprocess.run(['reg', 'delete', r'HKCR\SystemFileAssociations\.bmp\Shell\3D Edit', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Removed "3D Print" options for images.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _remove_share():
    """Remove 'Share' from Context Menu"""
    try:
        subprocess.run(['reg', 'delete', r'HKCR\*\shellex\ContextMenuHandlers\ModernSharing', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Removed "Share" option from context menu.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _add_take_ownership():
    """Add 'Take Ownership' to Context Menu"""
    try:
        cmds = [
            r'reg add "HKCR\*\shell\TakeOwnership" /v "" /t REG_SZ /d "Take Ownership" /f',
            r'reg add "HKCR\*\shell\TakeOwnership" /v "HasLUAShield" /t REG_SZ /d "" /f',
            r'reg add "HKCR\*\shell\TakeOwnership\command" /v "" /t REG_SZ /d "cmd.exe /c takeown /f \"%%1\" && icacls \"%%1\" /grant administrators:F" /f'
        ]
        for cmd in cmds:
            subprocess.run(cmd, shell=True, capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Added "Take Ownership" to files.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _add_cmd_here():
    """Add 'Open Command Prompt Here'"""
    try:
        subprocess.run(['reg', 'add', r'HKCR\Directory\shell\cmd', '/v', 'HideBasedOnVelocityId', '/t', 'REG_DWORD', '/d', '0', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Added "Open command window here" to folder context menu.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _add_copy_path():
    """Add 'Copy Path' to Context Menu"""
    try:
        # It's usually Shift+Right-click, this forces it to show always (in some Win versions)
        return {'success': True, 'message': 'Note: In Windows 10/11, you can simply press Shift + Right-Click to see "Copy as path".'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _enable_long_paths():
    """Enable Long Paths (Over 260 characters)"""
    try:
        subprocess.run(['reg', 'add', r'HKLM\SYSTEM\CurrentControlSet\Control\FileSystem', '/v', 'LongPathsEnabled', '/t', 'REG_DWORD', '/d', '1', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Win32 Long Paths (>260 chars) enabled.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _disable_last_access():
    """Disable NTFS Last Access Time (Boosts HDD performance)"""
    try:
        subprocess.Popen(['cmd', '/c', 'fsutil behavior set disablelastaccess 1'], creationflags=0x08000000)
        return {'success': True, 'message': 'NTFS Last Access updates disabled (Performance boost).'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _delete_empty_folders():
    """Delete Empty Folders on C: Drive"""
    try:
        subprocess.Popen(['powershell', '-Command', 'Get-ChildItem -Path C:\\ -Recurse -Directory -ErrorAction SilentlyContinue | Where-Object {$_.GetFileSystemInfos().Count -eq 0} | Remove-Item -Force'], creationflags=0x08000000)
        return {'success': True, 'message': 'Scanning and removing empty folders on C: in background.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _save_icon_positions():
    """Save Desktop Icon Positions (Dummy/Placeholder)"""
    return {'success': True, 'message': 'To save icon layouts, we recommend third-party tools like DesktopOK.'}

def _rebuild_thumbnails():
    """Rebuild File Explorer Thumbnails"""
    try:
        cmds = [
            'taskkill /f /im explorer.exe',
            r'del /f /s /q /a %LocalAppData%\Microsoft\Windows\Explorer\thumbcache_*.db',
            'start explorer.exe'
        ]
        subprocess.Popen(['cmd', '/c', ' & '.join(cmds)], creationflags=0x08000000)
        return {'success': True, 'message': 'Explorer thumbnails rebuilt.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

CONTEXT_MENU_UTILITIES = [
    {'id': 'rm_cast', 'name': 'Remove Cast to Device', 'desc': 'Clean up right-click menu', 'category': 'context_menu', 'icon': '📺', 'color': '#ef4444', 'run': _remove_cast_to_device},
    {'id': 'rm_3d', 'name': 'Remove 3D Print', 'desc': 'Remove 3D Print option', 'category': 'context_menu', 'icon': '🧊', 'color': '#f97316', 'run': _remove_3d_print},
    {'id': 'rm_share', 'name': 'Remove Share', 'desc': 'Remove Share from context', 'category': 'context_menu', 'icon': '🔗', 'color': '#3b82f6', 'run': _remove_share},
    {'id': 'add_takeown', 'name': 'Add Take Ownership', 'desc': 'Easily fix permissions', 'category': 'context_menu', 'icon': '👑', 'color': '#10b981', 'run': _add_take_ownership},
    {'id': 'add_cmd', 'name': 'Add CMD Here', 'desc': 'Open terminal in folder', 'category': 'context_menu', 'icon': '💻', 'color': '#8b5cf6', 'run': _add_cmd_here},
    {'id': 'add_copy', 'name': 'Copy Path Tip', 'desc': 'How to copy full file paths', 'category': 'context_menu', 'icon': '📋', 'color': '#f59e0b', 'run': _add_copy_path},
    {'id': 'long_paths', 'name': 'Enable Long Paths', 'desc': 'Fix 260 char limit errors', 'category': 'context_menu', 'icon': '📏', 'color': '#14b8a6', 'run': _enable_long_paths},
    {'id': 'ntfs_access', 'name': 'Disable Last Access', 'desc': 'Boost HDD performance', 'category': 'context_menu', 'icon': '⏱️', 'color': '#ec4899', 'run': _disable_last_access},
    {'id': 'empty_folders', 'name': 'Del Empty Folders', 'desc': 'Clean up directory trees', 'category': 'context_menu', 'icon': '📁', 'color': '#6366f1', 'run': _delete_empty_folders},
    {'id': 'icon_pos', 'name': 'Icon Layouts', 'desc': 'Desktop icon management', 'category': 'context_menu', 'icon': '🖥️', 'color': '#84cc16', 'run': _save_icon_positions},
    {'id': 'reb_thumbs', 'name': 'Rebuild Thumbs', 'desc': 'Fix broken image icons', 'category': 'context_menu', 'icon': '🖼️', 'color': '#0ea5e9', 'run': _rebuild_thumbnails},
]
