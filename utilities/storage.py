"""
Storage Utilities — Disk health, space analysis, and data tools
"""

import subprocess
import os
import shutil


def _disk_health_smart():
    """Check S.M.A.R.T. status via wmic"""
    try:
        result = subprocess.run(
            ['wmic', 'diskdrive', 'get', 'Model,Status,Size,MediaType'],
            capture_output=True, text=True, timeout=15, creationflags=0x08000000
        )
        return {'success': True, 'message': f'Disk Health (S.M.A.R.T.):\n{result.stdout.strip()}'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _partition_info():
    """Show disk partition info"""
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-Partition | Select-Object DiskNumber, PartitionNumber, DriveLetter, Size, Type | Format-Table -AutoSize | Out-String -Width 200'],
            capture_output=True, text=True, timeout=15, creationflags=0x08000000
        )
        return {'success': True, 'message': f'Disk Partitions:\n{result.stdout.strip()[:1200]}'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _large_files_finder():
    """Find largest files on C: drive"""
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-ChildItem -Path C:\\ -Recurse -ErrorAction SilentlyContinue -File | '
             'Sort-Object Length -Descending | '
             'Select-Object -First 20 @{N="SizeMB";E={[math]::Round($_.Length/1MB,1)}}, FullName | '
             'Format-Table -AutoSize | Out-String -Width 200'],
            capture_output=True, text=True, timeout=60, creationflags=0x08000000
        )
        if result.stdout.strip():
            return {'success': True, 'message': f'Top 20 Largest Files on C:\n{result.stdout.strip()[:1500]}'}
        return {'success': True, 'message': 'Scan complete — no large files found or access denied.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _folder_size_analysis():
    """Show space usage of major C: folders"""
    try:
        folders = ['Windows', 'Program Files', 'Program Files (x86)', 'Users']
        msg = "Folder Size Analysis (C:\\):\n" + "-" * 40 + "\n"
        for folder in folders:
            path = os.path.join('C:\\', folder)
            if os.path.exists(path):
                try:
                    total = sum(
                        os.path.getsize(os.path.join(dp, f))
                        for dp, dn, fn in os.walk(path)
                        for f in fn
                        if os.path.exists(os.path.join(dp, f))
                    )
                    gb = total / (1024**3)
                    msg += f"  {folder}: {gb:.2f} GB\n"
                except Exception:
                    msg += f"  {folder}: Access denied\n"

        # Free space
        usage = shutil.disk_usage('C:\\')
        msg += f"\n  Free: {usage.free / (1024**3):.2f} GB / {usage.total / (1024**3):.2f} GB Total"
        return {'success': True, 'message': msg}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _trim_ssd():
    """Run TRIM optimization on SSD drives"""
    try:
        subprocess.Popen(
            ['powershell', '-Command',
             'Start-Process cmd -ArgumentList \'/k defrag C: /L /O & echo TRIM optimization complete!\' -Verb RunAs'],
            creationflags=0x08000000
        )
        return {'success': True, 'message': 'SSD TRIM/Optimize started in Admin window.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _check_disk_errors():
    """Quick disk error check"""
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-Volume | Select-Object DriveLetter, FileSystemLabel, FileSystemType, '
             'HealthStatus, SizeRemaining, Size | Format-Table -AutoSize | Out-String -Width 200'],
            capture_output=True, text=True, timeout=15, creationflags=0x08000000
        )
        return {'success': True, 'message': f'Volume Health:\n{result.stdout.strip()}'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


STORAGE_UTILITIES = [
    {'id': 'smart', 'name': 'Disk Health (SMART)', 'desc': 'Check drive SMART status', 'category': 'storage', 'icon': '🏥', 'color': '#22c55e', 'run': _disk_health_smart},
    {'id': 'partitions', 'name': 'Partition Info', 'desc': 'List all disk partitions', 'category': 'storage', 'icon': '📊', 'color': '#3b82f6', 'run': _partition_info},
    {'id': 'large_files', 'name': 'Large File Finder', 'desc': 'Top 20 biggest files on C:', 'category': 'storage', 'icon': '📁', 'color': '#f97316', 'run': _large_files_finder},
    {'id': 'folder_sizes', 'name': 'Folder Size Analysis', 'desc': 'Space usage of major folders', 'category': 'storage', 'icon': '📈', 'color': '#a855f7', 'run': _folder_size_analysis},
    {'id': 'trim', 'name': 'SSD TRIM Optimize', 'desc': 'Run TRIM on SSD drives', 'category': 'storage', 'icon': '⚡', 'color': '#06b6d4', 'run': _trim_ssd},
    {'id': 'vol_health', 'name': 'Volume Health Check', 'desc': 'Check all volumes status', 'category': 'storage', 'icon': '💚', 'color': '#22c55e', 'run': _check_disk_errors},
]
