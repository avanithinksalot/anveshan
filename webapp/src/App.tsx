import { useNavigate, Navigate, Route, Routes } from 'react-router-dom';
import { AnveshanLogo } from './components/AnveshanLogo';
import { AuditorView } from './views/AuditorView';
import { DAView } from './views/DAView';
import { LoginView } from './views/LoginView';
import { MinistryView } from './views/MinistryView';
import { MPView } from './views/MPView';
import { StateNodalView } from './views/StateNodalView';

const ROLE_META: Record<string, { label: string; badge: string; accent: string }> = {
  ministry:          { label: 'Ministry Level',          badge: 'MoSPI — National Scope',       accent: '#138808' },
  state_nodal:       { label: 'State Nodal Authority',   badge: 'State Level Monitoring',        accent: '#DC6B00' },
  district_authority:{ label: 'District Authority / IDA',badge: 'District Case Queue',           accent: '#B91C1C' },
  mp:                { label: 'Member of Parliament',    badge: 'Constituency Portfolio',         accent: '#B45309' },
  auditor:           { label: 'Auditor / CAG',           badge: 'Cross-Cutting Audit',           accent: '#166534' },
};

function Topnav({ title, pill }: { title: string; pill: string }) {
  const nav = useNavigate();
  const roleKey = sessionStorage.getItem('anveshan_role') ?? '';
  const meta = ROLE_META[roleKey];

  return (
    <header className="sticky top-0 z-30 border-b border-edge bg-panel shadow-sm">
      <div className="flex h-12 items-center gap-4 px-5">
        {/* Brand */}
        <button
          onClick={() => nav('/login')}
          className="flex items-center gap-2 shrink-0 hover:opacity-80 transition-opacity"
          title="Back to role selection"
        >
          <AnveshanLogo size={34} />
          <span className="font-bold text-[13px] text-fg tracking-wide">ANVESHAN</span>
        </button>

        <div className="h-5 w-px bg-edge shrink-0" />

        {/* Page title */}
        <div className="min-w-0 flex-1">
          <span className="text-[13px] font-semibold text-fg truncate">{title}</span>
        </div>

        {/* Pill */}
        <span className="rounded border border-[#DC6B00]/50 bg-[#DC6B00]/8 px-2.5 py-0.5 font-mono text-[10px] text-[#DC6B00] font-semibold whitespace-nowrap shrink-0">
          {pill}
        </span>

        {/* Role badge */}
        {meta && (
          <span
            className="rounded border px-2.5 py-0.5 font-mono text-[10px] font-semibold whitespace-nowrap shrink-0"
            style={{ color: meta.accent, borderColor: meta.accent + '50', background: meta.accent + '10' }}
          >
            {meta.label}
          </span>
        )}
      </div>
    </header>
  );
}

function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col min-h-screen bg-base text-fg">
      {children}
    </div>
  );
}

function RequireRole({ children }: { children: React.ReactNode }) {
  const role = sessionStorage.getItem('anveshan_role');
  if (!role) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function View({ title, pill, content }: { title: string; pill: string; content: React.ReactNode }) {
  return (
    <AppShell>
      <Topnav title={title} pill={pill} />
      <main className="flex-1 px-6 py-5 overflow-x-auto">{content}</main>
    </AppShell>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<AppShell><LoginView /></AppShell>} />

      <Route path="/da" element={
        <RequireRole>
          <View
            title="District Authority — Case Queue & SHAP Audit"
            pill="DISTRICT: BAREILLY · UTTAR PRADESH"
            content={<DAView topbar={null} />}
          />
        </RequireRole>
      } />

      <Route path="/ministry" element={
        <RequireRole>
          <View
            title="Ministry — National Risk Overview & MP↔IDA Network"
            pill="SCOPE: MoSPI (MINISTRY OF STATISTICS)"
            content={<MinistryView topbar={null} />}
          />
        </RequireRole>
      } />

      <Route path="/state-nodal" element={
        <RequireRole>
          <View
            title="State Nodal — Multi-District Drill-Down"
            pill="SCOPE: STATE NODAL DEPT"
            content={<StateNodalView topbar={null} />}
          />
        </RequireRole>
      } />

      <Route path="/mp" element={
        <RequireRole>
          <View
            title="Member of Parliament — Portfolio Transparency"
            pill="MP: SHRI HARDEEP SINGH PURI · 2020–26"
            content={<MPView topbar={null} />}
          />
        </RequireRole>
      } />

      <Route path="/auditor" element={
        <RequireRole>
          <View
            title="Auditor Console — Ground-Truth Active Learning Loop"
            pill="AUDIT FEEDBACK STORE · POSTGRES"
            content={<AuditorView topbar={null} />}
          />
        </RequireRole>
      } />

      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
