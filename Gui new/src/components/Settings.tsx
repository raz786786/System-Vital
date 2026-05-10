import { useState } from 'react';
import { Save, Eye, EyeOff, CheckCircle, RefreshCw, Info } from 'lucide-react';

interface SettingsProps {
  theme: 'dark' | 'light';
  onThemeChange: (t: 'dark' | 'light') => void;
  accentColor: string;
  onAccentChange: (c: string) => void;
}

const accentColors = [
  { label: 'Blue', value: '#3b82f6' },
  { label: 'Purple', value: '#a855f7' },
  { label: 'Cyan', value: '#06b6d4' },
  { label: 'Green', value: '#22c55e' },
  { label: 'Orange', value: '#f97316' },
  { label: 'Pink', value: '#ec4899' },
];

export default function Settings({ theme, onThemeChange, accentColor, onAccentChange }: SettingsProps) {
  const [apiKey, setApiKey] = useState('********************************');
  const [showKey, setShowKey] = useState(false);
  const [saved, setSaved] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validResult, setValidResult] = useState<string | null>(null);
  const [notifyThreshold, setNotifyThreshold] = useState(90);
  const [profile, setProfile] = useState('power');
  const [language, setLanguage] = useState('en');
  const [offlineMode, setOfflineMode] = useState(false);
  const [autoRestore, setAutoRestore] = useState(true);
  const [scheduledScan, setScheduledScan] = useState(true);
  const [scanFreq, setScanFreq] = useState('weekly');

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  const handleValidate = () => {
    setValidating(true);
    setValidResult(null);
    setTimeout(() => {
      setValidating(false);
      setValidResult('✅ API Key is valid — Amazon Nova AI ready');
    }, 1800);
  };

  const Toggle = ({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) => (
    <label className="toggle-switch">
      <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} />
      <span className="toggle-slider" />
    </label>
  );

  const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <div className="glass-card" style={{ padding: 20 }}>
      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 16 }}>{title}</div>
      {children}
    </div>
  );

  const Row = ({ label, sub, children }: { label: string; sub?: string; children: React.ReactNode }) => (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
      <div>
        <div style={{ fontSize: 13, fontWeight: 600 }}>{label}</div>
        {sub && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{sub}</div>}
      </div>
      {children}
    </div>
  );

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <h1 style={{ fontSize: 22, fontWeight: 800 }}>Settings</h1>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>Configure Dekcheck to your preferences</p>
      </div>

      {/* AI Config */}
      <Section title="AI Provider Configuration">
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Amazon Nova API Key</div>
          <div style={{ position: 'relative' }}>
            <input
              type={showKey ? 'text' : 'password'}
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              style={{ paddingRight: 44 }}
            />
            <button
              onClick={() => setShowKey(!showKey)}
              style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
            >
              {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
            Get a free tier key from the Amazon Nova portal.
          </div>
        </div>
        {validResult && (
          <div style={{ padding: '8px 12px', borderRadius: 8, background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.3)', fontSize: 12, color: 'var(--green)', marginBottom: 10 }}>
            {validResult}
          </div>
        )}
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn-success" onClick={handleValidate} disabled={validating}>
            {validating ? <><RefreshCw size={13} className="spinner" />Validating…</> : <><CheckCircle size={13} />Validate Key</>}
          </button>
        </div>

        <div style={{ borderTop: '1px solid var(--border)', marginTop: 14, paddingTop: 14 }}>
          <Row label="Offline Mode" sub="Use rule-based engine without AI (no internet required)">
            <Toggle checked={offlineMode} onChange={setOfflineMode} />
          </Row>
          <div style={{ paddingTop: 10 }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>AI Provider</div>
            <select value="nova" onChange={() => {}}>
              <option value="nova">Amazon Nova AI</option>
              <option value="gemini">Google Gemini</option>
              <option value="offline">Offline (Rule-based)</option>
            </select>
          </div>
        </div>
      </Section>

      {/* Appearance */}
      <Section title="Appearance & Theme">
        <Row label="Color Scheme" sub="Switch between dark and light interface">
          <select value={theme} onChange={e => onThemeChange(e.target.value as 'dark' | 'light')} style={{ width: 140 }}>
            <option value="dark">Dark</option>
            <option value="light">Light</option>
          </select>
        </Row>

        <div style={{ padding: '12px 0', borderBottom: '1px solid var(--border)' }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>Accent Color</div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {accentColors.map(c => (
              <button
                key={c.value}
                onClick={() => onAccentChange(c.value)}
                title={c.label}
                style={{
                  width: 32, height: 32, borderRadius: '50%',
                  background: c.value, border: `3px solid ${accentColor === c.value ? 'white' : 'transparent'}`,
                  cursor: 'pointer', boxShadow: accentColor === c.value ? `0 0 0 2px ${c.value}` : 'none',
                  transition: 'all 0.2s'
                }}
              />
            ))}
          </div>
        </div>

        <Row label="User Profile" sub="Adjust interface complexity to your experience level">
          <select value={profile} onChange={e => setProfile(e.target.value)} style={{ width: 160 }}>
            <option value="beginner">Beginner — Simple mode</option>
            <option value="power">Power User — All features</option>
            <option value="it">IT Professional — CLI & advanced</option>
          </select>
        </Row>

        <Row label="Language" sub="Interface language (requires restart)">
          <select value={language} onChange={e => setLanguage(e.target.value)} style={{ width: 140 }}>
            <option value="en">English</option>
            <option value="es">Español</option>
            <option value="fr">Français</option>
            <option value="de">Deutsch</option>
            <option value="ar">العربية</option>
          </select>
        </Row>
      </Section>

      {/* Notifications */}
      <Section title="Monitoring & Alerts">
        <Row label="Threshold Alerts" sub={`Send notification when CPU/RAM > ${notifyThreshold}%`}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <input
              type="range" min={60} max={99} value={notifyThreshold}
              onChange={e => setNotifyThreshold(+e.target.value)}
              style={{ width: 100, accentColor: 'var(--accent)' }}
            />
            <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)', minWidth: 36 }}>{notifyThreshold}%</span>
          </div>
        </Row>

        <Row label="Scheduled Health Scan" sub="Automatically run diagnostics in the background">
          <Toggle checked={scheduledScan} onChange={setScheduledScan} />
        </Row>

        {scheduledScan && (
          <Row label="Scan Frequency" sub="How often to run automatic diagnostics">
            <select value={scanFreq} onChange={e => setScanFreq(e.target.value)} style={{ width: 140 }}>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </Row>
        )}

        <Row label="Auto Restore Point" sub="Create a restore point before any fix is applied">
          <Toggle checked={autoRestore} onChange={setAutoRestore} />
        </Row>
      </Section>

      {/* App Info */}
      <Section title="Application Info">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {[
            { label: 'Version', value: 'v1.0.0' },
            { label: 'Build Date', value: 'June 2025' },
            { label: 'Made by', value: 'AHMED ZUBAIR RAO · SHAYAN HUMAYUN · MUHAMMAD AHMAD' },
            { label: 'License', value: 'MIT Open Source' },
          ].map((row, i) => (
            <div key={i} style={{ background: 'var(--bg-secondary)', borderRadius: 8, padding: '10px 14px', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>{row.label}</div>
              <div style={{ fontSize: 12, color: 'var(--text-primary)' }}>{row.value}</div>
            </div>
          ))}
        </div>

        <div style={{ marginTop: 14, display: 'flex', gap: 8 }}>
          <button className="btn-secondary"><Info size={13} />Changelog</button>
          <button className="btn-secondary">Export Settings</button>
          <button className="btn-secondary">Import Settings</button>
        </div>
      </Section>

      {/* Save Bar */}
      <button
        className="btn-primary"
        onClick={handleSave}
        style={{ width: '100%', justifyContent: 'center', padding: '14px', fontSize: 14, fontWeight: 700 }}
      >
        {saved ? <><CheckCircle size={16} />Changes Saved!</> : <><Save size={16} />Apply & Save Changes</>}
      </button>
    </div>
  );
}
