import { useState } from 'react';
import { RefreshCw, CheckCircle, AlertTriangle, XCircle, TrendingUp } from 'lucide-react';

interface Category {
  name: string;
  score: number;
  max: number;
  icon: string;
  color: string;
  issues: { severity: 'ok' | 'warn' | 'fail'; msg: string; fix?: string }[];
}

const initialCategories: Category[] = [
  {
    name: 'Disk Health', score: 10, max: 20, icon: '💾', color: 'var(--orange)',
    issues: [
      { severity: 'fail', msg: 'C:\\ drive at 91% capacity — critically low', fix: 'Run Disk Cleanup' },
      { severity: 'warn', msg: 'HDD detected — fragmentation likely', fix: 'Defrag Now' },
      { severity: 'ok', msg: 'No S.M.A.R.T. errors detected' },
    ]
  },
  {
    name: 'RAM Health', score: 16, max: 20, icon: '🧠', color: 'var(--purple)',
    issues: [
      { severity: 'warn', msg: 'RAM at 72% usage at idle — investigate background apps', fix: 'Kill Zombies' },
      { severity: 'ok', msg: 'No memory errors in last boot' },
      { severity: 'ok', msg: 'RAM speed is adequate (DDR3 2133)' },
    ]
  },
  {
    name: 'Thermal', score: 18, max: 20, icon: '🌡️', color: 'var(--green)',
    issues: [
      { severity: 'ok', msg: 'CPU temperature: 62°C (normal)' },
      { severity: 'ok', msg: 'GPU temperature: 54°C (cool)' },
      { severity: 'warn', msg: 'Thermal paste age unknown — consider replacement', fix: 'View Guide' },
    ]
  },
  {
    name: 'Security', score: 14, max: 20, icon: '🔒', color: 'var(--accent)',
    issues: [
      { severity: 'ok', msg: 'Windows Defender active and up to date' },
      { severity: 'ok', msg: 'Firewall enabled on all profiles' },
      { severity: 'warn', msg: '2 startup items flagged as potentially unwanted', fix: 'Review Startup' },
      { severity: 'warn', msg: 'BitLocker recovery key not backed up', fix: 'Backup Key' },
    ]
  },
  {
    name: 'Performance', score: 9, max: 20, icon: '⚡', color: 'var(--yellow)',
    issues: [
      { severity: 'fail', msg: '14 startup programs — 6 high-impact (slow boot)', fix: 'Manage Startup' },
      { severity: 'warn', msg: 'Power plan set to Balanced instead of High Performance', fix: 'Switch Plan' },
      { severity: 'ok', msg: 'Game Mode is enabled' },
    ]
  },
];

function getGrade(pct: number) {
  if (pct >= 90) return { grade: 'A+', color: 'var(--green)' };
  if (pct >= 80) return { grade: 'A', color: 'var(--green)' };
  if (pct >= 70) return { grade: 'B', color: 'var(--cyan)' };
  if (pct >= 60) return { grade: 'C', color: 'var(--yellow)' };
  if (pct >= 50) return { grade: 'D', color: 'var(--orange)' };
  return { grade: 'F', color: 'var(--red)' };
}

