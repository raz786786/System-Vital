"""
Service Utilities — Manage Windows background services
"""

import subprocess

def _restart_audio():
    """Restart Windows Audio service"""
    try:
        subprocess.Popen(
            ['powershell', '-Command', 'Restart-Service -Name Audiosrv -Force'],
            creationflags=0x08000000
        )
        return {'success': True, 'message': 'Windows Audio service restarting...'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _restart_print_spooler():
    """Restart Print Spooler service"""
    try:
        subprocess.Popen(
            ['powershell', '-Command', 'Restart-Service -Name Spooler -Force'],
            creationflags=0x08000000
        )
        return {'success': True, 'message': 'Print Spooler service restarting...'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _restart_windows_update():
    """Restart Windows Update service"""
    try:
        subprocess.Popen(
            ['powershell', '-Command', 'Restart-Service -Name wuauserv -Force'],
            creationflags=0x08000000
        )
        return {'success': True, 'message': 'Windows Update service restarting...'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _restart_bluetooth():
    """Restart Bluetooth Support Service"""
    try:
        subprocess.Popen(
            ['powershell', '-Command', 'Restart-Service -Name bthserv -Force'],
            creationflags=0x08000000
        )
        return {'success': True, 'message': 'Bluetooth service restarting...'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _restart_explorer():
    """Restart Windows Explorer"""
    try:
        subprocess.Popen(
            ['powershell', '-Command', 'Stop-Process -Name explorer -Force'],
            creationflags=0x08000000
        )
        return {'success': True, 'message': 'Windows Explorer restarted.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _list_failed_services():
    """List services that failed to start"""
    try:
        result = subprocess.run(
            ['powershell', '-Command', 'Get-WmiObject win32_service | Where-Object {$_.State -ne "Running" -and $_.StartMode -eq "Auto"} | Select-Object Name, DisplayName | Out-String'],
            capture_output=True, text=True, timeout=15, creationflags=0x08000000
        )
        if result.stdout.strip():
            return {'success': True, 'message': f'Failed auto-start services:\n{result.stdout.strip()}'}
        return {'success': True, 'message': 'All automatic services are running correctly.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

SERVICES_UTILITIES = [
    {'id': 'audio_srv', 'name': 'Restart Audio', 'desc': 'Fix no sound issues', 'category': 'services', 'icon': '🔊', 'color': '#3b82f6', 'run': _restart_audio},
    {'id': 'print_srv', 'name': 'Restart Print Spooler', 'desc': 'Fix printer stuck in queue', 'category': 'services', 'icon': '🖨️', 'color': '#8b5cf6', 'run': _restart_print_spooler},
    {'id': 'wu_srv', 'name': 'Restart Win Update', 'desc': 'Fix stuck updates', 'category': 'services', 'icon': '🔄', 'color': '#10b981', 'run': _restart_windows_update},
    {'id': 'bt_srv', 'name': 'Restart Bluetooth', 'desc': 'Fix connection issues', 'category': 'services', 'icon': '🦷', 'color': '#0ea5e9', 'run': _restart_bluetooth},
    {'id': 'explorer_srv', 'name': 'Restart Explorer', 'desc': 'Fix frozen taskbar', 'category': 'services', 'icon': '📁', 'color': '#f59e0b', 'run': _restart_explorer},
    {'id': 'failed_srv', 'name': 'List Failed Services', 'desc': 'Check auto-start failures', 'category': 'services', 'icon': '⚠️', 'color': '#ef4444', 'run': _list_failed_services},
]
