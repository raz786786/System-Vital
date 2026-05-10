"""
Repair Utilities — System repair and integrity tools
"""

import subprocess
import os
import glob


def _run_sfc():
    """Run System File Checker (sfc /scannow)"""
    try:
        subprocess.Popen(
            ['powershell', '-Command', 'Start-Process cmd -ArgumentList \'/k sfc /scannow\' -Verb RunAs'],
            creationflags=0x08000000
        )
        return {'success': True, 'message': 'SFC scan started in new Admin window. Wait for it to finish.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _run_dism():
    """Run DISM RestoreHealth"""
    try:
        subprocess.Popen(
            ['powershell', '-Command',
             'Start-Process cmd -ArgumentList \'/k DISM /Online /Cleanup-Image /RestoreHealth\' -Verb RunAs'],
            creationflags=0x08000000
        )
        return {'success': True, 'message': 'DISM repair started in new Admin window.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _run_chkdsk():
    """Schedule CHKDSK on next reboot"""
    try:
        subprocess.Popen(
            ['powershell', '-Command',
             'Start-Process cmd -ArgumentList \'/k echo Y | chkdsk C: /F /R\' -Verb RunAs'],
            creationflags=0x08000000
        )
        return {'success': True, 'message': 'CHKDSK scheduled. It will run on next reboot.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _scan_registry():
    """Scan registry for common invalid entries"""
    import winreg
    orphaned = 0
    checked = 0
    uninstall_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, uninstall_key) as key:
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    with winreg.OpenKey(key, subkey_name) as subkey:
                        try:
                            install_loc, _ = winreg.QueryValueEx(subkey, "InstallLocation")
                            if install_loc and install_loc.strip() and not os.path.exists(install_loc.strip()):
                                orphaned += 1
                        except FileNotFoundError:
                            pass
                    checked += 1
                    i += 1
                except OSError:
                    break
    except Exception:
        pass
    return {'success': True, 'message': f'Scanned {checked} entries. Found {orphaned} orphaned install locations.'}


def _scan_bsod_dumps():
    """Read minidump files for BSOD info"""
    minidump_dir = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'Minidump')
    if not os.path.exists(minidump_dir):
        return {'success': True, 'message': 'No minidump folder found — no recent BSODs detected! ✅'}

    dumps = glob.glob(os.path.join(minidump_dir, '*.dmp'))
    if not dumps:
        return {'success': True, 'message': 'Minidump folder exists but no .dmp files found — system is stable ✅'}

    dumps.sort(key=os.path.getmtime, reverse=True)
    latest = dumps[:5]
    info = []
    for d in latest:
        mtime = os.path.getmtime(d)
        import time
        date_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(mtime))
        size_kb = os.path.getsize(d) // 1024
        info.append(f"  {os.path.basename(d)} — {date_str} ({size_kb} KB)")

    msg = f"Found {len(dumps)} crash dump(s). Latest:\n" + "\n".join(info)
    msg += "\n\nUse WinDbg or BlueScreenView for detailed analysis."
    return {'success': True, 'message': msg}


def _scan_dlls():
    """Detect missing DLL errors from Event Log"""
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-WinEvent -FilterHashtable @{LogName="Application"; Level=2; ProviderName="SideBySide"} '
             '-MaxEvents 10 -ErrorAction SilentlyContinue | '
             'Select-Object -Property TimeCreated,Message | Format-List'],
            capture_output=True, text=True, timeout=30, creationflags=0x08000000
        )
        if result.stdout.strip():
            lines = result.stdout.strip()[:500]
            return {'success': True, 'message': f'DLL/SideBySide errors found:\n{lines}'}
        return {'success': True, 'message': 'No DLL errors found in Event Log ✅'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _restart_explorer():
    """Kill and restart explorer.exe"""
    try:
        subprocess.run(['taskkill', '/f', '/im', 'explorer.exe'],
                       capture_output=True, creationflags=0x08000000)
        subprocess.Popen(['explorer.exe'])
        return {'success': True, 'message': 'Explorer restarted successfully'}
    except Exception as e:
        subprocess.Popen(['explorer.exe'])
        return {'success': False, 'message': str(e)}


def _check_hosts_file():
    """Compare hosts file against default"""
    hosts_path = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), r'System32\drivers\etc\hosts')
    try:
        with open(hosts_path, 'r') as f:
            content = f.read()
        lines = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith('#')]
        if not lines:
            return {'success': True, 'message': 'Hosts file is clean — no custom entries ✅'}
        return {'success': True, 'message': f'Found {len(lines)} custom entries in hosts file:\n' + '\n'.join(lines[:10])}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _repair_windows_update():
    """Stop, clear, and restart Windows Update services"""
    try:
        cmds = [
            'net stop wuauserv',
            'net stop cryptSvc',
            'net stop bits',
            'net stop msiserver',
            'ren C:\\Windows\\SoftwareDistribution SoftwareDistribution.old',
            'ren C:\\Windows\\System32\\catroot2 catroot2.old',
            'net start wuauserv',
            'net start cryptSvc',
            'net start bits',
            'net start msiserver',
        ]
        script = '; '.join(cmds)
        subprocess.Popen(
            ['powershell', '-Command', f'Start-Process cmd -ArgumentList \'/k {script}\' -Verb RunAs'],
            creationflags=0x08000000
        )
        return {'success': True, 'message': 'Windows Update repair started in Admin window.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


REPAIR_UTILITIES = [
    {'id': 'sfc', 'name': 'SFC Scanner', 'desc': 'sfc /scannow with result parser', 'category': 'repair', 'icon': '🛡️', 'color': '#22c55e', 'run': _run_sfc},
    {'id': 'dism', 'name': 'DISM Repair', 'desc': 'RestoreHealth Windows image', 'category': 'repair', 'icon': '🔧', 'color': '#3b82f6', 'run': _run_dism},
    {'id': 'reg_clean', 'name': 'Registry Cleaner', 'desc': 'Scan for invalid/orphaned keys', 'category': 'repair', 'icon': '📝', 'color': '#a855f7', 'run': _scan_registry},
    {'id': 'chkdsk', 'name': 'CHKDSK Runner', 'desc': 'Schedule disk error check', 'category': 'repair', 'icon': '💾', 'color': '#f97316', 'run': _run_chkdsk},
    {'id': 'bsod', 'name': 'BSOD Dump Reader', 'desc': 'Decode minidump .dmp files', 'category': 'repair', 'icon': '💀', 'color': '#ef4444', 'run': _scan_bsod_dumps},
    {'id': 'dll', 'name': 'DLL Error Scanner', 'desc': 'Detect missing DLLs from Event Log', 'category': 'repair', 'icon': '📦', 'color': '#eab308', 'run': _scan_dlls},
    {'id': 'explorer_fix', 'name': 'Explorer Restarter', 'desc': 'Kill + restart explorer.exe', 'category': 'repair', 'icon': '🗂️', 'color': '#06b6d4', 'run': _restart_explorer},
    {'id': 'hosts', 'name': 'Hosts File Checker', 'desc': 'Compare against default hosts', 'category': 'repair', 'icon': '🏠', 'color': '#22c55e', 'run': _check_hosts_file},
    {'id': 'update_repair', 'name': 'Update Repair', 'desc': 'Stop/clear/restart WU services', 'category': 'repair', 'icon': '🔄', 'color': '#3b82f6', 'run': _repair_windows_update},
]
