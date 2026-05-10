"""
Accessibility & Ease-of-Use Utilities
"""

import subprocess


def _enable_high_contrast():
    """Toggle Windows high contrast mode"""
    try:
        subprocess.Popen(
            ['powershell', '-Command',
             'Start-Process ms-settings:easeofaccess-highcontrast'],
            creationflags=0x08000000
        )
        return {'success': True, 'message': 'Opened High Contrast settings. Toggle it from there.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _cursor_size():
    """Open mouse pointer size settings"""
    try:
        subprocess.Popen(
            ['powershell', '-Command',
             'Start-Process ms-settings:easeofaccess-mousepointer'],
            creationflags=0x08000000
        )
        return {'success': True, 'message': 'Opened Mouse Pointer settings.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _text_scaling():
    """Open display text scaling settings"""
    try:
        subprocess.Popen(
            ['powershell', '-Command',
             'Start-Process ms-settings:easeofaccess-display'],
            creationflags=0x08000000
        )
        return {'success': True, 'message': 'Opened Display/Text Size settings.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _narrator_toggle():
    """Open Narrator settings"""
    try:
        subprocess.Popen(
            ['powershell', '-Command',
             'Start-Process ms-settings:easeofaccess-narrator'],
            creationflags=0x08000000
        )
        return {'success': True, 'message': 'Opened Narrator settings.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _night_light():
    """Toggle night light / blue light filter"""
    try:
        subprocess.Popen(
            ['powershell', '-Command',
             'Start-Process ms-settings:nightlight'],
            creationflags=0x08000000
        )
        return {'success': True, 'message': 'Opened Night Light settings.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _magnifier():
    """Launch Windows Magnifier"""
    try:
        subprocess.Popen(['magnify.exe'])
        return {'success': True, 'message': 'Windows Magnifier launched. Press Win+Esc to close.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


ACCESSIBILITY_UTILITIES = [
    {'id': 'contrast', 'name': 'High Contrast', 'desc': 'Toggle high contrast mode', 'category': 'accessibility', 'icon': '🌓', 'color': '#eab308', 'run': _enable_high_contrast},
    {'id': 'cursor', 'name': 'Cursor Size', 'desc': 'Adjust pointer size/style', 'category': 'accessibility', 'icon': '🖱️', 'color': '#3b82f6', 'run': _cursor_size},
    {'id': 'text_scale', 'name': 'Text Scaling', 'desc': 'Adjust display text size', 'category': 'accessibility', 'icon': '🔤', 'color': '#22c55e', 'run': _text_scaling},
    {'id': 'narrator', 'name': 'Narrator', 'desc': 'Open Narrator settings', 'category': 'accessibility', 'icon': '🗣️', 'color': '#a855f7', 'run': _narrator_toggle},
    {'id': 'night', 'name': 'Night Light', 'desc': 'Blue light filter settings', 'category': 'accessibility', 'icon': '🌙', 'color': '#f97316', 'run': _night_light},
    {'id': 'magnify', 'name': 'Magnifier', 'desc': 'Launch screen magnifier', 'category': 'accessibility', 'icon': '🔍', 'color': '#06b6d4', 'run': _magnifier},
]
