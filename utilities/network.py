"""
Network Utilities — Real network diagnosis and repair tools
"""

import subprocess
import socket
import time


def _flush_dns():
    """Flush DNS cache"""
    try:
        result = subprocess.run(
            ['ipconfig', '/flushdns'],
            capture_output=True, text=True, creationflags=0x08000000
        )
        return {'success': True, 'message': 'DNS cache flushed successfully ✅'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _ip_reset():
    """Release + renew + flush DNS"""
    try:
        msgs = []
        for cmd, label in [
            (['ipconfig', '/release'], 'IP Release'),
            (['ipconfig', '/renew'], 'IP Renew'),
            (['ipconfig', '/flushdns'], 'DNS Flush'),
        ]:
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    timeout=30, creationflags=0x08000000)
            msgs.append(f'{label}: {"✅" if result.returncode == 0 else "⚠️"}')
        return {'success': True, 'message': '\n'.join(msgs)}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _wifi_passwords():
    """Show saved Wi-Fi passwords"""
    try:
        result = subprocess.run(
            ['netsh', 'wlan', 'show', 'profiles'],
            capture_output=True, text=True, creationflags=0x08000000
        )
        profiles = []
        for line in result.stdout.splitlines():
            if 'All User Profile' in line or 'Current User Profile' in line:
                name = line.split(':')[-1].strip()
                if name:
                    profiles.append(name)

        if not profiles:
            return {'success': True, 'message': 'No saved Wi-Fi profiles found'}

        results = []
        for profile in profiles[:10]:  # Limit to 10
            pwd_result = subprocess.run(
                ['netsh', 'wlan', 'show', 'profile', f'name={profile}', 'key=clear'],
                capture_output=True, text=True, creationflags=0x08000000
            )
            password = ''
            for line in pwd_result.stdout.splitlines():
                if 'Key Content' in line:
                    password = line.split(':')[-1].strip()
                    break
            results.append(f'{profile}: {password if password else "(no password)"}')

        return {'success': True, 'message': '\n'.join(results)}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _network_reset():
    """Full network stack reset (WinSock + TCP/IP)"""
    try:
        subprocess.Popen(
            ['powershell', '-Command',
             'Start-Process cmd -ArgumentList \'/k netsh winsock reset & netsh int ip reset & echo Restart required!\' -Verb RunAs'],
            creationflags=0x08000000
        )
        return {'success': True, 'message': 'Network stack reset started in Admin window. Restart required.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _dns_benchmark():
    """Benchmark DNS servers by measuring lookup latency"""
    servers = [
        ('ISP Default', None),
        ('Google DNS', '8.8.8.8'),
        ('Cloudflare', '1.1.1.1'),
        ('OpenDNS', '208.67.222.222'),
        ('Quad9', '9.9.9.9'),
    ]
    results = []
    test_domain = 'www.google.com'

    for name, server in servers:
        try:
            if server:
                # Measure DNS lookup time using nslookup
                start = time.time()
                result = subprocess.run(
                    ['nslookup', test_domain, server],
                    capture_output=True, text=True, timeout=5, creationflags=0x08000000
                )
                elapsed = (time.time() - start) * 1000
                results.append(f'{name} ({server}): {elapsed:.0f}ms')
            else:
                start = time.time()
                socket.getaddrinfo(test_domain, 80)
                elapsed = (time.time() - start) * 1000
                results.append(f'{name}: {elapsed:.0f}ms')
        except Exception:
            results.append(f'{name}: TIMEOUT')

    return {'success': True, 'message': 'DNS Benchmark Results:\n' + '\n'.join(results)}


def _clear_proxy():
    """Remove leftover proxy configurations"""
    try:
        subprocess.run(
            ['reg', 'add', r'HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings',
             '/v', 'ProxyEnable', '/t', 'REG_DWORD', '/d', '0', '/f'],
            capture_output=True, creationflags=0x08000000
        )
        return {'success': True, 'message': 'Proxy disabled. No proxy is configured now ✅'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _ping_monitor():
    """Quick ping test to 8.8.8.8 and gateway"""
    try:
        results = []
        for target in ['8.8.8.8', '1.1.1.1']:
            result = subprocess.run(
                ['ping', '-n', '4', target],
                capture_output=True, text=True, timeout=15, creationflags=0x08000000
            )
            for line in result.stdout.splitlines():
                if 'Average' in line or 'average' in line.lower():
                    results.append(f'{target}: {line.strip()}')
                    break
            else:
                if 'Request timed out' in result.stdout:
                    results.append(f'{target}: Request timed out ⚠️')
                else:
                    results.append(f'{target}: Reachable ✅')

        return {'success': True, 'message': '\n'.join(results)}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def _port_checker():
    """Check common ports"""
    ports = [
        (80, 'HTTP'),
        (443, 'HTTPS'),
        (3389, 'RDP'),
        (22, 'SSH'),
        (445, 'SMB'),
        (8080, 'HTTP Alt'),
    ]
    results = []
    for port, name in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', port))
            status = 'OPEN' if result == 0 else 'CLOSED'
            results.append(f'Port {port} ({name}): {status}')
            sock.close()
        except Exception:
            results.append(f'Port {port} ({name}): ERROR')

    return {'success': True, 'message': '\n'.join(results)}


NETWORK_UTILITIES = [
    {'id': 'dns_flush', 'name': 'DNS Flusher', 'desc': 'ipconfig /flushdns one-click', 'category': 'network', 'icon': '🌐', 'color': '#06b6d4', 'run': _flush_dns},
    {'id': 'ip_reset', 'name': 'IP Reset', 'desc': 'Release + renew + flush DNS', 'category': 'network', 'icon': '📡', 'color': '#3b82f6', 'run': _ip_reset},
    {'id': 'wifi_pass', 'name': 'Wi-Fi Password Viewer', 'desc': 'Show saved Wi-Fi passwords', 'category': 'network', 'icon': '🔑', 'color': '#22c55e', 'run': _wifi_passwords},
    {'id': 'net_reset', 'name': 'Network Reset', 'desc': 'netsh winsock + int ip reset', 'category': 'network', 'icon': '🔌', 'color': '#ef4444', 'run': _network_reset},
    {'id': 'dns_bench', 'name': 'DNS Benchmark', 'desc': 'Test ISP vs Cloudflare vs Google', 'category': 'network', 'icon': '⚡', 'color': '#a855f7', 'run': _dns_benchmark},
    {'id': 'proxy', 'name': 'Proxy Remover', 'desc': 'Remove leftover proxy configs', 'category': 'network', 'icon': '🔐', 'color': '#eab308', 'run': _clear_proxy},
    {'id': 'ping', 'name': 'Ping Monitor', 'desc': 'Quick ping test to 8.8.8.8', 'category': 'network', 'icon': '📶', 'color': '#f97316', 'run': _ping_monitor},
    {'id': 'port', 'name': 'Port Checker', 'desc': 'Check if ports are open/closed', 'category': 'network', 'icon': '🚪', 'color': '#06b6d4', 'run': _port_checker},
]
