import { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import {
  Cpu, HardDrive, MemoryStick, Wifi, Battery,
  Clock, AlertTriangle, TrendingUp, Activity, Monitor,
  RefreshCw, Download
} from 'lucide-react';

interface MetricHistory {
  t: string;
  cpu: number;
  ram: number;
  gpu: number;
  temp: number;
}

function generateHistory(): MetricHistory[] {
  const data: MetricHistory[] = [];
  let cpu = 35, ram = 62, gpu = 20, temp = 55;
  for (let i = 59; i >= 0; i--) {
    cpu = Math.min(95, Math.max(5, cpu + (Math.random() - 0.5) * 10));
    ram = Math.min(92, Math.max(40, ram + (Math.random() - 0.5) * 4));
    gpu = Math.min(85, Math.max(5, gpu + (Math.random() - 0.5) * 15));
    temp = Math.min(88, Math.max(45, temp + (Math.random() - 0.5) * 5));
    data.push({
      t: `${i}s`,
      cpu: Math.round(cpu),
      ram: Math.round(ram),
      gpu: Math.round(gpu),
      temp: Math.round(temp),
    });
  }
  return data;
}

const specs = {
  cpu: { name: 'Intel Core i7-6500U @ 2.50GHz', cores: 2, threads: 4, usage: 38, temp: 62 },
  gpu: { name: 'AMD Radeon R5 M335', vram: '2.00 GB', usage: 22, temp: 54 },
  ram: { total: '11.89 GB', used: '8.56 GB', usedPct: 72, speed: '2133 MHz', modules: 2 },
  storage: { label: 'C:\\', total: '1.14 TB', used: '1.04 TB', usedPct: 91, type: 'HDD', health: 'Good' },
  network: { down: 24.3, up: 3.8, ping: 18, adapter: 'Realtek PCIe GbE' },
  battery: { level: 74, health: 82, cycles: 312, status: 'Discharging' },
  uptime: '2d 14h 38m',
  score: 67,
};

const healthIssues = [
  { id: 1, severity: 'warning', msg: 'Disk at 91% — Low free space on C:\\', fix: 'Run Disk Cleanup' },
  { id: 2, severity: 'warning', msg: 'RAM usage is 72% at idle — check background apps', fix: 'Kill Zombies' },
  { id: 3, severity: 'info', msg: 'HDD detected — Consider disk optimization', fix: 'Defrag Now' },
  { id: 4, severity: 'ok', msg: 'CPU temperature is normal (62°C)', fix: null },
  { id: 5, severity: 'warning', msg: 'Battery health at 82% — moderate degradation', fix: 'View Report' },
];

function getScoreColor(score: number) {
  if (score >= 80) return 'var(--green)';
  if (score >= 60) return 'var(--yellow)';
  if (score >= 40) return 'var(--orange)';
  return 'var(--red)';
}
function getScoreLabel(score: number) {
  if (score >= 80) return 'GOOD';
  if (score >= 60) return 'FAIR';
  if (score >= 40) return 'POOR';
  return 'CRITICAL';
}

function CircularScore({ score }: { score: number }) {
  const r = 54;
  const circ = 2 * Math.PI * r;
  const pct = score / 100;
  const offset = circ * (1 - pct);
  const color = getScoreColor(score);
  return (
    <div className="score-ring" style={{ width: 140, height: 140 }}>
      <svg width="140" height="140" style={{ transform: 'rotate(-90deg)' }}>
        <circle cx="70" cy="70" r={r} fill="none" stroke="var(--border)" strokeWidth="10" />
        <circle
          cx="70" cy="70" r={r} fill="none"
          stroke={color} strokeWidth="10"
          strokeDasharray={circ} strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 1.2s ease, stroke 0.5s ease' }}
        />
      </svg>
      <div style={{ position: 'absolute', textAlign: 'center' }}>
        <div style={{ fontSize: 32, fontWeight: 800, color, lineHeight: 1 }}>{score}</div>
        <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em', marginTop: 4 }}>
          {getScoreLabel(score)}
        </div>
      </div>
    </div>
  );
}

function ProgressBar({ value, color = 'var(--accent)' }: { value: number; color?: string }) {
  const c = value > 85 ? 'var(--red)' : value > 70 ? 'var(--yellow)' : color;
  return (
    <div className="progress-bar-bg" style={{ marginTop: 8 }}>
      <div className="progress-bar-fill" style={{ width: `${value}%`, background: c }} />
    </div>
  );
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: '8px 12px', fontSize: 12 }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>{label}</div>
      {payload.map((p: any) => (
        <div key={p.dataKey} style={{ color: p.color }}>{p.name}: {p.value}%</div>
      ))}
    </div>
  );
};

