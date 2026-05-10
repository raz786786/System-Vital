import { useState } from 'react';
import {
  Search, Play, CheckCircle, AlertTriangle, XCircle, RefreshCw,
  Shield, HardDrive, Wifi, Trash2, FileText, Terminal, Clock
} from 'lucide-react';

interface DiagResult {
  id: string;
  label: string;
  status: 'pass' | 'warn' | 'fail' | 'pending';
  detail: string;
  fix?: string;
}

const defaultResults: DiagResult[] = [
  { id: 'disk', label: 'Disk Health (S.M.A.R.T.)', status: 'pass', detail: 'No bad sectors detected. Reallocated: 0', fix: undefined },
  { id: 'ram', label: 'RAM Integrity Check', status: 'pass', detail: 'No memory errors detected in last boot', fix: undefined },
  { id: 'sysfiles', label: 'System File Integrity (SFC)', status: 'warn', detail: '3 corrupted files detected. Repair recommended.', fix: 'sfc /scannow' },
  { id: 'dism', label: 'Windows Image (DISM)', status: 'pass', detail: 'Component store is healthy', fix: undefined },
  { id: 'updates', label: 'Windows Update Status', status: 'warn', detail: '2 updates pending installation', fix: 'Open Windows Update' },
  { id: 'defender', label: 'Windows Defender Status', status: 'pass', detail: 'Real-time protection: ON. Last scan: 2h ago', fix: undefined },
  { id: 'firewall', label: 'Firewall Status', status: 'pass', detail: 'All profiles active (Domain, Private, Public)', fix: undefined },
  { id: 'startup', label: 'Startup Programs', status: 'warn', detail: '14 startup entries found (6 high impact)', fix: 'Manage Startup' },
  { id: 'disk_usage', label: 'Disk Usage', status: 'fail', detail: 'C:\\ is 91% full — critical low space', fix: 'Run Disk Cleanup' },
  { id: 'temp', label: 'Temp Files Scan', status: 'warn', detail: '3.2 GB of temp files found', fix: 'Clean Temp Files' },
  { id: 'drivers', label: 'Driver Health Check', status: 'warn', detail: '4 drivers older than 1 year detected', fix: 'View Drivers' },
  { id: 'events', label: 'Critical Event Log Errors', status: 'fail', detail: '12 critical errors in last 24 hours', fix: 'View Events' },
];

const quickTools = [
  { id: 'explorer', label: 'Restart Explorer', icon: RefreshCw, color: 'var(--accent)', desc: 'Kill & restart explorer.exe' },
  { id: 'dns', label: 'Flush DNS', icon: Wifi, color: 'var(--cyan)', desc: 'ipconfig /flushdns' },
  { id: 'optimize', label: 'Optimize Drives', icon: HardDrive, color: 'var(--orange)', desc: 'Defrag HDD / TRIM SSD' },
  { id: 'clean', label: 'Clean Temp Files', icon: Trash2, color: 'var(--red)', desc: 'Wipe %TEMP% & Windows\\Temp' },
  { id: 'sfc', label: 'Run SFC Scan', icon: Shield, color: 'var(--green)', desc: 'System file integrity check' },
  { id: 'dism', label: 'Run DISM Repair', icon: Terminal, color: 'var(--purple)', desc: 'Repair Windows image' },
  { id: 'iprenew', label: 'IP Release/Renew', icon: Wifi, color: 'var(--cyan)', desc: 'Reset IP configuration' },
  { id: 'eventlog', label: 'Scan Event Logs', icon: FileText, color: 'var(--yellow)', desc: 'AI-powered log analysis' },
];

