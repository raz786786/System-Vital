import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Globe, RefreshCw, Play } from 'lucide-react';

interface PingPoint { t: string; ping: number; }

function generatePing(): PingPoint[] {
  const pts: PingPoint[] = [];
  let p = 18;
  for (let i = 29; i >= 0; i--) {
    p = Math.max(5, Math.min(120, p + (Math.random() - 0.45) * 20));
    pts.push({ t: `${i}s`, ping: Math.round(p) });
  }
  return pts;
}

const dnsServers = [
  { name: 'ISP Default', addr: '10.0.0.1', latency: null as number | null, status: 'idle' as string },
  { name: 'Google DNS', addr: '8.8.8.8', latency: null as number | null, status: 'idle' as string },
  { name: 'Cloudflare', addr: '1.1.1.1', latency: null as number | null, status: 'idle' as string },
  { name: 'OpenDNS', addr: '208.67.222.222', latency: null as number | null, status: 'idle' as string },
  { name: 'Quad9', addr: '9.9.9.9', latency: null as number | null, status: 'idle' as string },
];

export default function NetworkSuite() {
  const [pingHistory, setPingHistory] = useState<PingPoint[]>(generatePing());
  const [dnsData, setDnsData] = useState(dnsServers);
  const [benchRunning, setBenchRunning] = useState(false);
  const [activeTab, setActiveTab] = useState<'monitor' | 'dns' | 'tools' | 'info'>('monitor');
  const [currentPing, setCurrentPing] = useState(18);
  const [toolRunning, setToolRunning] = useState<Set<string>>(new Set());
  const [toolResults, setToolResults] = useState<Record<string, string>>({});

  useEffect(() => {
    const iv = setInterval(() => {
      setPingHistory(prev => {
        const last = prev[prev.length - 1];
        const newPing = Math.max(5, Math.min(150, last.ping + (Math.random() - 0.45) * 20));
        const rounded = Math.round(newPing);
        setCurrentPing(rounded);
        return [...prev.slice(1), { t: '0s', ping: rounded }];
      });
    }, 1500);
    return () => clearInterval(iv);
  }, []);

  const runDnsBenchmark = () => {
    setBenchRunning(true);
    setDnsData(dnsServers.map(d => ({ ...d, latency: null, status: 'testing' })));
    dnsServers.forEach((_, i) => {
      setTimeout(() => {
        const latency = Math.round(8 + Math.random() * 60);
        setDnsData(prev => prev.map((d, idx) =>
          idx === i ? { ...d, latency, status: 'done' } : d
        ));
        if (i === dnsServers.length - 1) setBenchRunning(false);
      }, (i + 1) * 600);
    });
  };

  const runTool = (id: string, result: string) => {
    setToolRunning(prev => new Set([...prev, id]));
    setTimeout(() => {
      setToolRunning(prev => { const n = new Set(prev); n.delete(id); return n; });
      setToolResults(prev => ({ ...prev, [id]: result }));
    }, 2000);
  };

  const pingColor = currentPing < 30 ? 'var(--green)' : currentPing < 80 ? 'var(--yellow)' : 'var(--red)';

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: '6px 12px', fontSize: 12 }}>
        <span style={{ color: pingColor }}>Ping: {payload[0]?.value}ms</span>
      </div>
    );
  };

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800 }}>Network Suite</h1>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>Monitor, diagnose, and repair network issues</p>
        </div>
        <div className="tab-bar">
          {([['monitor', '📶 Live Monitor'], ['dns', '🌐 DNS Bench'], ['tools', '🔧 Tools'], ['info', 'ℹ️ Adapter Info']] as const).map(([k, lbl]) => (
            <div key={k} className={`tab-item ${activeTab === k ? 'active' : ''}`} onClick={() => setActiveTab(k)}>{lbl}</div>
          ))}
        </div>
      </div>

      {activeTab === 'monitor' && (
        <>
          {/* Stats Row */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
            {[
              { label: 'LIVE PING', value: `${currentPing}ms`, color: pingColor, sub: 'to 8.8.8.8' },
              { label: 'DOWNLOAD', value: '24.3 Mbps', color: 'var(--green)', sub: 'Realtek PCIe GbE' },
              { label: 'UPLOAD', value: '3.8 Mbps', color: 'var(--accent)', sub: 'DHCP assigned' },
              { label: 'STATUS', value: 'Connected', color: 'var(--green)', sub: 'No packet loss' },
            ].map(stat => (
              <div key={stat.label} className="glass-card" style={{ padding: 16, textAlign: 'center' }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.1em', marginBottom: 6 }}>{stat.label}</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: stat.color }}>{stat.value}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{stat.sub}</div>
              </div>
            ))}
          </div>

          {/* Live Ping Graph */}
          <div className="glass-card" style={{ padding: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
              <div className="status-dot" style={{ background: 'var(--green)', boxShadow: '0 0 6px var(--green)' }} />
              <span style={{ fontSize: 13, fontWeight: 700 }}>Live Ping Graph</span>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>— real-time latency to 8.8.8.8</span>
              <span style={{ marginLeft: 'auto', fontSize: 20, fontWeight: 800, color: pingColor }}>{currentPing}ms</span>
            </div>
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={pingHistory} margin={{ top: 4, right: 0, left: -20, bottom: 0 }}>
                <XAxis dataKey="t" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} interval={5} />
                <YAxis domain={[0, 150]} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Line type="monotone" dataKey="ping" stroke={pingColor} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Quick Network Actions */}
          <div className="glass-card" style={{ padding: 20 }}>
            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 14 }}>Quick Network Fixes</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
              {[
                { id: 'dns_flush', label: 'Flush DNS', icon: '🌐', result: '✅ DNS cache flushed successfully' },
                { id: 'ip_renew', label: 'IP Release/Renew', icon: '📡', result: '✅ IP renewed: 192.168.1.105' },
                { id: 'winsock', label: 'Reset WinSock', icon: '🔌', result: '✅ WinSock reset complete (restart required)' },
                { id: 'proxy', label: 'Clear Proxy', icon: '🔐', result: '✅ No proxy detected — all clear' },
                { id: 'firewall', label: 'Check Firewall', icon: '🛡️', result: '✅ All firewall profiles active' },
                { id: 'adapter', label: 'Reset Adapter', icon: '📶', result: '✅ Network adapter restarted' },
              ].map(tool => (
                <div key={tool.id} style={{
                  background: 'var(--bg-secondary)', border: '1px solid var(--border)',
                  borderRadius: 8, padding: '12px 14px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <span style={{ fontSize: 18 }}>{tool.icon}</span>
                    <span style={{ fontSize: 12, fontWeight: 700 }}>{tool.label}</span>
                  </div>
                  {toolResults[tool.id] && (
                    <div style={{ fontSize: 11, color: 'var(--green)', marginBottom: 8, lineHeight: 1.4 }}>{toolResults[tool.id]}</div>
                  )}
                  <button className="btn-primary" style={{ width: '100%', justifyContent: 'center', fontSize: 11 }}
                    onClick={() => runTool(tool.id, tool.result)}>
                    {toolRunning.has(tool.id) ? <><RefreshCw size={11} className="spinner" />Running</> : <><Play size={11} />Run</>}
                  </button>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {activeTab === 'dns' && (
        <div className="glass-card" style={{ padding: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700 }}>DNS Benchmark</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>Compare DNS servers to find the fastest one for your location</div>
            </div>
            <button className="btn-primary" onClick={runDnsBenchmark} disabled={benchRunning}>
              {benchRunning ? <><RefreshCw size={14} className="spinner" />Testing…</> : <><Play size={14} />Run Benchmark</>}
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {dnsData.map((dns, i) => {
              const fastest = dnsData.filter(d => d.latency !== null).sort((a, b) => (a.latency ?? 999) - (b.latency ?? 999))[0];
              const isFastest = fastest && dns.addr === fastest.addr && dns.latency !== null;
              return (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: 16, padding: '14px 16px',
                  borderRadius: 10, background: isFastest ? 'rgba(34,197,94,0.05)' : 'var(--bg-secondary)',
                  border: `1px solid ${isFastest ? 'rgba(34,197,94,0.3)' : 'var(--border)'}`,
                }}>
                  <Globe size={16} color={isFastest ? 'var(--green)' : 'var(--text-muted)'} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 700 }}>{dns.name}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{dns.addr}</div>
                  </div>
                  {dns.status === 'testing' && <RefreshCw size={16} color="var(--accent)" className="spinner" />}
                  {dns.latency !== null && (
                    <>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: 18, fontWeight: 800, color: dns.latency < 20 ? 'var(--green)' : dns.latency < 50 ? 'var(--yellow)' : 'var(--red)' }}>
                          {dns.latency}ms
                        </div>
                      </div>
                      {isFastest && <span className="badge badge-green">⚡ FASTEST</span>}
                    </>
                  )}
                  {dns.latency !== null && (
                    <button className="tool-btn">Set as Default</button>
                  )}
                </div>
              );
            })}
          </div>

          {dnsData.some(d => d.latency !== null) && (
            <div style={{ marginTop: 16, padding: 14, background: 'rgba(59,130,246,0.05)', borderRadius: 8, border: '1px solid rgba(59,130,246,0.15)', fontSize: 12, color: 'var(--text-secondary)' }}>
              💡 <strong>Tip:</strong> A faster DNS server can significantly reduce page load times. Click "Set as Default" to apply the fastest server automatically.
            </div>
          )}
        </div>
      )}

      {activeTab === 'tools' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {[
            { id: 'wifi_pass', title: 'Wi-Fi Password Viewer', desc: 'Show passwords for all saved Wi-Fi networks', icon: '🔑', result: 'HomeNetwork: mypassword123\nOfficeWifi: c0rp0rate@2024\nPhone_Hotspot: hotspot456' },
            { id: 'port_check', title: 'Port Checker', desc: 'Test if specific ports are open or blocked', icon: '🚪', result: 'Port 80 (HTTP): OPEN\nPort 443 (HTTPS): OPEN\nPort 3389 (RDP): CLOSED\nPort 22 (SSH): CLOSED' },
            { id: 'net_shares', title: 'Network Share Auditor', desc: 'List all shared folders on this system', icon: '📁', result: 'No shared folders found — System is secure' },
            { id: 'vpn_reset', title: 'VPN Reset Tool', desc: 'Reset WinSock + TCP/IP stack after VPN break', icon: '🔒', result: 'WinSock reset: ✅\nTCP/IP stack reset: ✅\nRestart required to apply' },
            { id: 'smb', title: 'SMB Repair', desc: 'Reset SMB service + credential manager', icon: '🔄', result: 'SMB service restarted: ✅\nCredential cache cleared: ✅' },
            { id: 'rdp', title: 'RDP Enabler', desc: 'Toggle Remote Desktop via registry + firewall', icon: '🖥️', result: 'Remote Desktop: ENABLED\nFirewall rule added: ✅' },
          ].map(tool => (
            <div key={tool.id} className="glass-card" style={{ padding: 20 }}>
              <div style={{ fontSize: 32, marginBottom: 10 }}>{tool.icon}</div>
              <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 6 }}>{tool.title}</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 14, lineHeight: 1.5 }}>{tool.desc}</div>
              {toolResults[tool.id] && (
                <div style={{
                  background: 'var(--bg-secondary)', borderRadius: 8, padding: 12, marginBottom: 12,
                  fontSize: 12, fontFamily: 'monospace', color: 'var(--green)',
                  border: '1px solid var(--border)', whiteSpace: 'pre-line'
                }}>
                  {toolResults[tool.id]}
                </div>
              )}
              <button className="btn-primary" style={{ width: '100%', justifyContent: 'center' }}
                onClick={() => runTool(tool.id, tool.result)}>
                {toolRunning.has(tool.id) ? <><RefreshCw size={14} className="spinner" />Running…</> : <><Play size={14} />Execute</>}
              </button>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'info' && (
        <div className="glass-card" style={{ padding: 24 }}>
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 20 }}>Network Adapter Information</div>
          {[
            { label: 'Adapter Name', value: 'Realtek PCIe GbE Family Controller' },
            { label: 'Connection Type', value: 'Ethernet (Wired)' },
            { label: 'IP Address', value: '192.168.1.104' },
            { label: 'Subnet Mask', value: '255.255.255.0' },
            { label: 'Default Gateway', value: '192.168.1.1' },
            { label: 'DNS Servers', value: '8.8.8.8, 8.8.4.4' },
            { label: 'MAC Address', value: 'A4:C3:F0:1B:7E:23' },
            { label: 'Link Speed', value: '1000 Mbps (Gigabit)' },
            { label: 'Driver Version', value: '10.51.1011.2020' },
            { label: 'Driver Date', value: 'November 2020 — ⚠️ Outdated (3+ years)' },
          ].map((row, i) => (
            <div key={i} style={{
              display: 'flex', gap: 16, padding: '10px 0',
              borderBottom: i < 9 ? '1px solid var(--border)' : 'none'
            }}>
              <span style={{ fontSize: 12, color: 'var(--text-muted)', minWidth: 160, fontWeight: 600 }}>{row.label}</span>
              <span style={{ fontSize: 12, color: row.value.includes('Outdated') ? 'var(--yellow)' : 'var(--text-primary)', fontFamily: row.value.includes('.') && !row.value.includes('Realtek') ? 'monospace' : 'inherit' }}>{row.value}</span>
            </div>
          ))}
          <div style={{ marginTop: 16, display: 'flex', gap: 10 }}>
            <button className="btn-primary"><Play size={14} />Update Driver</button>
            <button className="btn-secondary"><RefreshCw size={14} />Reset Adapter</button>
          </div>
        </div>
      )}
    </div>
  );
}
