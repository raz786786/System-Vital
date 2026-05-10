"""
Utilities Module — Registry of all one-click tools
Each utility is a dict with id, name, desc, category, icon, color, and run function.
"""

from utilities.cleaner import CLEANER_UTILITIES
from utilities.repair import REPAIR_UTILITIES
from utilities.network import NETWORK_UTILITIES
from utilities.security import SECURITY_UTILITIES
from utilities.performance import PERFORMANCE_UTILITIES
from utilities.sysinfo import SYSINFO_UTILITIES
from utilities.drivers import DRIVER_UTILITIES
from utilities.power import POWER_UTILITIES
from utilities.windows import WINDOWS_UTILITIES
from utilities.storage import STORAGE_UTILITIES
from utilities.accessibility import ACCESSIBILITY_UTILITIES
from utilities.processes import PROCESS_UTILITIES
from utilities.services import SERVICES_UTILITIES
from utilities.customization import CUSTOMIZATION_UTILITIES
from utilities.gaming import GAMING_UTILITIES
from utilities.deep_maintenance import DEEP_MAINTENANCE_UTILITIES
from utilities.browser_opt import BROWSER_OPT_UTILITIES
from utilities.advanced_hardware import ADV_HARDWARE_UTILITIES
from utilities.privacy_deep import PRIVACY_DEEP_UTILITIES
from utilities.context_menu import CONTEXT_MENU_UTILITIES
from utilities.advanced_tweaks import ADVANCED_TWEAKS_UTILITIES

ALL_UTILITIES = (
    CLEANER_UTILITIES +
    REPAIR_UTILITIES +
    NETWORK_UTILITIES +
    SECURITY_UTILITIES +
    PERFORMANCE_UTILITIES +
    SYSINFO_UTILITIES +
    DRIVER_UTILITIES +
    POWER_UTILITIES +
    WINDOWS_UTILITIES +
    STORAGE_UTILITIES +
    ACCESSIBILITY_UTILITIES +
    PROCESS_UTILITIES +
    SERVICES_UTILITIES +
    CUSTOMIZATION_UTILITIES +
    GAMING_UTILITIES +
    DEEP_MAINTENANCE_UTILITIES +
    BROWSER_OPT_UTILITIES +
    ADV_HARDWARE_UTILITIES +
    PRIVACY_DEEP_UTILITIES +
    CONTEXT_MENU_UTILITIES +
    ADVANCED_TWEAKS_UTILITIES
)

CATEGORY_MAP = {
    'all': 'All Utilities',
    'cleaner': '🧹 Cleaner',
    'repair': '🔧 Repair',
    'network': '🌐 Network',
    'security': '🔒 Security',
    'performance': '⚡ Performance',
    'sysinfo': '🖥️ System Info',
    'drivers': '🔌 Drivers',
    'power': '🔋 Power',
    'windows': '🪟 Windows',
    'storage': '💾 Storage',
    'accessibility': '♿ Accessibility',
    'processes': '🔄 Processes',
    'services': '⚙️ Services',
    'customization': '🎨 Customization',
    'gaming': '🎮 Gaming',
    'deep_maintenance': '🛠️ Deep Maintenance',
    'browser_opt': '🌎 Browser Opt',
    'advanced_hardware': '💻 Adv. Hardware',
    'privacy_deep': '🕵️ Deep Privacy',
    'context_menu': '🖱️ Context Menu',
    'advanced_tweaks': '⚙️ Advanced Tweaks',
}

def get_utilities_by_category(category: str = 'all'):
    if category == 'all':
        return ALL_UTILITIES
    return [u for u in ALL_UTILITIES if u['category'] == category]

def get_utility_by_id(uid: str):
    for u in ALL_UTILITIES:
        if u['id'] == uid:
            return u
    return None

def run_utility(uid: str) -> dict:
    """Run a utility by ID, returns {success, message}"""
    util = get_utility_by_id(uid)
    if not util:
        return {'success': False, 'message': f'Unknown utility: {uid}'}
    try:
        return util['run']()
    except Exception as e:
        return {'success': False, 'message': str(e)}
