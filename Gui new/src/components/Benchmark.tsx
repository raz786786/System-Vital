import { useState, useEffect, useRef } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, RadarChart, Radar, PolarGrid, PolarAngleAxis } from 'recharts';
import { Rocket, Play, RefreshCw, TrendingUp, Cpu, HardDrive, MemoryStick, Monitor } from 'lucide-react';

interface BenchScore {
  cpu: number; gpu: number; ram: number; disk: number; overall: number;
}

const historicalData = [
  { date: 'Jan 2025', overall: 1820, cpu: 1240, gpu: 890, ram: 2100, disk: 340 },
  { date: 'Feb 2025', overall: 1795, cpu: 1220, gpu: 880, ram: 2090, disk: 320 },
  { date: 'Mar 2025', overall: 1830, cpu: 1250, gpu: 910, ram: 2130, disk: 355 },
  { date: 'Apr 2025', overall: 1810, cpu: 1230, gpu: 895, ram: 2110, disk: 348 },
];

const ratings = [
  { label: 'CPU', score: 58, max: 100, color: 'var(--accent)', icon: Cpu },
  { label: 'GPU', score: 32, max: 100, color: 'var(--cyan)', icon: Monitor },
  { label: 'RAM', score: 71, max: 100, color: 'var(--purple)', icon: MemoryStick },
  { label: 'Disk', score: 24, max: 100, color: 'var(--orange)', icon: HardDrive },
];

const radarData = [
  { subject: 'CPU', A: 58 },
  { subject: 'GPU', A: 32 },
  { subject: 'RAM', A: 71 },
  { subject: 'Disk', A: 24 },
  { subject: 'Network', A: 65 },
  { subject: 'Thermal', A: 78 },
];

function AnimatedValue({ target, suffix = '' }: { target: number; suffix?: string }) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    let start = 0;
    const step = target / 60;
    const iv = setInterval(() => {
      start += step;
      if (start >= target) { setVal(target); clearInterval(iv); }
      else setVal(Math.round(start));
    }, 16);
    return () => clearInterval(iv);
  }, [target]);
  return <span>{val.toLocaleString()}{suffix}</span>;
}

