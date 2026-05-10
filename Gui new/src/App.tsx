import { useState, useEffect } from 'react';
import {
  LayoutDashboard, Stethoscope, Zap, Wrench, Wifi,
  Heart, Settings as SettingsIcon, ChevronLeft, ChevronRight,
  Sun, Moon, AlertCircle
} from 'lucide-react';
import Dashboard from './components/Dashboard';
import Diagnostics from './components/Diagnostics';
import Benchmark from './components/Benchmark';
import Utilities from './components/Utilities';
import NetworkSuite from './components/NetworkSuite';
import HealthScore from './components/HealthScore';
import Settings from './components/Settings';

type Tab = 'dashboard' | 'diagnostics' | 'benchmark' | 'utilities' | 'network' | 'health' | 'settings';

const navItems: { id: Tab; label: string; Icon: any; badge?: string }[] = [
  { id: 'dashboard', label: 'Dashboard', Icon: LayoutDashboard },
  { id: 'diagnostics', label: 'Diagnostics', Icon: Stethoscope, badge: '3' },
  { id: 'benchmark', label: 'Benchmark', Icon: Zap },
  { id: 'utilities', label: 'Utilities', Icon: Wrench, badge: '50+' },
  { id: 'network', label: 'Network Suite', Icon: Wifi },
  { id: 'health', label: 'Health Score', Icon: Heart },
  { id: 'settings', label: 'Settings', Icon: SettingsIcon },
];

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [accentColor, setAccentColor] = useState('#3b82f6');
  const [collapsed, setCollapsed] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  useEffect(() => {
    // Update CSS accent variable
    document.documentElement.style.setProperty('--accent', accentColor);
    document.documentElement.style.setProperty('--accent-hover', accentColor + 'cc');
    document.documentElement.style.setProperty('--accent-glow', accentColor + '26');
  }, [accentColor]);

  // Simulate thermal alert after 5s
  useEffect(() => {
    const t = setTimeout(() => {
      setNotification('⚠️ CPU temperature reached 78°C — Consider improving cooling');
      setTimeout(() => setNotification(null), 5000);
    }, 5000);
    return () => clearTimeout(t);
  }, []);

  const handleThemeChange = (t: 'dark' | 'light') => setTheme(t);
  const handleAccentChange = (c: string) => setAccentColor(c);

  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      width: '100vw',
      background: 'var(--bg-primary)',
      overflow: 'hidden',
      position: 'relative',
    }}>
      {/* Notification Toast */}
      {notification && (
        <div style={{
          position: 'fixed', top: 20, right: 20, zIndex: 999,
          background: 'var(--bg-card)', border: '1px solid var(--yellow)',
          borderRadius: 12, padding: '14px 18px', maxWidth: 380,
          boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
          display: 'flex', alignItems: 'center', gap: 10,
          animation: 'fadeIn 0.3s ease',
        }}>
          <AlertCircle size={18} color="var(--yellow)" style={{ flexShrink: 0 }} />
          <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>{notification}</span>
          <button onClick={() => setNotification(null)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', marginLeft: 'auto', fontSize: 18, lineHeight: 1 }}>
            ×
          </button>
        </div>
      )}

      {/* Sidebar */}
      <aside style={{
        width: collapsed ? 64 : 220,
        minWidth: collapsed ? 64 : 220,
        background: 'var(--bg-secondary)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        padding: '16px 10px',
        transition: 'width 0.25s ease, min-width 0.25s ease',
        overflow: 'hidden',
        position: 'relative',
        zIndex: 10,
      }}>
        {/* Logo */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10, marginBottom: 24,
          paddingLeft: collapsed ? 4 : 6, overflow: 'hidden',
          minHeight: 48,
        }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: 'linear-gradient(135deg, var(--accent), #6366f1)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 18, flexShrink: 0, boxShadow: '0 4px 14px var(--accent-glow)'
          }}>
            🔬
          </div>
          {!collapsed && (
            <div>
              <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '0.02em', lineHeight: 1.2 }}>
                DEKCHECK
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.06em' }}>
                DIAGNOSTIC TOOL
              </div>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
          {!collapsed && <div className="section-label" style={{ marginTop: 0 }}>MAIN</div>}
          {navItems.slice(0, 5).map(item => (
            <NavItem key={item.id} item={item} active={activeTab === item.id}
              collapsed={collapsed} onClick={() => setActiveTab(item.id)} />
          ))}
          {!collapsed && <div className="section-label">SYSTEM</div>}
          {navItems.slice(5).map(item => (
            <NavItem key={item.id} item={item} active={activeTab === item.id}
              collapsed={collapsed} onClick={() => setActiveTab(item.id)} />
          ))}
        </nav>

        {/* Bottom */}
        <div style={{ borderTop: '1px solid var(--border)', paddingTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
          {/* Theme toggle */}
          <button
            onClick={() => handleThemeChange(theme === 'dark' ? 'light' : 'dark')}
            style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '8px 10px', borderRadius: 8, border: '1px solid var(--border)',
              background: 'transparent', cursor: 'pointer', color: 'var(--text-secondary)',
              transition: 'all 0.2s', fontSize: 12, fontWeight: 500,
              justifyContent: collapsed ? 'center' : 'flex-start'
            }}
          >
            {theme === 'dark'
              ? <Sun size={16} color="var(--yellow)" />
              : <Moon size={16} color="var(--accent)" />}
            {!collapsed && <span>{theme === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>}
          </button>

          {/* Status */}
          {!collapsed && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px' }}>
              <div className="status-dot" style={{ background: 'var(--green)', boxShadow: '0 0 6px var(--green)' }} />
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>System Ready</span>
            </div>
          )}

          {!collapsed && (
            <div style={{ fontSize: 10, color: 'var(--text-muted)', padding: '0 10px 4px', textAlign: 'center' }}>v1.0.0</div>
          )}
        </div>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(c => !c)}
          style={{
            position: 'absolute', right: -12, top: '50%', transform: 'translateY(-50%)',
            width: 24, height: 24, borderRadius: '50%',
            background: 'var(--bg-card)', border: '1px solid var(--border)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer', color: 'var(--text-muted)', zIndex: 20,
            transition: 'all 0.2s'
          }}
        >
          {collapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
        </button>
      </aside>

      {/* Main Content */}
      <main style={{
        flex: 1,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        minWidth: 0,
      }}>
        {/* Top bar */}
        <div style={{
          height: 52,
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg-secondary)',
          display: 'flex',
          alignItems: 'center',
          padding: '0 20px',
          gap: 12,
          flexShrink: 0,
        }}>
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
              {navItems.find(n => n.id === activeTab)?.label}
            </span>
            <div style={{ height: 14, width: 1, background: 'var(--border)' }} />
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Dekcheck Hardware Diagnostic Tool
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '5px 12px', borderRadius: 20, background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.2)' }}>
              <div className="status-dot" style={{ background: 'var(--green)', boxShadow: '0 0 6px var(--green)' }} />
              <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--green)' }}>All Systems Normal</span>
            </div>
            <div style={{ padding: '5px 12px', borderRadius: 20, background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)', fontSize: 11, fontWeight: 600, color: 'var(--accent)' }}>
              Health: 67/100
            </div>
          </div>
        </div>

        {/* Scrollable content */}
        <div style={{ flex: 1, overflow: 'auto', padding: 20 }}>
          {activeTab === 'dashboard' && <Dashboard />}
          {activeTab === 'diagnostics' && <Diagnostics />}
          {activeTab === 'benchmark' && <Benchmark />}
          {activeTab === 'utilities' && <Utilities />}
          {activeTab === 'network' && <NetworkSuite />}
          {activeTab === 'health' && <HealthScore />}
          {activeTab === 'settings' && (
            <Settings
              theme={theme}
              onThemeChange={handleThemeChange}
              accentColor={accentColor}
              onAccentChange={handleAccentChange}
            />
          )}
        </div>
      </main>
    </div>
  );
}

