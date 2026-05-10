"""
Performance Utilities — System speed optimization tools
"""

import subprocess
import winreg


def _manage_startup():
    """List all startup programs"""
    items = []
    # HKCU Run
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    items.append(f'[User] {name}: {value[:60]}...' if len(value) > 60 else f'[User] {name}: {value}')
                    i += 1
                except OSError:
                    break
    except Exception:
        pass

    # HKLM Run
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    items.append(f'[System] {name}: {value[:60]}...' if len(value) > 60 else f'[System] {name}: {value}')
                    i += 1
                except OSError:
                    break
    except Exception:
        pass

    if items:
        return {'success': True, 'message': f'{len(items)} startup entries found:\n' + '\n'.join(items)}
    return {'success': True, 'message': 'No startup entries found'}


def _switch_power_plan():
    """Toggle to High Performance power plan"""
    try:
        # Check current plan
        result = subprocess.run(
            ['powercfg', '/getactivescheme'],
            capture_output=True, text=True, creationflags=0x08000000
        )
        current = result.stdout.strip()

        if 'High Performance' in current or 'Ultimate' in current:
            # Already on high — switch to balanced
            subprocess.run(['powercfg', '/setactive', 'SCHEME_BALANCED'],
                           capture_output=True, creationflags=0x08000000)
            return {'success': True, 'message': 'Switched to Balanced power plan (was already High Performance)'}
        else:
            subprocess.run(['powercfg', '/setactive', 'SCHEME_MIN'],
                           capture_output=True, creationflags=0x08000000)
            return {'success': True, 'message': 'Switched to High Performance power plan ⚡'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _toggle_game_mode():
    """Toggle Windows Game Mode"""
    try:
        key_path = r"Software\Microsoft\GameBar"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, "AllowAutoGameMode")
                current = val
        except Exception:
            current = 1

        new_val = 0 if current == 1 else 1
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "AllowAutoGameMode", 0, winreg.REG_DWORD, new_val)

        status = "ENABLED" if new_val == 1 else "DISABLED"
        return {'success': True, 'message': f'Game Mode {status} 🎮'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _unpark_cpu():
    """Unpark all CPU cores via power plan settings"""
    try:
        # Set minimum processor state to 100% for current plan
        subprocess.run(
            ['powercfg', '-setacvalueindex', 'scheme_current', 'sub_processor',
             'PROCTHROTTLEMIN', '100'],
            capture_output=True, creationflags=0x08000000
        )
        subprocess.run(['powercfg', '-setactive', 'scheme_current'],
                       capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'CPU cores unparked — minimum processor state set to 100%'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _disable_visual_effects():
    """Disable Aero animations and transparency"""
    try:
        # Disable transparency
        subprocess.run(
            ['reg', 'add', r'HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize',
             '/v', 'EnableTransparency', '/t', 'REG_DWORD', '/d', '0', '/f'],
            capture_output=True, creationflags=0x08000000
        )
        # Set visual effects to "Best Performance"
        subprocess.run(
            ['reg', 'add', r'HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects',
             '/v', 'VisualFXSetting', '/t', 'REG_DWORD', '/d', '2', '/f'],
            capture_output=True, creationflags=0x08000000
        )
        return {'success': True, 'message': 'Visual effects set to "Best Performance". Transparency disabled. Relog to apply.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _toggle_sysmain():
    """Toggle SysMain (Superfetch) service"""
    try:
        # Check current status
        result = subprocess.run(
            ['sc', 'query', 'SysMain'],
            capture_output=True, text=True, creationflags=0x08000000
        )
        if 'RUNNING' in result.stdout:
            subprocess.Popen(
                ['powershell', '-Command', 'Start-Process cmd -ArgumentList \'/k sc stop SysMain & sc config SysMain start=disabled\' -Verb RunAs'],
                creationflags=0x08000000
            )
            return {'success': True, 'message': 'SysMain (Superfetch) being DISABLED. Run as Admin window opened.'}
        else:
            subprocess.Popen(
                ['powershell', '-Command', 'Start-Process cmd -ArgumentList \'/k sc config SysMain start=auto & sc start SysMain\' -Verb RunAs'],
                creationflags=0x08000000
            )
            return {'success': True, 'message': 'SysMain (Superfetch) being ENABLED.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _optimize_pagefile():
    """Report pagefile status and recommended size"""
    try:
        import psutil
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        ram_gb = mem.total / (1024 ** 3)
        swap_gb = swap.total / (1024 ** 3)

        recommended = ram_gb * 1.5 if ram_gb <= 8 else ram_gb

        msg = f"RAM: {ram_gb:.1f} GB\n"
        msg += f"Current Pagefile: {swap_gb:.1f} GB\n"
        msg += f"Recommended: {recommended:.1f} GB\n\n"

        if swap.total == 0:
            msg += "⚠️ No pagefile detected! This can cause crashes.\n"
            msg += "Enable via: System Properties > Advanced > Performance > Virtual Memory"
        elif swap_gb < recommended * 0.5:
            msg += "⚠️ Pagefile is too small. Consider increasing it."
        else:
            msg += "✅ Pagefile size is adequate."

        return {'success': True, 'message': msg}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _disable_game_bar():
    """Disable Game Bar and Game DVR"""
    try:
        reg_cmds = [
            (r'HKCU\Software\Microsoft\GameBar', 'UseNexusForGameBarEnabled', '0'),
            (r'HKCU\System\GameConfigStore', 'GameDVR_Enabled', '0'),
            (r'HKLM\SOFTWARE\Policies\Microsoft\Windows\GameDVR', 'AllowGameDVR', '0'),
        ]
        for key, name, value in reg_cmds:
            subprocess.run(
                ['reg', 'add', key, '/v', name, '/t', 'REG_DWORD', '/d', value, '/f'],
                capture_output=True, creationflags=0x08000000
            )
        return {'success': True, 'message': 'Game Bar and Game DVR disabled 🎯'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _apply_gaming_profile():
    """Apply a bundle of performance optimizations for gaming"""
    try:
        _switch_power_plan()
        _toggle_game_mode()
        _unpark_cpu()
        _disable_game_bar()
        _disable_visual_effects()
        return {'success': True, 'message': 'Gaming Optimization Profile Applied! 🎮 (Restart recommended)'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _enable_ultimate_power():
    """Unlock the 'Ultimate Performance' power plan (Hidden by default)"""
    try:
        subprocess.run(['powercfg', '-duplicatescheme', 'e9a42b02-d5df-448d-aa00-03f14749eb61'], capture_output=True, creationflags=0x08000000)
        return {'success': True, 'message': 'Ultimate Performance plan UNLOCKED. You can now select it in Windows Power Options.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


PERFORMANCE_UTILITIES = [
    {'id': 'startup', 'name': 'Startup Manager', 'desc': 'List startup programs', 'category': 'performance', 'icon': '🚀', 'color': '#3b82f6', 'run': _manage_startup},
    {'id': 'power', 'name': 'Power Plan Switcher', 'desc': 'Toggle High Performance mode', 'category': 'performance', 'icon': '⚡', 'color': '#eab308', 'run': _switch_power_plan},
    {'id': 'game_mode', 'name': 'Game Mode Toggle', 'desc': 'Enable/disable Windows Game Mode', 'category': 'performance', 'icon': '🎮', 'color': '#22c55e', 'run': _toggle_game_mode},
    {'id': 'unpark', 'name': 'CPU Unparker', 'desc': 'Unpark all CPU cores', 'category': 'performance', 'icon': '🔓', 'color': '#f97316', 'run': _unpark_cpu},
    {'id': 'visual_fx', 'name': 'Visual Effects Off', 'desc': 'Disable Aero animations', 'category': 'performance', 'icon': '✨', 'color': '#a855f7', 'run': _disable_visual_effects},
    {'id': 'sysmain', 'name': 'SysMain Toggle', 'desc': 'Enable/disable Superfetch', 'category': 'performance', 'icon': '🔄', 'color': '#ef4444', 'run': _toggle_sysmain},
    {'id': 'pagefile', 'name': 'Pagefile Optimizer', 'desc': 'Check pagefile status & size', 'category': 'performance', 'icon': '📊', 'color': '#06b6d4', 'run': _optimize_pagefile},
    {'id': 'gamebar', 'name': 'Game Bar Disabler', 'desc': 'Disable Game Bar + DVR', 'category': 'performance', 'icon': '🎯', 'color': '#ef4444', 'run': _disable_game_bar},
    {'id': 'gaming_profile', 'name': 'Ultimate Gaming Boost', 'desc': 'Apply ALL gaming optimizations at once', 'category': 'performance', 'icon': '💎', 'color': '#00B894', 'run': _apply_gaming_profile},
    {'id': 'ultimate_power', 'name': 'Ultimate Power Plan', 'desc': 'Unlock hidden high-perf power plan', 'category': 'performance', 'icon': '⚡', 'color': '#FFD700', 'run': _enable_ultimate_power},
]