const advancedTools = [
  { label: 'HWiNFO Utility', desc: 'Hardware monitoring & sensor data', btn: 'Launch Application', color: 'btn-primary' },
  { label: 'Sensor Log Analysis (HWiNFO)', desc: 'Analyze exported CSV sensor logs', btn: 'Analyze .CSV', color: 'btn-success' },
  { label: 'AI System Log Analysis', desc: 'AI-powered Windows event log scanner', btn: 'Scan Windows Logs', color: 'btn-purple' },
  { label: 'BSOD Minidump Parser', desc: 'Decode crash dump files (.dmp)', btn: 'Parse Dumps', color: 'btn-danger' },
];

function StatusIcon({ status }: { status: DiagResult['status'] }) {
  if (status === 'pass') return <CheckCircle size={16} color="var(--green)" />;
  if (status === 'warn') return <AlertTriangle size={16} color="var(--yellow)" />;
  if (status === 'fail') return <XCircle size={16} color="var(--red)" />;
  return <RefreshCw size={16} color="var(--text-muted)" className="spinner" />;
}

function StatusBadge({ status }: { status: DiagResult['status'] }) {
  const map = {
    pass: { cls: 'badge-green', label: 'PASS' },
    warn: { cls: 'badge-yellow', label: 'WARN' },
    fail: { cls: 'badge-red', label: 'FAIL' },
    pending: { cls: 'badge-blue', label: '...' },
  };
  const { cls, label } = map[status];
  return <span className={`badge ${cls}`}>{label}</span>;
}

