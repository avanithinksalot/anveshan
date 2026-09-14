import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AnveshanLogo } from '../components/AnveshanLogo';

const ROLES = [
  { key: 'ministry',           path: '/ministry',    emoji: '🏛️', title: 'Ministry Level',        scope: 'National Overview (All India)',           accent: '#138808' },
  { key: 'state_nodal',        path: '/state-nodal', emoji: '🏢', title: 'State Nodal Authority', scope: 'State-Level Monitoring',                  accent: '#DC6B00' },
  { key: 'district_authority', path: '/da',          emoji: '📍', title: 'District Authority / IDA', scope: 'District Case Queue',                  accent: '#B91C1C' },
  { key: 'mp',                 path: '/mp',          emoji: '👤', title: 'Member of Parliament',   scope: 'Constituency Portfolio Self-Verification', accent: '#B45309' },
  { key: 'auditor',            path: '/auditor',     emoji: '🔍', title: 'Auditor / CAG',          scope: 'Ground-Truth Active Learning Loop',       accent: '#166534' },
];

const DEMO_CREDS: Record<string, string> = {
  ministry: 'min2026', state_nodal: 'sna2026',
  district_authority: 'da2026', mp: 'mp2026', auditor: 'cag2026',
};


export function LoginView() {
  const nav = useNavigate();
  const [selectedRole, setSelectedRole] = useState<string | null>(null);
  const [username, setUsername]         = useState('');
  const [password, setPassword]         = useState('');
  const [error, setError]               = useState('');
  const [loading, setLoading]           = useState(false);

  const roleObj = ROLES.find((r) => r.key === selectedRole);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!selectedRole)      { setError('Please select a role above.'); return; }
    if (!username.trim())   { setError('Username is required.'); return; }
    if (!password.trim())   { setError('Password is required.'); return; }
    if (password.length < 4){ setError('Password must be at least 4 characters.'); return; }

    setLoading(true);
    sessionStorage.setItem('anveshan_role', selectedRole);
    setTimeout(() => nav(roleObj!.path), 500);
  };

  return (
    <div className="min-h-screen bg-panel flex flex-col items-center justify-center px-4 py-12">

      {/* ── Card ────────────────────────────────────────────── */}
      <div className="w-full max-w-md rounded-2xl border border-edge bg-white shadow-lg overflow-hidden">

        {/* Tricolor top stripe */}
        <div className="flex h-1.5 w-full">
          <div className="flex-1 bg-[#FF9933]" />
          <div className="flex-1 bg-white border-x border-edge/30" />
          <div className="flex-1 bg-[#138808]" />
        </div>

        <div className="px-5 py-6 sm:px-8 sm:py-8">

          {/* Logo + brand */}
          <div className="flex flex-col items-center mb-5">
            <AnveshanLogo size={130} />
            <div className="mt-3 font-mono text-[10px] uppercase tracking-widest text-mut text-center">
              MPLADS Anomaly Detection Console
            </div>
            {/* Sanskrit tagline */}
            <div className="mt-3 flex flex-col items-center gap-0.5">
              <span className="font-serif text-[16px] font-semibold text-[#138808] tracking-wide">
                योगः कर्मसु कौशलम्।
              </span>
              <span className="font-mono text-[9px] text-mut tracking-widest uppercase">
                Excellence through disciplined action
              </span>
            </div>
          </div>

          {/* Divider */}
          <div className="mb-6 h-px bg-edge" />

          <form onSubmit={handleSubmit}>

            {/* Role selector */}
            <div className="mb-5">
              <div className="mb-2 font-mono text-[9px] uppercase tracking-widest text-sub font-bold">
                Select Access Role
              </div>
              <div className="space-y-1">
                {ROLES.map((r) => {
                  const active = selectedRole === r.key;
                  return (
                    <button
                      key={r.key}
                      type="button"
                      onClick={() => { setSelectedRole(r.key); setError(''); }}
                      className="flex w-full items-center gap-3 rounded-lg border px-3.5 py-2.5 text-left transition-all duration-100 focus:outline-none"
                      style={active
                        ? { borderColor: r.accent, background: r.accent + '0D', boxShadow: `inset 3px 0 0 ${r.accent}` }
                        : { borderColor: '#B8CEB8', background: 'transparent' }
                      }
                    >
                      <span className="text-[16px] shrink-0">{r.emoji}</span>
                      <div className="flex-1 min-w-0">
                        <div className="text-[12px] font-semibold leading-tight"
                          style={{ color: active ? r.accent : '#0C190C' }}>
                          {r.title}
                        </div>
                        <div className="font-mono text-[10px] text-mut leading-tight mt-0.5">{r.scope}</div>
                      </div>
                      {active && (
                        <span className="shrink-0 h-2 w-2 rounded-full" style={{ background: r.accent }} />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Credentials */}
            <div className="space-y-3 mb-4">
              <div>
                <label className="block font-mono text-[9px] uppercase tracking-widest text-sub font-bold mb-1.5">
                  Username
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => { setUsername(e.target.value); setError(''); }}
                  placeholder="Enter your username"
                  autoComplete="username"
                  className="w-full rounded-lg border border-edge bg-base px-3.5 py-2.5 font-mono text-[13px] text-fg placeholder:text-mut focus:border-[#138808] focus:outline-none focus:ring-2 focus:ring-[#138808]/20 transition-colors"
                />
              </div>
              <div>
                <label className="block font-mono text-[9px] uppercase tracking-widest text-sub font-bold mb-1.5">
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => { setPassword(e.target.value); setError(''); }}
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  className="w-full rounded-lg border border-edge bg-base px-3.5 py-2.5 font-mono text-[13px] text-fg placeholder:text-mut focus:border-[#138808] focus:outline-none focus:ring-2 focus:ring-[#138808]/20 transition-colors"
                />
              </div>
            </div>

            {error && (
              <div className="mb-3 rounded-lg border border-tier-high/40 bg-tier-high/8 px-3 py-2 font-mono text-[11px] text-tier-high">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-[#138808] px-4 py-3 font-mono text-[13px] font-bold text-white transition-opacity hover:opacity-90 disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-[#138808]/40"
            >
              {loading ? 'Signing in…' : 'Sign In →'}
            </button>
          </form>

          {/* Demo hint */}
          <div className="mt-4 rounded-lg border border-edge bg-panel px-3.5 py-2.5">
            <div className="font-mono text-[9px] uppercase tracking-widest text-mut mb-1">
              Demo Credentials
            </div>
            <div className="font-mono text-[11px] text-sub">
              Username: <span className="text-fg font-semibold">any value</span>
              {'  ·  '}Password:{' '}
              {selectedRole
                ? <span className="font-bold text-fg">{DEMO_CREDS[selectedRole]}</span>
                : <span className="italic text-mut">select a role above</span>
              }
            </div>
          </div>
        </div>

        {/* Bottom tricolor stripe */}
        <div className="flex h-1 w-full">
          <div className="flex-1 bg-[#FF9933]" />
          <div className="flex-1 bg-white border-x border-edge/30" />
          <div className="flex-1 bg-[#138808]" />
        </div>
      </div>

      <div className="mt-5 font-mono text-[9px] text-mut text-center">
        SIH 2026 · PS-26102 · MoSPI · ANVESHAN v1.0
      </div>
    </div>
  );
}
