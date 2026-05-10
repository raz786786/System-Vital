import { useState } from 'react';
import { RefreshCw, Play, CheckCircle } from 'lucide-react';

interface UtilityItem {
  id: string;
  name: string;
  desc: string;
  category: string;
  color: string;
  icon: string;
}

const utilities: UtilityItem[] = [
  // Cleaner
  { id: 'temp', name: 'Temp File Cleaner', desc: 'Wipe %TEMP% & Windows\\Temp', category: 'cleaner', color: 'var(--red)', icon: '🗑️' },
  { id: 'recycle', name: 'Recycle Bin Wiper', desc: 'Force clear stuck recycle bin', category: 'cleaner', color: 'var(--red)', icon: '♻️' },
  { id: 'ram', name: 'RAM Cleaner', desc: 'Flush standby list, kill zombies', category: 'cleaner', color: 'var(--purple)', icon: '🧠' },
  { id: 'browser_cache', name: 'Browser Cache Clear', desc: 'Clear cache across all browsers', category: 'cleaner', color: 'var(--orange)', icon: '🌐' },
  { id: 'logs', name: 'Log File Cleaner', desc: 'Remove old .log and .etl files', category: 'cleaner', color: 'var(--yellow)', icon: '📋' },
  { id: 'prefetch', name: 'Prefetch Cleaner', desc: 'Safely clean Windows prefetch', category: 'cleaner', color: 'var(--cyan)', icon: '⚡' },
  { id: 'winsxs', name: 'WinSxS Cleanup', desc: 'Component store cleanup via DISM', category: 'cleaner', color: 'var(--accent)', icon: '🪟' },
  { id: 'shader', name: 'Shader Cache Clear', desc: 'Clear DX/Vulkan shader caches', category: 'cleaner', color: 'var(--green)', icon: '🎮' },
  { id: 'downloads', name: 'Downloads Cleaner', desc: 'Flag files older than X days', category: 'cleaner', color: 'var(--yellow)', icon: '📥' },
  // Repair
  { id: 'sfc', name: 'SFC Scanner', desc: 'sfc /scannow with result parser', category: 'repair', color: 'var(--green)', icon: '🛡️' },
  { id: 'dism', name: 'DISM Repair', desc: 'RestoreHealth Windows image', category: 'repair', color: 'var(--accent)', icon: '🔧' },
  { id: 'reg_clean', name: 'Registry Cleaner', desc: 'Scan for invalid/orphaned keys', category: 'repair', color: 'var(--purple)', icon: '📝' },
  { id: 'chkdsk', name: 'CHKDSK Runner', desc: 'Schedule disk error check', category: 'repair', color: 'var(--orange)', icon: '💾' },
  { id: 'bsod', name: 'BSOD Dump Reader', desc: 'Decode minidump .dmp files', category: 'repair', color: 'var(--red)', icon: '💀' },
  { id: 'dll', name: 'DLL Error Scanner', desc: 'Detect missing DLLs from Event Log', category: 'repair', color: 'var(--yellow)', icon: '📦' },
  { id: 'explorer_fix', name: 'Explorer Restarter', desc: 'Kill + restart explorer.exe', category: 'repair', color: 'var(--cyan)', icon: '🗂️' },
  { id: 'hosts', name: 'Hosts File Checker', desc: 'Compare against default hosts', category: 'repair', color: 'var(--green)', icon: '🏠' },
  { id: 'update_repair', name: 'Update Repair', desc: 'Stop/clear/restart WU services', category: 'repair', color: 'var(--accent)', icon: '🔄' },
  // Network
  { id: 'dns_flush', name: 'DNS Flusher', desc: 'ipconfig /flushdns one-click', category: 'network', color: 'var(--cyan)', icon: '🌐' },
  { id: 'ip_reset', name: 'IP Reset', desc: 'Release + renew + flush DNS', category: 'network', color: 'var(--accent)', icon: '📡' },
  { id: 'wifi_pass', name: 'Wi-Fi Password Viewer', desc: 'Show saved Wi-Fi passwords', category: 'network', color: 'var(--green)', icon: '🔑' },
  { id: 'net_reset', name: 'Network Reset', desc: 'netsh winsock + int ip reset', category: 'network', color: 'var(--red)', icon: '🔌' },
  { id: 'dns_bench', name: 'DNS Benchmark', desc: 'Test ISP vs Cloudflare vs Google', category: 'network', color: 'var(--purple)', icon: '⚡' },
  { id: 'proxy', name: 'Proxy Remover', desc: 'Remove leftover proxy configs', category: 'network', color: 'var(--yellow)', icon: '🔐' },
  { id: 'ping', name: 'Ping Monitor', desc: 'Real-time ping graph to gateway', category: 'network', color: 'var(--orange)', icon: '📶' },
  { id: 'port', name: 'Port Checker', desc: 'Check if ports are open/closed', category: 'network', color: 'var(--cyan)', icon: '🚪' },
  // Security
  { id: 'telemetry', name: 'Telemetry Disabler', desc: 'Block known telemetry tasks', category: 'security', color: 'var(--red)', icon: '📵' },
  { id: 'bloat', name: 'Bloatware Remover', desc: 'Remove known OEM bloatware', category: 'security', color: 'var(--orange)', icon: '🗑️' },
  { id: 'privacy', name: 'Privacy Hardener', desc: 'Disable telemetry, ad ID, Cortana', category: 'security', color: 'var(--purple)', icon: '🔒' },
  { id: 'perm_audit', name: 'Permission Auditor', desc: 'List apps with camera/mic/GPS', category: 'security', color: 'var(--yellow)', icon: '👁️' },
  { id: 'firewall', name: 'Firewall Checker', desc: 'Check + re-enable all profiles', category: 'security', color: 'var(--accent)', icon: '🛡️' },
  { id: 'defender', name: 'Defender Re-enabler', desc: 'Re-enable via registry + service', category: 'security', color: 'var(--green)', icon: '🦺' },
  { id: 'autorun', name: 'Autorun Disabler', desc: 'Disable USB autoplay via registry', category: 'security', color: 'var(--red)', icon: '🚫' },
  { id: 'smartscreen', name: 'SmartScreen Fixer', desc: 'Restore SmartScreen via GPO', category: 'security', color: 'var(--cyan)', icon: '🔍' },
  // Performance
  { id: 'startup', name: 'Startup Manager', desc: 'List, enable/disable startup items', category: 'performance', color: 'var(--accent)', icon: '🚀' },
  { id: 'power', name: 'Power Plan Switcher', desc: 'Toggle Balanced/High Performance', category: 'performance', color: 'var(--yellow)', icon: '⚡' },
  { id: 'game_mode', name: 'Game Mode Toggle', desc: 'Enable/disable Windows Game Mode', category: 'performance', color: 'var(--green)', icon: '🎮' },
  { id: 'unpark', name: 'CPU Unparker', desc: 'Unpark all CPU cores via registry', category: 'performance', color: 'var(--orange)', icon: '🔓' },
  { id: 'visual_fx', name: 'Visual Effects Off', desc: 'Disable Aero animations', category: 'performance', color: 'var(--purple)', icon: '✨' },
  { id: 'sysmain', name: 'SysMain Toggle', desc: 'Enable/disable Superfetch/SysMain', category: 'performance', color: 'var(--red)', icon: '🔄' },
  { id: 'pagefile', name: 'Pagefile Optimizer', desc: 'Auto-calculate optimal page file', category: 'performance', color: 'var(--cyan)', icon: '📊' },
  { id: 'gamebar', name: 'Game Bar Disabler', desc: 'Disable Game Bar + DVR', category: 'performance', color: 'var(--red)', icon: '🎯' },
  // System Info
  { id: 'apps', name: 'Installed Apps List', desc: 'Full list with version & publisher', category: 'sysinfo', color: 'var(--accent)', icon: '📦' },
  { id: 'drivers', name: 'Driver Version Report', desc: 'All drivers with date & version', category: 'sysinfo', color: 'var(--purple)', icon: '🔌' },
  { id: 'license', name: 'Windows License Info', desc: 'Show Windows product key info', category: 'sysinfo', color: 'var(--green)', icon: '🔑' },
  { id: 'hw_export', name: 'Hardware Summary Export', desc: 'Export full specs to HTML/PDF', category: 'sysinfo', color: 'var(--orange)', icon: '💻' },
  { id: 'uptime_log', name: 'Uptime & Boot Log', desc: 'Boot duration history viewer', category: 'sysinfo', color: 'var(--cyan)', icon: '⏱️' },
  { id: 'bios', name: 'BIOS Version Info', desc: 'Display BIOS/UEFI firmware info', category: 'sysinfo', color: 'var(--yellow)', icon: '🖥️' },
];

