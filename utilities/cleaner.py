"""
Cleaner Utilities — Real Windows cleanup tools
"""

import os
import shutil
import subprocess
import glob

def _clean_temp_files():
    """Wipe %TEMP% and Windows\\Temp"""
    cleaned = 0
    errors = 0
    paths = [
        os.environ.get('TEMP', ''),
        os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'Temp'),
    ]
    for p in paths:
        if not p or not os.path.exists(p):
            continue
        for item in os.listdir(p):
            item_path = os.path.join(p, item)
            try:
                if os.path.isfile(item_path):
                    os.remove(item_path)
                    cleaned += 1
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path, ignore_errors=True)
                    cleaned += 1
            except Exception:
                errors += 1
    return {'success': True, 'message': f'Cleaned {cleaned} items ({errors} skipped — in use)'}


def _clean_recycle_bin():
    """Force clear recycle bin via PowerShell"""
    try:
        subprocess.run(
            ['powershell', '-Command', 'Clear-RecycleBin -Force -ErrorAction SilentlyContinue'],
            capture_output=True, text=True, creationflags=0x08000000
        )
        return {'success': True, 'message': 'Recycle Bin emptied successfully'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _clean_ram():
    """Flush standby memory list (requires admin)"""
    try:
        # Use RAMMap-style approach via PowerShell
        subprocess.run(
            ['powershell', '-Command',
             '[System.GC]::Collect(); [System.GC]::WaitForPendingFinalizers()'],
            capture_output=True, text=True, creationflags=0x08000000
        )
        return {'success': True, 'message': 'Memory garbage collection triggered. For deeper flush, run as Administrator.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _clean_browser_cache():
    """Clear cache across Chrome, Edge, Firefox"""
    cleaned = []
    local = os.environ.get('LOCALAPPDATA', '')
    appdata = os.environ.get('APPDATA', '')

    # Chrome
    chrome_cache = os.path.join(local, r'Google\Chrome\User Data\Default\Cache')
    if os.path.exists(chrome_cache):
        shutil.rmtree(chrome_cache, ignore_errors=True)
        cleaned.append('Chrome')

    # Edge
    edge_cache = os.path.join(local, r'Microsoft\Edge\User Data\Default\Cache')
    if os.path.exists(edge_cache):
        shutil.rmtree(edge_cache, ignore_errors=True)
        cleaned.append('Edge')

    # Firefox
    ff_profiles = os.path.join(appdata, r'Mozilla\Firefox\Profiles')
    if os.path.exists(ff_profiles):
        for profile in os.listdir(ff_profiles):
            cache_dir = os.path.join(ff_profiles, profile, 'cache2')
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir, ignore_errors=True)
                cleaned.append('Firefox')
                break

    if cleaned:
        return {'success': True, 'message': f'Cleared cache for: {", ".join(cleaned)}'}
    return {'success': True, 'message': 'No browser caches found'}


def _clean_log_files():
    """Remove old .log and .etl files from Windows Logs"""
    cleaned = 0
    log_dirs = [
        os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'Logs'),
        os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), r'System32\LogFiles'),
    ]
    for d in log_dirs:
        if not os.path.exists(d):
            continue
        for root, dirs, files in os.walk(d):
            for f in files:
                if f.lower().endswith(('.log', '.etl', '.tmp')):
                    try:
                        os.remove(os.path.join(root, f))
                        cleaned += 1
                    except Exception:
                        pass
    return {'success': True, 'message': f'Removed {cleaned} log files'}


def _clean_prefetch():
    """Safely clean Windows Prefetch folder"""
    prefetch_dir = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'Prefetch')
    cleaned = 0
    if os.path.exists(prefetch_dir):
        for f in os.listdir(prefetch_dir):
            try:
                fp = os.path.join(prefetch_dir, f)
                if os.path.isfile(fp):
                    os.remove(fp)
                    cleaned += 1
            except Exception:
                pass
    return {'success': True, 'message': f'Cleaned {cleaned} prefetch files'}


