"""
Process Utilities — Manage running applications and background tasks
"""

import subprocess
import psutil

def _kill_top_cpu():
    """Kill the highest CPU consuming process (excluding system)"""
    try:
        procs = sorted(psutil.process_iter(['pid', 'name', 'cpu_percent']), key=lambda p: p.info['cpu_percent'], reverse=True)
        for p in procs:
            name = p.info['name'].lower()
            if name not in ['system idle process', 'system', 'registry', 'smss.exe', 'csrss.exe', 'wininit.exe', 'services.exe']:
                pid = p.info['pid']
                pname = p.info['name']
                subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True, creationflags=0x08000000)
                return {'success': True, 'message': f'Killed top CPU consumer: {pname} (PID: {pid})'}
        return {'success': True, 'message': 'No safe process found to kill.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _list_memory_hogs():
    """List top 10 memory consuming processes"""
    try:
        procs = sorted(psutil.process_iter(['name', 'memory_info']), key=lambda p: p.info.get('memory_info', getattr(p, 'memory_info', lambda: None)()).rss if p.info.get('memory_info') else 0, reverse=True)[:10]
        msg = "Top 10 Memory Hogs:\n" + "-"*30 + "\n"
        for p in procs:
            mem_mb = p.info['memory_info'].rss / (1024 * 1024)
            msg += f"{p.info['name']}: {mem_mb:.1f} MB\n"
        return {'success': True, 'message': msg}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _kill_zombie_processes():
    """Find and kill unresponsive processes"""
    try:
        result = subprocess.run(
            ['powershell', '-Command', 'Get-Process | Where-Object {$_.Responding -eq $false} | Stop-Process -Force -PassThru | Select-Object Name'],
            capture_output=True, text=True, timeout=15, creationflags=0x08000000
        )
        if result.stdout.strip():
            return {'success': True, 'message': f'Killed unresponsive processes:\n{result.stdout.strip()}'}
        return {'success': True, 'message': 'No unresponsive processes found.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _list_cpu_hogs():
    """List top 10 CPU consuming processes"""
    try:
        # psutil cpu_percent requires an interval, taking a quick sample
        for p in psutil.process_iter(['name', 'cpu_percent']):
            p.cpu_percent(interval=None)
        import time; time.sleep(0.5)
        procs = []
        for p in psutil.process_iter(['name', 'cpu_percent']):
            procs.append((p.info['name'], p.cpu_percent(interval=None)))
        procs = sorted(procs, key=lambda x: x[1], reverse=True)[:10]
        
        msg = "Top 10 CPU Consumers:\n" + "-"*30 + "\n"
        for name, cpu in procs:
            msg += f"{name}: {cpu}%\n"
        return {'success': True, 'message': msg}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _kill_all_browsers():
    """Force close all web browsers"""
    try:
        browsers = ['chrome.exe', 'msedge.exe', 'firefox.exe', 'brave.exe', 'opera.exe']
        killed = []
        for b in browsers:
            res = subprocess.run(['taskkill', '/F', '/IM', b], capture_output=True, creationflags=0x08000000)
            if res.returncode == 0:
                killed.append(b)
        if killed:
            return {'success': True, 'message': f'Force closed: {", ".join(killed)}'}
        return {'success': True, 'message': 'No active browsers found.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _task_manager():
    """Open Windows Task Manager"""
    try:
        subprocess.Popen(['taskmgr.exe'])
        return {'success': True, 'message': 'Task Manager opened.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

PROCESS_UTILITIES = [
    {'id': 'kill_cpu', 'name': 'Kill Top CPU Hog', 'desc': 'Force close highest CPU app', 'category': 'processes', 'icon': '🎯', 'color': '#ef4444', 'run': _kill_top_cpu},
    {'id': 'mem_hogs', 'name': 'Memory Hogs', 'desc': 'List top RAM consumers', 'category': 'processes', 'icon': '🧠', 'color': '#a855f7', 'run': _list_memory_hogs},
    {'id': 'cpu_hogs', 'name': 'CPU Hogs', 'desc': 'List top CPU consumers', 'category': 'processes', 'icon': '🔥', 'color': '#f97316', 'run': _list_cpu_hogs},
    {'id': 'kill_zombies', 'name': 'Kill Zombies', 'desc': 'Kill unresponsive programs', 'category': 'processes', 'icon': '🧟', 'color': '#ef4444', 'run': _kill_zombie_processes},
    {'id': 'kill_browsers', 'name': 'Kill All Browsers', 'desc': 'Force close all browsers', 'category': 'processes', 'icon': '🌐', 'color': '#3b82f6', 'run': _kill_all_browsers},
    {'id': 'taskmgr', 'name': 'Task Manager', 'desc': 'Open Windows Task Manager', 'category': 'processes', 'icon': '📋', 'color': '#22c55e', 'run': _task_manager},
]