const categories = [
  { id: 'all', label: 'All Utilities', count: utilities.length },
  { id: 'cleaner', label: '🧹 Cleaner', count: utilities.filter(u => u.category === 'cleaner').length },
  { id: 'repair', label: '🔧 Repair', count: utilities.filter(u => u.category === 'repair').length },
  { id: 'network', label: '🌐 Network', count: utilities.filter(u => u.category === 'network').length },
  { id: 'security', label: '🔒 Security', count: utilities.filter(u => u.category === 'security').length },
  { id: 'performance', label: '⚡ Performance', count: utilities.filter(u => u.category === 'performance').length },
  { id: 'sysinfo', label: '🖥️ System Info', count: utilities.filter(u => u.category === 'sysinfo').length },
];

export default function Utilities() {
  const [activeCategory, setActiveCategory] = useState('all');
  const [search, setSearch] = useState('');
  const [running, setRunning] = useState<Set<string>>(new Set());
  const [done, setDone] = useState<Set<string>>(new Set());

  const filtered = utilities.filter(u => {
    const matchCat = activeCategory === 'all' || u.category === activeCategory;
    const matchSearch = u.name.toLowerCase().includes(search.toLowerCase()) ||
      u.desc.toLowerCase().includes(search.toLowerCase());
    return matchCat && matchSearch;
  });

  const handleRun = (id: string) => {
    if (running.has(id) || done.has(id)) return;
    setRunning(prev => new Set([...prev, id]));
    setTimeout(() => {
      setRunning(prev => { const n = new Set(prev); n.delete(id); return n; });
      setDone(prev => new Set([...prev, id]));
      setTimeout(() => {
        setDone(prev => { const n = new Set(prev); n.delete(id); return n; });
      }, 3000);
    }, 1800);
  };

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800 }}>Utilities Hub</h1>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
            {utilities.length} one-click tools for every Windows problem
          </p>
        </div>
        <div style={{ position: 'relative' }}>
          <input
            type="text"
            placeholder="Search utilities…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ paddingLeft: 36, width: 240 }}
          />
          <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }}>
            🔍
          </span>
        </div>
      </div>

      {/* Category Bar */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {categories.map(cat => (
          <button
            key={cat.id}
            onClick={() => setActiveCategory(cat.id)}
            style={{
              padding: '6px 14px', borderRadius: 20, border: '1px solid',
              fontSize: 12, fontWeight: 600, cursor: 'pointer', transition: 'all 0.2s',
              background: activeCategory === cat.id ? 'var(--accent)' : 'var(--bg-card)',
              borderColor: activeCategory === cat.id ? 'var(--accent)' : 'var(--border)',
              color: activeCategory === cat.id ? 'white' : 'var(--text-secondary)',
            }}
          >
            {cat.label} <span style={{ opacity: 0.7 }}>({cat.count})</span>
          </button>
        ))}
      </div>

      {/* Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
        {filtered.map(util => {
          const isRunning = running.has(util.id);
          const isDone = done.has(util.id);
          return (
            <div key={util.id} className="utility-card" onClick={() => handleRun(util.id)}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                <div style={{
                  width: 40, height: 40, borderRadius: 10,
                  background: `${util.color}22`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 20, flexShrink: 0
                }}>
                  {util.icon}
                </div>
                {isDone && <CheckCircle size={16} color="var(--green)" />}
                {isRunning && <RefreshCw size={16} color="var(--accent)" className="spinner" />}
              </div>
              <div>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.3 }}>{util.name}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.4 }}>{util.desc}</div>
              </div>
              <button
                onClick={e => { e.stopPropagation(); handleRun(util.id); }}
                style={{
                  background: isDone ? 'rgba(34,197,94,0.15)' : `${util.color}22`,
                  color: isDone ? 'var(--green)' : util.color,
                  border: `1px solid ${isDone ? 'rgba(34,197,94,0.3)' : `${util.color}44`}`,
                  borderRadius: 6, padding: '5px 10px', fontSize: 11, fontWeight: 700,
                  cursor: 'pointer', transition: 'all 0.2s', display: 'flex',
                  alignItems: 'center', gap: 4, justifyContent: 'center', width: '100%'
                }}
              >
                {isRunning ? (
                  <><RefreshCw size={11} className="spinner" /> Running…</>
                ) : isDone ? (
                  <><CheckCircle size={11} /> Done!</>
                ) : (
                  <><Play size={11} /> Run</>
                )}
              </button>
            </div>
          );
        })}
      </div>

      {filtered.length === 0 && (
        <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
          <div style={{ fontSize: 40 }}>🔍</div>
          <p style={{ fontSize: 14, marginTop: 12 }}>No utilities found for "{search}"</p>
        </div>
      )}
    </div>
  );
}