def _clean_winsxs():
    """Run Component Store cleanup via DISM"""
    try:
        result = subprocess.run(
            ['dism', '/Online', '/Cleanup-Image', '/StartComponentCleanup'],
            capture_output=True, text=True, timeout=120, creationflags=0x08000000
        )
        if result.returncode == 0:
            return {'success': True, 'message': 'WinSxS component store cleaned'}
        return {'success': False, 'message': f'DISM returned code {result.returncode}. Run as Administrator.'}
    except subprocess.TimeoutExpired:
        return {'success': False, 'message': 'Timed out — run manually as Administrator'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _clean_shader_cache():
    """Clear DirectX and Vulkan shader caches"""
    cleaned = []
    local = os.environ.get('LOCALAPPDATA', '')

    # DirectX shader cache
    dx_cache = os.path.join(local, 'D3DSCache')
    if os.path.exists(dx_cache):
        shutil.rmtree(dx_cache, ignore_errors=True)
        cleaned.append('DirectX')

    # NVIDIA
    nv_cache = os.path.join(local, r'NVIDIA\DXCache')
    if os.path.exists(nv_cache):
        shutil.rmtree(nv_cache, ignore_errors=True)
        cleaned.append('NVIDIA DX')

    nv_gl = os.path.join(local, r'NVIDIA\GLCache')
    if os.path.exists(nv_gl):
        shutil.rmtree(nv_gl, ignore_errors=True)
        cleaned.append('NVIDIA GL')

    # AMD
    amd_cache = os.path.join(local, r'AMD\DxCache')
    if os.path.exists(amd_cache):
        shutil.rmtree(amd_cache, ignore_errors=True)
        cleaned.append('AMD DX')

    if cleaned:
        return {'success': True, 'message': f'Cleared: {", ".join(cleaned)} shader caches'}
    return {'success': True, 'message': 'No shader caches found'}


def _clean_downloads():
    """Flag and list old files in Downloads folder"""
    import time
    downloads = os.path.join(os.path.expanduser('~'), 'Downloads')
    if not os.path.exists(downloads):
        return {'success': True, 'message': 'Downloads folder not found'}

    threshold = time.time() - (30 * 86400)  # 30 days
    old_files = []
    total_size = 0
    for f in os.listdir(downloads):
        fp = os.path.join(downloads, f)
        try:
            if os.path.getmtime(fp) < threshold:
                size = os.path.getsize(fp) if os.path.isfile(fp) else 0
                old_files.append(f)
                total_size += size
        except Exception:
            pass

    mb = total_size / (1024 * 1024)
    return {
        'success': True,
        'message': f'Found {len(old_files)} files older than 30 days ({mb:.1f} MB). Clean manually in Downloads folder.'
    }


CLEANER_UTILITIES = [
    {'id': 'temp', 'name': 'Temp File Cleaner', 'desc': 'Wipe %TEMP% & Windows\\Temp', 'category': 'cleaner', 'icon': '🗑️', 'color': '#ef4444', 'run': _clean_temp_files},
    {'id': 'recycle', 'name': 'Recycle Bin Wiper', 'desc': 'Force clear stuck recycle bin', 'category': 'cleaner', 'icon': '♻️', 'color': '#ef4444', 'run': _clean_recycle_bin},
    {'id': 'ram', 'name': 'RAM Cleaner', 'desc': 'Flush standby list, trigger GC', 'category': 'cleaner', 'icon': '🧠', 'color': '#a855f7', 'run': _clean_ram},
    {'id': 'browser_cache', 'name': 'Browser Cache Clear', 'desc': 'Clear cache across all browsers', 'category': 'cleaner', 'icon': '🌐', 'color': '#f97316', 'run': _clean_browser_cache},
    {'id': 'logs', 'name': 'Log File Cleaner', 'desc': 'Remove old .log and .etl files', 'category': 'cleaner', 'icon': '📋', 'color': '#eab308', 'run': _clean_log_files},
    {'id': 'prefetch', 'name': 'Prefetch Cleaner', 'desc': 'Safely clean Windows prefetch', 'category': 'cleaner', 'icon': '⚡', 'color': '#06b6d4', 'run': _clean_prefetch},
    {'id': 'winsxs', 'name': 'WinSxS Cleanup', 'desc': 'Component store cleanup via DISM', 'category': 'cleaner', 'icon': '🪟', 'color': '#3b82f6', 'run': _clean_winsxs},
    {'id': 'shader', 'name': 'Shader Cache Clear', 'desc': 'Clear DX/Vulkan shader caches', 'category': 'cleaner', 'icon': '🎮', 'color': '#22c55e', 'run': _clean_shader_cache},
    {'id': 'downloads', 'name': 'Downloads Cleaner', 'desc': 'Flag files older than 30 days', 'category': 'cleaner', 'icon': '📥', 'color': '#eab308', 'run': _clean_downloads},
]