export default function Diagnostics() {
  const [results, setResults] = useState<DiagResult[] | null>(null);
  const [running, setRunning] = useState(false);
  const [runningTools, setRunningTools] = useState<Set<string>>(new Set());
  const [score, setScore] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<'results' | 'tools' | 'advanced'>('results');

  const handleRunAll = () => {
    setRunning(true);
    setResults(defaultResults.map(r => ({ ...r, status: 'pending' as const })));
    let i = 0;
    const interval = setInterval(() => {
      setResults(prev => {
        if (!prev) return prev;
        const updated = [...prev];
        if (updated[i]) updated[i] = { ...defaultResults[i] };
        i++;
        if (i >= updated.length) {
          clearInterval(interval);
          setRunning(false);
          const pass = updated.filter(r => r.status === 'pass').length;
          const total = updated.length;
          setScore(Math.round((pass / total) * 100));
        }
        return updated;
      });
    }, 350);
  };

  const handleTool = (id: string) => {
    setRunningTools(prev => new Set([...prev, id]));
    setTimeout(() => {
      setRunningTools(prev => {
        const n = new Set(prev);
        n.delete(id);
        return n;
      });
    }, 2000);
  };

  const passCount = results?.filter(r => r.status === 'pass').length ?? 0;
  const warnCount = results?.filter(r => r.status === 'warn').length ?? 0;
  const failCount = results?.filter(r => r.status === 'fail').length ?? 0;

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800 }}>System Diagnostics</h1>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>Full system health analysis & one-click repair tools</p>
        </div>
        <button className="btn-primary" onClick={handleRunAll} disabled={running} style={{ minWidth: 160 }}>
          {running ? <><RefreshCw size={14} className="spinner" /> Scanning…</> : <><Search size={14} /> Run Full Analysis</>}
        </button>
      </div>

      {/* Score Bar */}
      {results && (
        <div className="glass-card" style={{ padding: 16, display: 'flex', alignItems: 'center', gap: 20 }}>
          <div style={{ display: 'flex', gap: 20, flex: 1 }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 800, color: 'var(--green)' }}>{passCount}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>PASSED</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 800, color: 'var(--yellow)' }}>{warnCount}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>WARNINGS</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 800, color: 'var(--red)' }}>{failCount}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>FAILED</div>
            </div>
          </div>
          {score !== null && (
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 4 }}>HEALTH SCORE</div>
              <div style={{ fontSize: 36, fontWeight: 800, color: score >= 80 ? 'var(--green)' : score >= 60 ? 'var(--yellow)' : 'var(--red)' }}>
                {score}/100
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="tab-bar" style={{ alignSelf: 'flex-start' }}>
        {([['results', 'Scan Results'], ['tools', 'Quick Tools'], ['advanced', 'Advanced Tools']] as const).map(([k, lbl]) => (
          <div key={k} className={`tab-item ${activeTab === k ? 'active' : ''}`} onClick={() => setActiveTab(k)}>{lbl}</div>
        ))}
      </div>

      {/* Scan Results */}
      {activeTab === 'results' && (
        <div className="glass-card" style={{ padding: 20 }}>
          {!results ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
              <Search size={40} style={{ opacity: 0.3, marginBottom: 12 }} />
              <p style={{ fontSize: 14 }}>No diagnostics run yet.</p>
              <p style={{ fontSize: 12, marginTop: 4 }}>Click "Run Full Analysis" to start scanning.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {results.map(r => (
                <div key={r.id} style={{
                  display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px',
                  borderRadius: 8, background: 'var(--bg-secondary)',
                  border: '1px solid var(--border)',
                  opacity: r.status === 'pending' ? 0.6 : 1,
                  transition: 'opacity 0.3s'
                }}>
                  <StatusIcon status={r.status} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>{r.label}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{r.detail}</div>
                  </div>
                  <StatusBadge status={r.status} />
                  {r.fix && r.status !== 'pending' && (
                    <button className="tool-btn">{r.fix}</button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Quick Tools */}
      {activeTab === 'tools' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
          {quickTools.map(tool => {
            const isRunning = runningTools.has(tool.id);
            const Icon = tool.icon;
            return (
              <div key={tool.id} className="glass-card" style={{ padding: 20, textAlign: 'center', cursor: 'pointer' }}
                onClick={() => handleTool(tool.id)}>
                <div style={{
                  width: 48, height: 48, borderRadius: 12,
                  background: `${tool.color}22`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  margin: '0 auto 12px'
                }}>
                  <Icon size={22} color={tool.color} className={isRunning ? 'spinner' : ''} />
                </div>
                <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 6 }}>{tool.label}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 12 }}>{tool.desc}</div>
                <button className="btn-primary" style={{ width: '100%', justifyContent: 'center', fontSize: 12 }}
                  onClick={e => { e.stopPropagation(); handleTool(tool.id); }}>
                  {isRunning ? <><RefreshCw size={12} className="spinner" />Running…</> : <><Play size={12} />Run</>}
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Advanced Tools */}
      {activeTab === 'advanced' && (
        <div className="glass-card" style={{ padding: 20 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {advancedTools.map((tool, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: 16, padding: '14px 16px',
                borderRadius: 10, background: 'var(--bg-secondary)', border: '1px solid var(--border)'
              }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 700 }}>{tool.label}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{tool.desc}</div>
                </div>
                <button className={tool.color}>{tool.btn}</button>
              </div>
            ))}
          </div>

          {/* Fix History */}
          <div style={{ marginTop: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <Clock size={14} color="var(--text-muted)" />
              <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                Fix History
              </span>
            </div>
            {[
              { time: '2h ago', action: 'DNS Flush — ipconfig /flushdns', result: 'Success' },
              { time: '1d ago', action: 'Temp File Cleaner — Removed 2.1 GB', result: 'Success' },
              { time: '3d ago', action: 'SFC Scan — 3 files repaired', result: 'Success' },
              { time: '1w ago', action: 'Disk Optimization — HDD defragmented', result: 'Success' },
            ].map((h, i) => (
              <div key={i} style={{
                display: 'flex', gap: 12, alignItems: 'center', padding: '8px 0',
                borderBottom: i < 3 ? '1px solid var(--border)' : 'none'
              }}>
                <span style={{ fontSize: 11, color: 'var(--text-muted)', minWidth: 50 }}>{h.time}</span>
                <span style={{ fontSize: 12, color: 'var(--text-secondary)', flex: 1 }}>{h.action}</span>
                <span className="badge badge-green">{h.result}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
