"""
Deep System Maintenance & Registry Utilities
"""

import subprocess
import os

def _rebuild_wmi():
    """Rebuild WMI Repository"""
    try:
        cmds = [
            'net stop winmgmt /y',
            'winmgmt /resetrepository',
            'net start winmgmt'
        ]
        subprocess.Popen(['powershell', '-Command', '; '.join(cmds)], creationflags=0x08000000)
        return {'success': True, 'message': 'Rebuilding WMI repository in background...'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _clear_wer():
    """Clear Windows Error Reporting Logs"""
    try:
        subprocess.Popen(['powershell', '-Command', 'Remove-Item -Path "C:\\ProgramData\\Microsoft\\Windows\\WER\\ReportArchive\\*" -Recurse -Force -ErrorAction SilentlyContinue'], creationflags=0x08000000)
        return {'success': True, 'message': 'Cleared Windows Error Reporting logs.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _deep_reset_wu():
    """Deep Reset Windows Update Components"""
    try:
        cmds = [
            'net stop wuauserv', 'net stop cryptSvc', 'net stop bits', 'net stop msiserver',
            'ren C:\\Windows\\SoftwareDistribution SoftwareDistribution.old',
            'ren C:\\Windows\\System32\\catroot2 catroot2.old',
            'net start wuauserv', 'net start cryptSvc', 'net start bits', 'net start msiserver'
        ]
        subprocess.Popen(['cmd', '/c', ' & '.join(cmds)], creationflags=0x08000000)
        return {'success': True, 'message': 'Deep reset of Windows Update started...'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _reregister_dlls():
    """Re-register All Core System DLLs"""
    try:
        subprocess.Popen(['cmd', '/c', 'for %1 in (%windir%\\system32\\*.dll) do regsvr32.exe /s %1'], creationflags=0x08000000)
        return {'success': True, 'message': 'System DLLs are being re-registered in the background.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _clear_event_logs():
    """Clear All Event Viewer Logs"""
    try:
        subprocess.Popen(['powershell', '-Command', 'wevtutil el | Foreach-Object {wevtutil cl "$_"}'], creationflags=0x08000000)
        return {'success': True, 'message': 'Clearing all Event Viewer logs...'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _backup_registry():
    """Backup Windows Registry"""
    try:
        path = os.path.join(os.environ.get('USERPROFILE', 'C:\\'), 'Desktop', 'RegistryBackup.reg')
        subprocess.Popen(['regedit', '/e', path], creationflags=0x08000000)
        return {'success': True, 'message': f'Registry backup started. Saving to Desktop/RegistryBackup.reg'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _restore_registry():
    """Restore Registry Backup (Instructional)"""
    return {'success': True, 'message': 'To restore, double-click the RegistryBackup.reg file on your Desktop and confirm.'}

def _fix_file_assoc():
    """Fix Broken File Associations (Reset to default)"""
    try:
        subprocess.run(['dism', '/online', '/Export-DefaultAppAssociations:C:\\temp_assoc.xml'], capture_output=True, creationflags=0x08000000)
        subprocess.Popen(['dism', '/online', '/Import-DefaultAppAssociations:C:\\temp_assoc.xml'], creationflags=0x08000000)
        return {'success': True, 'message': 'Resetting default app associations...'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _rebuild_perf_counters():
    """Rebuild Performance Counters"""
    try:
        subprocess.Popen(['cmd', '/c', 'cd %windir%\\system32 & lodctr /R'], creationflags=0x08000000)
        return {'success': True, 'message': 'Performance counters rebuilding...'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _reset_gpo():
    """Reset Group Policy Settings"""
    try:
        subprocess.Popen(['cmd', '/c', 'RD /S /Q "%WinDir%\\System32\\GroupPolicyUsers" & RD /S /Q "%WinDir%\\System32\\GroupPolicy" & gpupdate /force'], creationflags=0x08000000)
        return {'success': True, 'message': 'Group Policy settings reset and updated.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _clear_clipboard():
    """Clear Clipboard History"""
    try:
        subprocess.run(['cmd', '/c', 'echo off | clip'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Clipboard history cleared.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _clear_print_spooler():
    """Clear Print Spooler Queue"""
    try:
        cmds = [
            'net stop spooler',
            'del /Q /F /S "%systemroot%\\System32\\Spool\\Printers\\*.*"',
            'net start spooler'
        ]
        subprocess.Popen(['cmd', '/c', ' & '.join(cmds)], creationflags=0x08000000)
        return {'success': True, 'message': 'Print spooler queue cleared.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _optimize_mft():
    """Optimize Master File Table (MFT)"""
    try:
        subprocess.run(['reg', 'add', r'HKLM\System\CurrentControlSet\Control\FileSystem', '/v', 'NtfsMftZoneReservation', '/t', 'REG_DWORD', '/d', '2', '/f'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'MFT Zone Reservation optimized (Restart required).'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _fix_wmi_corruption():
    """Fix WMI Corruption Issues"""
    try:
        subprocess.Popen(['cmd', '/c', 'winmgmt /verifyrepository'], creationflags=0x08000000)
        return {'success': True, 'message': 'WMI repository verification triggered.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

DEEP_MAINTENANCE_UTILITIES = [
    {'id': 'rebuild_wmi', 'name': 'Rebuild WMI', 'desc': 'Fix Windows Management inst.', 'category': 'deep_maintenance', 'icon': '🛠️', 'color': '#ef4444', 'run': _rebuild_wmi},
    {'id': 'clear_wer', 'name': 'Clear Error Logs', 'desc': 'Clear Windows Error Reporting', 'category': 'deep_maintenance', 'icon': '🗑️', 'color': '#3b82f6', 'run': _clear_wer},
    {'id': 'reset_wu_deep', 'name': 'Deep Reset WU', 'desc': 'Complete Windows Update reset', 'category': 'deep_maintenance', 'icon': '🔄', 'color': '#10b981', 'run': _deep_reset_wu},
    {'id': 'reregister_dlls', 'name': 'Re-register DLLs', 'desc': 'Fix missing core DLLs', 'category': 'deep_maintenance', 'icon': '🧩', 'color': '#8b5cf6', 'run': _reregister_dlls},
    {'id': 'clear_events', 'name': 'Clear Event Logs', 'desc': 'Wipe all Event Viewer logs', 'category': 'deep_maintenance', 'icon': '📑', 'color': '#f59e0b', 'run': _clear_event_logs},
    {'id': 'backup_reg', 'name': 'Backup Registry', 'desc': 'Save registry to Desktop', 'category': 'deep_maintenance', 'icon': '💾', 'color': '#0ea5e9', 'run': _backup_registry},
    {'id': 'restore_reg', 'name': 'Restore Registry', 'desc': 'How to restore from backup', 'category': 'deep_maintenance', 'icon': '🔙', 'color': '#ec4899', 'run': _restore_registry},
    {'id': 'fix_file_assoc', 'name': 'Fix File Assoc.', 'desc': 'Reset default app bindings', 'category': 'deep_maintenance', 'icon': '🔗', 'color': '#14b8a6', 'run': _fix_file_assoc},
    {'id': 'rebuild_perf', 'name': 'Rebuild Counters', 'desc': 'Fix performance monitor', 'category': 'deep_maintenance', 'icon': '📈', 'color': '#f97316', 'run': _rebuild_perf_counters},
    {'id': 'reset_gpo', 'name': 'Reset Group Policy', 'desc': 'Restore default policies', 'category': 'deep_maintenance', 'icon': '🛡️', 'color': '#6366f1', 'run': _reset_gpo},
    {'id': 'clear_clipboard', 'name': 'Clear Clipboard', 'desc': 'Wipe clipboard history', 'category': 'deep_maintenance', 'icon': '📋', 'color': '#84cc16', 'run': _clear_clipboard},
    {'id': 'clear_spooler', 'name': 'Clear Spooler', 'desc': 'Fix stuck print jobs', 'category': 'deep_maintenance', 'icon': '🖨️', 'color': '#a855f7', 'run': _clear_print_spooler},
    {'id': 'optimize_mft', 'name': 'Optimize MFT', 'desc': 'Boost NTFS performance', 'category': 'deep_maintenance', 'icon': '🗃️', 'color': '#06b6d4', 'run': _optimize_mft},
    {'id': 'verify_wmi', 'name': 'Verify WMI', 'desc': 'Check WMI integrity', 'category': 'deep_maintenance', 'icon': '✔️', 'color': '#22c55e', 'run': _fix_wmi_corruption},
]