export default function HealthScore() {
  const [categories] = useState(initialCategories);
  const [scanning, setScanning] = useState(false);

  const totalScore = categories.reduce((s, c) => s + c.score, 0);
  const maxScore = categories.reduce((s, c) => s + c.max, 0);
  const pct = Math.round((totalScore / maxScore) * 100);
  const { grade, color: gradeColor } = getGrade(pct);

  const runScan = () => {
    setScanning(true);
    setTimeout(() => {
      setScanning(false);
    }, 2500);
  };

  const issueCount = categories.flatMap(c => c.issues).filter(i => i.severity !== 'ok').length;

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800 }}>System Health Score</h1>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>Comprehensive system scoring across 5 key categories</p>
        </div>
        <button className="btn-primary" onClick={runScan} disabled={scanning}>
          {scanning ? <><RefreshCw size={14} className="spinner" />Scanning…</> : <><TrendingUp size={14} />Refresh Score</>}
        </button>
      </div>

      {/* Big Score Card */}
      <div className="glass-card" style={{ padding: 32 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 48, justifyContent: 'center' }}>
          {/* Circular gauge */}
          <div style={{ position: 'relative', width: 180, height: 180, flexShrink: 0 }}>
            <svg width="180" height="180" style={{ transform: 'rotate(-90deg)' }}>
              <circle cx="90" cy="90" r="76" fill="none" stroke="var(--border)" strokeWidth="14" />
              <circle cx="90" cy="90" r="76" fill="none"
                stroke={gradeColor} strokeWidth="14"
                strokeDasharray={2 * Math.PI * 76}
                strokeDashoffset={2 * Math.PI * 76 * (1 - pct / 100)}
                strokeLinecap="round"
                style={{ transition: 'stroke-dashoffset 1.5s ease, stroke 0.5s ease' }}
              />
            </svg>
            <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ fontSize: 52, fontWeight: 900, color: gradeColor, lineHeight: 1 }}>{grade}</div>
              <div style={{ fontSize: 14, color: 'var(--text-muted)', marginTop: 4 }}>{pct}/100</div>
            </div>
          </div>

          {/* Category breakdown */}
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 14 }}>
              Category Breakdown
            </div>
            {categories.map(cat => {
              const catPct = Math.round((cat.score / cat.max) * 100);
              return (
                <div key={cat.name} style={{ marginBottom: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontSize: 16 }}>{cat.icon}</span>
                    <span style={{ fontSize: 12, fontWeight: 600, flex: 1 }}>{cat.name}</span>
                    <span style={{ fontSize: 12, fontWeight: 800, color: cat.color }}>{cat.score}/{cat.max}</span>
                  </div>
                  <div className="progress-bar-bg" style={{ height: 6 }}>
                    <div className="progress-bar-fill" style={{ width: `${catPct}%`, background: cat.color }} />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Summary stats */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, flexShrink: 0 }}>
            <div style={{ textAlign: 'center', background: 'var(--bg-secondary)', borderRadius: 12, padding: '16px 24px', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Total Score</div>
              <div style={{ fontSize: 36, fontWeight: 900, color: gradeColor }}>{totalScore}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>out of {maxScore}</div>
            </div>
            <div style={{ textAlign: 'center', background: 'rgba(239,68,68,0.05)', borderRadius: 12, padding: '12px 24px', border: '1px solid rgba(239,68,68,0.2)' }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Issues Found</div>
              <div style={{ fontSize: 32, fontWeight: 900, color: 'var(--red)' }}>{issueCount}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Category Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 12 }}>
        {categories.map(cat => (
          <div key={cat.name} className="glass-card" style={{ padding: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
              <span style={{ fontSize: 24 }}>{cat.icon}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 700 }}>{cat.name}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{cat.score}/{cat.max} points</div>
              </div>
              <div style={{
                width: 48, height: 48, borderRadius: '50%',
                background: `${cat.color}22`,
                border: `2px solid ${cat.color}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 14, fontWeight: 800, color: cat.color
              }}>
                {Math.round((cat.score / cat.max) * 100)}%
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {cat.issues.map((issue, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  {issue.severity === 'ok' && <CheckCircle size={13} color="var(--green)" style={{ flexShrink: 0 }} />}
                  {issue.severity === 'warn' && <AlertTriangle size={13} color="var(--yellow)" style={{ flexShrink: 0 }} />}
                  {issue.severity === 'fail' && <XCircle size={13} color="var(--red)" style={{ flexShrink: 0 }} />}
                  <span style={{ fontSize: 11, color: 'var(--text-secondary)', flex: 1, lineHeight: 1.4 }}>{issue.msg}</span>
                  {issue.fix && (
                    <button className="tool-btn" style={{ fontSize: 10, padding: '3px 8px' }}>{issue.fix}</button>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