function NavItem({ item, active, collapsed, onClick }: {
  item: { id: string; label: string; Icon: any; badge?: string };
  active: boolean; collapsed: boolean; onClick: () => void;
}) {
  const { Icon, label, badge } = item;
  return (
    <button
      onClick={onClick}
      title={collapsed ? label : undefined}
      style={{
        display: 'flex', alignItems: 'center',
        gap: collapsed ? 0 : 10,
        padding: collapsed ? '10px' : '10px 12px',
        borderRadius: 10, cursor: 'pointer',
        background: active ? 'var(--accent)' : 'transparent',
        border: active ? '1px solid var(--accent)' : '1px solid transparent',
        color: active ? 'white' : 'var(--text-secondary)',
        fontSize: 13, fontWeight: 500,
        transition: 'all 0.2s',
        width: '100%',
        justifyContent: collapsed ? 'center' : 'flex-start',
        boxShadow: active ? '0 4px 14px var(--accent-glow)' : 'none',
        position: 'relative',
      }}
      onMouseEnter={e => { if (!active) (e.currentTarget as HTMLElement).style.background = 'var(--bg-hover)'; }}
      onMouseLeave={e => { if (!active) (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
    >
      <Icon size={16} />
      {!collapsed && <span style={{ flex: 1, textAlign: 'left' }}>{label}</span>}
      {!collapsed && badge && (
        <span style={{
          background: active ? 'rgba(255,255,255,0.2)' : 'var(--accent)',
          color: active ? 'white' : 'white',
          borderRadius: 10, padding: '1px 7px', fontSize: 10, fontWeight: 700
        }}>{badge}</span>
      )}
      {collapsed && badge && (
        <span style={{
          position: 'absolute', top: 4, right: 4,
          background: 'var(--red)', borderRadius: '50%',
          width: 8, height: 8, display: 'block'
        }} />
      )}
    </button>
  );
}
