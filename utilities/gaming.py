"""
Gaming Utilities — Optimizations for gaming performance
"""

import subprocess

def _dxdiag_report():
    """Run DirectX Diagnostic Tool and save report"""
    try:
        import os
        report_path = os.path.join(os.environ.get('USERPROFILE', 'C:\\'), 'Desktop', 'dxdiag_report.txt')
        subprocess.Popen(['dxdiag', '/t', report_path], creationflags=0x08000000)
        return {'success': True, 'message': f'Generating dxdiag report on Desktop...'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _clear_directx_cache():
    """Clear DirectX Shader Cache via cleanmgr"""
    try:
        subprocess.run(
            ['reg', 'add', r'HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\VolumeCaches\D3D Shader Cache', '/v', 'StateFlags0001', '/t', 'REG_DWORD', '/d', '2', '/f'],
            capture_output=True, creationflags=0x08000000
        )
        subprocess.Popen(['cleanmgr', '/sagerun:1'], creationflags=0x08000000)
        return {'success': True, 'message': 'DirectX Shader Cache cleanup started.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _toggle_hags():
    """Toggle Hardware-Accelerated GPU Scheduling"""
    try:
        result = subprocess.run(
            ['reg', 'query', r'HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers', '/v', 'HwSchMode'],
            capture_output=True, text=True, creationflags=0x08000000
        )
        current = "2" in result.stdout # 2 is enabled, 1 is disabled
        new_val = "1" if current else "2"
        subprocess.run(
            ['reg', 'add', r'HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers', '/v', 'HwSchMode', '/t', 'REG_DWORD', '/d', new_val, '/f'],
            capture_output=True, creationflags=0x08000000
        )
        state = "Disabled" if current else "Enabled"
        return {'success': True, 'message': f'HAGS is now {state}. Restart PC to apply.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _game_bar_presence():
    """Toggle Game Bar Presence Writer"""
    try:
        subprocess.run(
            ['reg', 'add', r'HKLM\SOFTWARE\Microsoft\GameBar', '/v', 'AutoGameModeEnabled', '/t', 'REG_DWORD', '/d', '0', '/f'],
            capture_output=True, creationflags=0x08000000
        )
        return {'success': True, 'message': 'Game Bar presence disabled for better performance.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _fullscreen_opt_disable():
    """Disable Fullscreen Optimizations globally (via registry)"""
    try:
        subprocess.run(
            ['reg', 'add', r'HKCU\System\GameConfigStore', '/v', 'GameDVR_FSEBehaviorMode', '/t', 'REG_DWORD', '/d', '2', '/f'],
            capture_output=True, creationflags=0x08000000
        )
        return {'success': True, 'message': 'Global Fullscreen Optimizations disabled.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _xbox_services_stop():
    """Stop Xbox background services"""
    try:
        services = ['XblAuthManager', 'XblGameSave', 'XboxNetApiSvc']
        for srv in services:
            subprocess.run(['sc', 'stop', srv], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Xbox background services stopped.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

GAMING_UTILITIES = [
    {'id': 'dxdiag', 'name': 'DirectX Diag', 'desc': 'Save dxdiag to Desktop', 'category': 'gaming', 'icon': '🎮', 'color': '#3b82f6', 'run': _dxdiag_report},
    {'id': 'dx_cache', 'name': 'Clear DX Cache', 'desc': 'Clear shader cache', 'category': 'gaming', 'icon': '🧹', 'color': '#ef4444', 'run': _clear_directx_cache},
    {'id': 'hags', 'name': 'Toggle HAGS', 'desc': 'GPU scheduling toggle', 'category': 'gaming', 'icon': '⚡', 'color': '#f59e0b', 'run': _toggle_hags},
    {'id': 'gb_presence', 'name': 'Game Bar Presence', 'desc': 'Disable Game Bar tracking', 'category': 'gaming', 'icon': '🎯', 'color': '#10b981', 'run': _game_bar_presence},
    {'id': 'fso_off', 'name': 'Disable FSO', 'desc': 'Disable Fullscreen Opt.', 'category': 'gaming', 'icon': '🖥️', 'color': '#8b5cf6', 'run': _fullscreen_opt_disable},
    {'id': 'xbox_srv', 'name': 'Stop Xbox Services', 'desc': 'Stop background services', 'category': 'gaming', 'icon': '🛑', 'color': '#ef4444', 'run': _xbox_services_stop},
]
