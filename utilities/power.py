"""
Power & Battery Utilities
"""

import subprocess
import psutil
import os


def _battery_report():
    """Generate full battery health report"""
    try:
        battery = psutil.sensors_battery()
        if not battery:
            return {'success': True, 'message': 'No battery detected — this appears to be a desktop PC.'}

        # Generate Windows battery report
        report_path = os.path.join(os.path.expanduser('~'), 'Desktop', 'battery-report.html')
        subprocess.run(
            ['powercfg', '/batteryreport', f'/output', report_path],
            capture_output=True, creationflags=0x08000000
        )

        msg = f"Battery Status:\n"
        msg += f"  Charge: {battery.percent}%\n"
        msg += f"  Plugged in: {'Yes' if battery.power_plugged else 'No'}\n"
        if battery.secsleft > 0 and not battery.power_plugged:
            hours = battery.secsleft // 3600
            mins = (battery.secsleft % 3600) // 60
            msg += f"  Time remaining: {hours}h {mins}m\n"
        msg += f"\nFull report saved to Desktop:\n{report_path}"

        return {'success': True, 'message': msg}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _energy_report():
    """Run Windows energy efficiency diagnostics"""
    try:
        report_path = os.path.join(os.path.expanduser('~'), 'Desktop', 'energy-report.html')
        subprocess.Popen(
            ['powershell', '-Command',
             f'Start-Process cmd -ArgumentList \'/k powercfg /energy /output "{report_path}" & echo Report saved to Desktop\' -Verb RunAs'],
            creationflags=0x08000000
        )
        return {'success': True, 'message': f'Energy efficiency report running (60 seconds).\nReport will be saved to Desktop.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _list_power_plans():
    """List all available power plans"""
    try:
        result = subprocess.run(
            ['powercfg', '/list'],
            capture_output=True, text=True, creationflags=0x08000000
        )
        return {'success': True, 'message': f'Available Power Plans:\n{result.stdout.strip()}'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _create_ultimate_plan():
    """Create Ultimate Performance power plan"""
    try:
        subprocess.Popen(
            ['powershell', '-Command',
             'Start-Process cmd -ArgumentList \'/k powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61 & echo Ultimate Performance plan created!\' -Verb RunAs'],
            creationflags=0x08000000
        )
        return {'success': True, 'message': 'Creating Ultimate Performance power plan. Check Power Settings to activate it.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _sleep_study():
    """Generate sleep/standby study report"""
    try:
        report_path = os.path.join(os.path.expanduser('~'), 'Desktop', 'sleepstudy-report.html')
        result = subprocess.run(
            ['powercfg', '/sleepstudy', '/output', report_path],
            capture_output=True, text=True, timeout=15, creationflags=0x08000000
        )
        if result.returncode == 0:
            return {'success': True, 'message': f'Sleep study report generated:\n{report_path}'}
        return {'success': True, 'message': 'Sleep study not available on this system (may require Modern Standby).'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


POWER_UTILITIES = [
    {'id': 'battery', 'name': 'Battery Health Report', 'desc': 'Full battery report to Desktop', 'category': 'power', 'icon': '🔋', 'color': '#22c55e', 'run': _battery_report},
    {'id': 'energy', 'name': 'Energy Efficiency Report', 'desc': 'powercfg /energy diagnostics', 'category': 'power', 'icon': '⚡', 'color': '#eab308', 'run': _energy_report},
    {'id': 'plans', 'name': 'Power Plan List', 'desc': 'Show all available power plans', 'category': 'power', 'icon': '📋', 'color': '#3b82f6', 'run': _list_power_plans},
    {'id': 'ultimate', 'name': 'Ultimate Performance', 'desc': 'Create Ultimate power plan', 'category': 'power', 'icon': '🚀', 'color': '#a855f7', 'run': _create_ultimate_plan},
    {'id': 'sleep', 'name': 'Sleep Study Report', 'desc': 'Analyze standby drain patterns', 'category': 'power', 'icon': '😴', 'color': '#06b6d4', 'run': _sleep_study},
]