export default function Dashboard() {
  const [history, setHistory] = useState<MetricHistory[]>(generateHistory());
  const [scanning, setScanning] = useState(false);
  const [activeChart, setActiveChart] = useState<'cpu' | 'ram' | 'gpu' | 'temp'>('cpu');

  useEffect(() => {
    const iv = setInterval(() => {
      setHistory(prev => {
        const last = prev[prev.length - 1];
        const newCpu = Math.min(95, Math.max(5, last.cpu + (Math.random() - 0.5) * 8));
        const newRam = Math.min(92, Math.max(40, last.ram + (Math.random() - 0.5) * 3));
        const newGpu = Math.min(85, Math.max(5, last.gpu + (Math.random() - 0.5) * 12));
        const newTemp = Math.min(88, Math.max(45, last.temp + (Math.random() - 0.5) * 4));
        return [...prev.slice(1), { t: '0s', cpu: Math.round(newCpu), ram: Math.round(newRam), gpu: Math.round(newGpu), temp: Math.round(newTemp) }];
      });
    }, 2000);
    return () => clearInterval(iv);
  }, []);

  const current = history[history.length - 1];

  const chartColors: Record<string, string> = {
    cpu: 'var(--accent)', ram: 'var(--purple)', gpu: 'var(--cyan)', temp: 'var(--orange)'
  };
  const chartLabels: Record<string, string> = {
    cpu: 'CPU %', ram: 'RAM %', gpu: 'GPU %', temp: 'Temp °C'
  };

  const handleScan = () => {
    setScanning(true);
    setTimeout(() => setScanning(false), 2500);
  };

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-primary)' }}>System Overview</h1>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>Real-time hardware monitoring & health analysis</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn-secondary" style={{ fontSize: 12 }}>
            <Download size={14} /> Export Report
          </button>
          <button className="btn-primary" onClick={handleScan} style={{ minWidth: 140 }}>
            {scanning ? <><RefreshCw size={14} className="spinner" /> Scanning…</> : <><Activity size={14} /> Scan Hardware</>}
          </button>
        </div>
      </div>

      {/* Top Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
        {/* Health Score */}
        <div className="glass-card" style={{ padding: 20, display: 'flex', alignItems: 'center', gap: 20 }}>
          <CircularScore score={specs.score} />
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 8 }}>Health Score</div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.8 }}>
              <div>• Disk: <span style={{ color: 'var(--red)' }}>Critical (91%)</span></div>
              <div>• RAM: <span style={{ color: 'var(--yellow)' }}>Warning (72%)</span></div>
              <div>• CPU: <span style={{ color: 'var(--green)' }}>Good (38%)</span></div>
              <div>• Thermal: <span style={{ color: 'var(--green)' }}>Normal (62°C)</span></div>
            </div>
          </div>
        </div>

        {/* Uptime & Network */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div className="glass-card" style={{ padding: 16, flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
              <Clock size={16} color="var(--cyan)" />
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Uptime</span>
            </div>
            <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--cyan)' }}>{specs.uptime}</div>
          </div>
          <div className="glass-card" style={{ padding: 16, flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
              <Wifi size={16} color="var(--green)" />
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Network</span>
              <span className="badge badge-green" style={{ marginLeft: 'auto' }}>Connected</span>
            </div>
            <div style={{ display: 'flex', gap: 16 }}>
              <div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>↓ DOWN</div>
                <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--green)' }}>{specs.network.down} Mbps</div>
              </div>
              <div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>↑ UP</div>
                <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--accent)' }}>{specs.network.up} Mbps</div>
              </div>
              <div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>PING</div>
                <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--yellow)' }}>{specs.network.ping}ms</div>
              </div>
            </div>
          </div>
        </div>

        {/* Battery */}
        <div className="glass-card" style={{ padding: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
            <Battery size={16} color="var(--yellow)" />
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Battery Health</span>
            <span className="badge badge-yellow" style={{ marginLeft: 'auto' }}>{specs.battery.status}</span>
          </div>
          <div style={{ fontSize: 36, fontWeight: 800, color: 'var(--yellow)', marginBottom: 4 }}>{specs.battery.level}%</div>
          <ProgressBar value={specs.battery.level} color="var(--yellow)" />
          <div style={{ display: 'flex', gap: 16, marginTop: 12, fontSize: 12, color: 'var(--text-secondary)' }}>
            <div>Health: <strong style={{ color: 'var(--text-primary)' }}>{specs.battery.health}%</strong></div>
            <div>Cycles: <strong style={{ color: 'var(--text-primary)' }}>{specs.battery.cycles}</strong></div>
          </div>
        </div>
      </div>

      {/* Live Chart */}
      <div className="glass-card" style={{ padding: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <TrendingUp size={16} color="var(--accent)" />
            <span style={{ fontSize: 13, fontWeight: 700 }}>60-Second Rolling Graph</span>
          </div>
          <div className="tab-bar">
            {(['cpu', 'ram', 'gpu', 'temp'] as const).map(k => (
              <div key={k} className={`tab-item ${activeChart === k ? 'active' : ''}`} onClick={() => setActiveChart(k)}>
                {chartLabels[k]}
              </div>
            ))}
          </div>
        </div>
        <ResponsiveContainer width="100%" height={120}>
          <AreaChart data={history} margin={{ top: 4, right: 0, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={chartColors[activeChart]} stopOpacity={0.3} />
                <stop offset="95%" stopColor={chartColors[activeChart]} stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="t" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} interval={9} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Area type="monotone" dataKey={activeChart} name={chartLabels[activeChart]}
              stroke={chartColors[activeChart]} strokeWidth={2}
              fill="url(#areaGrad)" dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Hardware Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        {/* CPU */}
        <div className="metric-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <div style={{ background: 'rgba(59,130,246,0.15)', borderRadius: 8, padding: 8 }}>
              <Cpu size={18} color="var(--accent)" />
            </div>
            <div>
              <div style={{ fontSize: 13, fontWeight: 700 }}>CPU</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{specs.cpu.name}</div>
            </div>
            <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
              <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--accent)' }}>{current.cpu}%</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{specs.cpu.temp}°C</div>
            </div>
          </div>
          <ProgressBar value={current.cpu} color="var(--accent)" />
          <div style={{ display: 'flex', gap: 16, marginTop: 10, fontSize: 11, color: 'var(--text-secondary)' }}>
            <span>{specs.cpu.cores} Cores / {specs.cpu.threads} Threads</span>
          </div>
        </div>

        {/* GPU */}
        <div className="metric-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <div style={{ background: 'rgba(6,182,212,0.15)', borderRadius: 8, padding: 8 }}>
              <Monitor size={18} color="var(--cyan)" />
            </div>
            <div>
              <div style={{ fontSize: 13, fontWeight: 700 }}>GPU</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{specs.gpu.name}</div>
            </div>
            <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
              <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--cyan)' }}>{current.gpu}%</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{specs.gpu.temp}°C</div>
            </div>
          </div>
          <ProgressBar value={current.gpu} color="var(--cyan)" />
          <div style={{ display: 'flex', gap: 16, marginTop: 10, fontSize: 11, color: 'var(--text-secondary)' }}>
            <span>VRAM: {specs.gpu.vram}</span>
          </div>
        </div>

        {/* RAM */}
        <div className="metric-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <div style={{ background: 'rgba(168,85,247,0.15)', borderRadius: 8, padding: 8 }}>
              <MemoryStick size={18} color="var(--purple)" />
            </div>
            <div>
              <div style={{ fontSize: 13, fontWeight: 700 }}>RAM</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Total: {specs.ram.total} · {specs.ram.speed}</div>
            </div>
            <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
              <div style={{ fontSize: 22, fontWeight: 800, color: current.ram > 80 ? 'var(--red)' : 'var(--purple)' }}>{current.ram}%</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{specs.ram.used} used</div>
            </div>
          </div>
          <ProgressBar value={current.ram} color="var(--purple)" />
          <div style={{ display: 'flex', gap: 16, marginTop: 10, fontSize: 11, color: 'var(--text-secondary)' }}>
            <span>{specs.ram.modules} Modules installed</span>
          </div>
        </div>

        {/* Storage */}
        <div className="metric-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <div style={{ background: 'rgba(249,115,22,0.15)', borderRadius: 8, padding: 8 }}>
              <HardDrive size={18} color="var(--orange)" />
            </div>
            <div>
              <div style={{ fontSize: 13, fontWeight: 700 }}>Storage</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{specs.storage.label} · {specs.storage.type}</div>
            </div>
            <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
              <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--red)' }}>{specs.storage.usedPct}%</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{specs.storage.total} total</div>
            </div>
          </div>
          <ProgressBar value={specs.storage.usedPct} color="var(--orange)" />
          <div style={{ display: 'flex', gap: 16, marginTop: 10, fontSize: 11, color: 'var(--text-secondary)' }}>
            <span>{specs.storage.used} used · Health: <span style={{ color: 'var(--green)' }}>{specs.storage.health}</span></span>
          </div>
        </div>
      </div>

      {/* Issues */}
      <div className="glass-card" style={{ padding: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
          <AlertTriangle size={16} color="var(--yellow)" />
          <span style={{ fontSize: 13, fontWeight: 700 }}>Detected Issues</span>
          <span className="badge badge-yellow" style={{ marginLeft: 4 }}>
            {healthIssues.filter(i => i.severity !== 'ok').length} issues
          </span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {healthIssues.map(issue => (
            <div key={issue.id} style={{
              display: 'flex', alignItems: 'center', gap: 12,
              padding: '10px 14px', borderRadius: 8,
              background: issue.severity === 'ok' ? 'rgba(34,197,94,0.05)' : issue.severity === 'warning' ? 'rgba(234,179,8,0.05)' : 'rgba(239,68,68,0.05)',
              border: `1px solid ${issue.severity === 'ok' ? 'rgba(34,197,94,0.15)' : issue.severity === 'warning' ? 'rgba(234,179,8,0.15)' : 'rgba(239,68,68,0.15)'}`,
            }}>
              <div className="status-dot" style={{
                background: issue.severity === 'ok' ? 'var(--green)' : issue.severity === 'warning' ? 'var(--yellow)' : 'var(--red)',
                flexShrink: 0
              }} />
              <span style={{ fontSize: 12, color: 'var(--text-secondary)', flex: 1 }}>{issue.msg}</span>
              {issue.fix && (
                <button className="tool-btn">{issue.fix}</button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