export default function Benchmark() {
  const [running, setRunning] = useState(false);
  const [phase, setPhase] = useState('');
  const [progress, setProgress] = useState(0);
  const [scores, setScores] = useState<BenchScore | null>(null);
  const [activeTab, setActiveTab] = useState<'run' | 'history' | 'stress'>('run');
  const [novaText, setNovaText] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [stressTarget, setStressTarget] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const phases = ['Initializing…', 'CPU Benchmark…', 'GPU Benchmark…', 'RAM Bandwidth Test…', 'Disk I/O Test…', 'Calculating Score…'];

  const runBenchmark = () => {
    setRunning(true);
    setScores(null);
    setProgress(0);
    let p = 0;
    let phaseIdx = 0;
    setPhase(phases[0]);
    intervalRef.current = setInterval(() => {
      p += 100 / (phases.length * 12);
      if (p >= ((phaseIdx + 1) / phases.length) * 100) {
        phaseIdx = Math.min(phaseIdx + 1, phases.length - 1);
        setPhase(phases[phaseIdx]);
      }
      if (p >= 100) {
        if (intervalRef.current) clearInterval(intervalRef.current);
        setProgress(100);
        setRunning(false);
        setScores({ cpu: 1247, gpu: 892, ram: 2134, disk: 342, overall: 1829 });
      } else {
        setProgress(Math.round(p));
      }
    }, 120);
  };

  const handleAnalyze = () => {
    if (!novaText.trim() && !scores) return;
    setAnalyzing(true);
    setTimeout(() => {
      setNovaText(`📊 **Benchmark Analysis Complete**

**CPU Score: ${scores?.cpu ?? 'N/A'}** — Your Intel i7-6500U scores below average for modern workloads. Consider limiting background processes during gaming.

**GPU Score: ${scores?.gpu ?? 'N/A'}** — AMD Radeon R5 M335 is an entry-level GPU from 2015. Expect 720p gaming at low settings in most titles.

**RAM Score: ${scores?.ram ?? 'N/A'}** — DDR3 2133MHz is adequate. Dual-channel configuration recommended for better bandwidth.

**Disk Score: ${scores?.disk ?? 'N/A'}** — HDD detected. Upgrading to an SSD would improve boot time by 5-8x and overall responsiveness significantly.

**Recommendations:**
• 🔴 Priority: Replace HDD with SSD (biggest impact)
• 🟡 Consider adding 4GB RAM to reach 16GB
• 🟢 CPU/GPU are within expected range for age`);
      setAnalyzing(false);
    }, 2200);
  };

  const runStress = (target: string) => {
    setStressTarget(target);
    setTimeout(() => setStressTarget(null), 5000);
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: '8px 12px', fontSize: 12 }}>
        <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>{label}</div>
        {payload.map((p: any) => (
          <div key={p.dataKey} style={{ color: p.fill }}>{p.name}: {p.value.toLocaleString()}</div>
        ))}
      </div>
    );
  };

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800 }}>Performance Benchmarks</h1>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>Measure, compare, and stress test your hardware</p>
        </div>
        <div className="tab-bar">
          {([['run', '🚀 Run Benchmark'], ['history', '📈 History'], ['stress', '🔥 Stress Test']] as const).map(([k, lbl]) => (
            <div key={k} className={`tab-item ${activeTab === k ? 'active' : ''}`} onClick={() => setActiveTab(k)}>{lbl}</div>
          ))}
        </div>
      </div>

      {activeTab === 'run' && (
        <>
          {/* Launch Card */}
          <div className="glass-card" style={{ padding: 24 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                <div style={{ background: 'rgba(59,130,246,0.15)', borderRadius: 12, padding: 12 }}>
                  <Rocket size={28} color="var(--accent)" />
                </div>
                <div>
                  <div style={{ fontSize: 16, fontWeight: 700 }}>Full System Benchmark</div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>Tests CPU, GPU, RAM bandwidth, and disk I/O sequentially</div>
                </div>
              </div>
              <button className="btn-primary" onClick={runBenchmark} disabled={running} style={{ minWidth: 160 }}>
                {running ? <><RefreshCw size={14} className="spinner" />Running…</> : <><Play size={14} />Launch Benchmark</>}
              </button>
            </div>

            {running && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 12, color: 'var(--text-secondary)' }}>
                  <span>{phase}</span>
                  <span>{progress}%</span>
                </div>
                <div className="progress-bar-bg" style={{ height: 8 }}>
                  <div className="progress-bar-fill" style={{ width: `${progress}%`, background: 'var(--accent)', transition: 'width 0.1s linear' }} />
                </div>
              </div>
            )}

            {scores && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginTop: running ? 16 : 0 }}>
                <div style={{
                  gridColumn: 'span 5', background: 'var(--bg-secondary)', borderRadius: 10, padding: 20,
                  textAlign: 'center', border: '1px solid var(--accent)', boxShadow: '0 0 20px var(--accent-glow)'
                }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>Overall Score</div>
                  <div style={{ fontSize: 52, fontWeight: 900, color: 'var(--accent)', margin: '4px 0' }}>
                    <AnimatedValue target={scores.overall} />
                  </div>
                  <span className="badge badge-yellow">ENTRY TIER</span>
                </div>
                {ratings.map(r => {
                  const Icon = r.icon;
                  const scoreKey = r.label.toLowerCase() as keyof BenchScore;
                  return (
                    <div key={r.label} style={{ background: 'var(--bg-secondary)', borderRadius: 10, padding: 16, textAlign: 'center', border: '1px solid var(--border)' }}>
                      <Icon size={20} color={r.color} style={{ margin: '0 auto 8px' }} />
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>{r.label}</div>
                      <div style={{ fontSize: 24, fontWeight: 800, color: r.color }}>
                        <AnimatedValue target={scores[scoreKey]} />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Ratings bars */}
          {scores && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              {/* Performance Radar */}
              <div className="glass-card" style={{ padding: 20 }}>
                <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 14 }}>Performance Radar</div>
                <ResponsiveContainer width="100%" height={200}>
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="var(--border)" />
                    <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                    <Radar name="Score" dataKey="A" stroke="var(--accent)" fill="var(--accent)" fillOpacity={0.2} strokeWidth={2} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>

              {/* Category bars */}
              <div className="glass-card" style={{ padding: 20 }}>
                <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 14 }}>Score Breakdown vs Average</div>
                {ratings.map(r => (
                  <div key={r.label} style={{ marginBottom: 14 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 12 }}>
                      <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>{r.label}</span>
                      <span style={{ color: r.color, fontWeight: 700 }}>{r.score}/100</span>
                    </div>
                    <div className="progress-bar-bg" style={{ height: 8 }}>
                      <div className="progress-bar-fill" style={{ width: `${r.score}%`, background: r.color }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* AI Analysis */}
          <div className="glass-card" style={{ padding: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
              <span style={{ background: 'var(--purple)', color: 'white', borderRadius: 6, padding: '2px 8px', fontSize: 11, fontWeight: 700 }}>NOVA AI</span>
              <span style={{ fontSize: 13, fontWeight: 700 }}>Benchmark Analysis</span>
            </div>
            {!novaText.includes('Analysis Complete') && (
              <textarea
                placeholder="Paste benchmark results here or run the benchmark above, then click Analyze…"
                value={novaText}
                onChange={e => setNovaText(e.target.value)}
                style={{ minHeight: 80, resize: 'vertical', marginBottom: 10 }}
              />
            )}
            {novaText.includes('Analysis Complete') ? (
              <div style={{ background: 'var(--bg-secondary)', borderRadius: 8, padding: 16, fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.8, whiteSpace: 'pre-wrap', border: '1px solid var(--border)' }}>
                {novaText}
              </div>
            ) : null}
            <button className="btn-purple" onClick={handleAnalyze} disabled={analyzing} style={{ marginTop: 10 }}>
              {analyzing ? <><RefreshCw size={14} className="spinner" />Analyzing…</> : <>✨ Analyze with Amazon Nova AI</>}
            </button>
          </div>
        </>
      )}

      {activeTab === 'history' && (
        <div className="glass-card" style={{ padding: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
            <TrendingUp size={16} color="var(--accent)" />
            <span style={{ fontSize: 13, fontWeight: 700 }}>Historical Benchmark Comparison</span>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={historicalData} margin={{ left: -10 }}>
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="overall" name="Overall" fill="var(--accent)" radius={[4, 4, 0, 0]} />
              <Bar dataKey="cpu" name="CPU" fill="var(--purple)" radius={[4, 4, 0, 0]} />
              <Bar dataKey="disk" name="Disk" fill="var(--orange)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <div style={{ marginTop: 20 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Run History</div>
            {historicalData.map((d, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0', borderBottom: i < historicalData.length - 1 ? '1px solid var(--border)' : 'none' }}>
                <span style={{ fontSize: 12, color: 'var(--text-muted)', minWidth: 80 }}>{d.date}</span>
                <div style={{ flex: 1, display: 'flex', gap: 20 }}>
                  {['overall', 'cpu', 'gpu', 'ram', 'disk'].map(k => (
                    <div key={k}>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{k}</div>
                      <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>{(d as any)[k]}</div>
                    </div>
                  ))}
                </div>
                <span className="badge badge-blue">Saved</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'stress' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {[
            { id: 'cpu_stress', label: 'CPU Stress Test', desc: 'Max load across all cores for thermal testing', icon: '🔥', color: 'var(--red)' },
            { id: 'ram_stress', label: 'RAM Stress Test', desc: 'Memory integrity check & bandwidth stress', icon: '🧠', color: 'var(--purple)' },
            { id: 'gpu_stress', label: 'GPU Stress Test', desc: 'FurMark-style GPU load test', icon: '🎮', color: 'var(--cyan)' },
            { id: 'disk_stress', label: 'Disk I/O Stress', desc: 'Sequential & random read/write test', icon: '💾', color: 'var(--orange)' },
          ].map(s => (
            <div key={s.id} className="glass-card" style={{ padding: 24 }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>{s.icon}</div>
              <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 6 }}>{s.label}</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16, lineHeight: 1.5 }}>{s.desc}</div>
              {stressTarget === s.id ? (
                <>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6 }}>
                    <span>Stress Running…</span>
                    <span style={{ color: 'var(--red)', fontWeight: 700 }}>LIVE</span>
                  </div>
                  <div className="progress-bar-bg" style={{ height: 8, marginBottom: 12 }}>
                    <div style={{ height: '100%', borderRadius: 4, background: s.color, width: '100%', animation: 'shimmer 1.5s infinite', backgroundSize: '200% 100%', backgroundImage: `linear-gradient(90deg, ${s.color} 25%, ${s.color}88 50%, ${s.color} 75%)` }} />
                  </div>
                </>
              ) : null}
              <button
                onClick={() => runStress(s.id)}
                disabled={stressTarget !== null}
                style={{
                  width: '100%', padding: '10px', borderRadius: 8,
                  background: stressTarget === s.id ? `${s.color}22` : s.color,
                  color: stressTarget === s.id ? s.color : 'white',
                  border: `1px solid ${stressTarget === s.id ? s.color : 'transparent'}`,
                  fontSize: 13, fontWeight: 700, cursor: 'pointer', transition: 'all 0.2s',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8
                }}
              >
                {stressTarget === s.id ? <><RefreshCw size={14} className="spinner" />Running…</> : <><Play size={14} />Start Stress Test</>}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
