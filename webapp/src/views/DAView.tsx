import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { API_BASE, amt, apiFetch, esc, riskColor } from '../lib/api';
import type { ActionKind } from '../components/DetailPanel';
import { CaseModal } from '../components/CaseModal';
import type { AlertRow, AlertsResponse, AuditResponse, DashboardSummary, RiskResponse } from '../lib/types';
import { Banner, Empty, SortTh, Stat, StatusBadge, TierDot, descCell, idCell, tdNowrap } from '../components/UI';

const ALL_DISTRICTS = [
  'All Districts (National Queue)',
  'Bareilly',
  'Lucknow',
  'Varanasi',
  'Pune',
  'Patna',
  'Kolkata North',
  'Bhopal',
  'Jaipur',
  'Chennai South',
  'Ahmedabad East',
  'Bengaluru South',
  'New Delhi',
  'Thiruvananthapuram',
  'Ludhiana',
  'Bhubaneswar',
  'Guwahati',
];

export function DAView({ topbar }: { topbar: ReactNode }) {
  const [summary, setSummary]         = useState<DashboardSummary | null>(null);
  const [selectedIda, setSelectedIda] = useState<string>('All Districts (National Queue)');
  const [alerts, setAlerts]           = useState<AlertRow[]>([]);
  const [er, setEr]                   = useState<string | null>(null);
  const [q, setQ]                     = useState('');
  const [tier, setTier]               = useState('');
  const [sel, setSel]                 = useState<AlertRow | null>(null);
  const [detail, setDetail]           = useState<RiskResponse | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailErr, setDetailErr]     = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [actioned, setActioned]       = useState<Set<string>>(new Set());
  const [toast, setToast]             = useState<[string, boolean] | null>(null);
  const [sortField, setSortField]     = useState<string>('risk_score');
  const [sortDir, setSortDir]         = useState<'asc' | 'desc'>('desc');

  useEffect(() => {
    (async () => {
      try {
        const idaParam  = selectedIda.includes('All') ? '' : `&ida=${encodeURIComponent(selectedIda)}`;
        const tierParam = tier ? `&tier=${encodeURIComponent(tier)}` : '';
        const s  = await apiFetch<DashboardSummary>(`${API_BASE}/dashboard/summary?role=district_authority${idaParam}`);
        const al = await apiFetch<AlertsResponse>(`${API_BASE}/alerts?limit=500${idaParam}${tierParam}`);
        setSummary(s);
        setAlerts(al.alerts);
        if (al.alerts.length > 0) void select(al.alerts[0], false);
        try {
          const audit = await apiFetch<AuditResponse>(`${API_BASE}/audit/actions`);
          setActioned((prev) => {
            const next = new Set(prev);
            audit.actions.forEach((a) => next.add(a.work_id));
            return next;
          });
        } catch { /* optional */ }
      } catch (e) {
        setEr((e as Error).message);
      }
    })();
  }, [selectedIda, tier]);

  const handleSort = (field: string) => {
    if (sortField === field) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else { setSortField(field); setSortDir('desc'); }
  };

  const rows = useMemo(() => {
    const needle = q.toLowerCase().trim();
    const filtered = alerts.filter((a) => {
      if (tier && String(a.risk_tier ?? '').toLowerCase() !== tier.toLowerCase()) return false;
      if (!needle) return true;
      return [a.work_id, a.mp_name, a.work_description, a.work_category_suffix, a.ida, a.state]
        .some((v) => String(v ?? '').toLowerCase().includes(needle));
    });
    return filtered.sort((a, b) => {
      let va: unknown = a[sortField as keyof AlertRow];
      let vb: unknown = b[sortField as keyof AlertRow];
      if (typeof va === 'number' && typeof vb === 'number')
        return sortDir === 'asc' ? va - vb : vb - va;
      va = String(va ?? '').toLowerCase();
      vb = String(vb ?? '').toLowerCase();
      return sortDir === 'asc'
        ? (va as string).localeCompare(vb as string)
        : (vb as string).localeCompare(va as string);
    });
  }, [alerts, q, tier, sortField, sortDir]);

  const select = async (w: AlertRow, openModal = true) => {
    setSel(w);
    setLoadingDetail(true);
    setDetailErr(null);
    if (openModal) setIsModalOpen(true);
    try {
      const d = await apiFetch<RiskResponse>(`${API_BASE}/works/${encodeURIComponent(w.work_id)}/risk`);
      setDetail(d);
    } catch (e) {
      setDetailErr((e as Error).message);
    } finally {
      setLoadingDetail(false);
    }
  };

  const act = async (action: ActionKind) => {
    if (!sel) return;
    try {
      await apiFetch(`${API_BASE}/cases/${encodeURIComponent(sel.work_id)}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, note: 'Recorded from District Authority console', reviewer: 'DA-BAREILLY@mspi' }),
      });
      setActioned((prev) => new Set(prev).add(sel.work_id));
      setToast([`Action '${action}' recorded for work ${sel.work_id}`, false]);
    } catch (e) {
      setToast(['ERROR: ' + (e as Error).message, true]);
    }
    window.setTimeout(() => setToast(null), 3000);
  };

  const t = summary?.totals;

  return (
    <>
      {topbar}
      <Banner hidden={!er}>Cannot reach API server — running in offline prototype mode ({esc(er)})</Banner>

      {toast && (
        <div
          className={`mb-3 rounded border px-3 py-1.5 font-mono text-xs ${
            toast[1]
              ? 'border-tier-high/40 bg-tier-high/8 text-tier-high'
              : 'border-tier-low/40 bg-tier-low/8 text-tier-low'
          }`}
        >
          {esc(toast[0])}
        </div>
      )}

      {/* District scope selector */}
      <div className="mb-4 flex items-center justify-between rounded-lg border border-edge bg-panel px-4 py-2.5 shadow-sm">
        <div className="flex items-center gap-3">
          <span className="font-mono text-[11px] text-sub uppercase font-semibold">District / IDA Scope:</span>
          <select
            value={selectedIda}
            onChange={(e) => setSelectedIda(e.target.value)}
            className="rounded border border-edge bg-base px-3 py-1.5 font-mono text-xs text-fg focus:border-[#138808] focus:outline-none focus:ring-1 focus:ring-[#138808]/30"
          >
            {ALL_DISTRICTS.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>
        <div className="font-mono text-[11px] text-mut">
          Viewing: <span className="text-[#DC6B00] font-bold">{selectedIda}</span>
          {' '}({alerts.length} works in queue)
        </div>
      </div>

      <div className="mb-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Stat label="Works in District Queue"  value={(t?.works            ?? alerts.length ?? '—')?.toLocaleString?.('en-IN') ?? t?.works ?? '—'} />
        <Stat label="High Risk Flagged"        value={(t?.high_works       ?? '—')?.toLocaleString?.('en-IN') ?? t?.high_works ?? '—'}              tone="high" />
        <Stat label="Hard Rule Breaches"       value={(t?.hard_violations  ?? '—')?.toLocaleString?.('en-IN') ?? t?.hard_violations ?? '—'}        tone="med"  />
        <Stat label="Total Sanctioned Fund"    value={t ? '₹' + Math.round(t.total_sanctioned).toLocaleString('en-IN') : '—'} />
      </div>

      {/* Tier filter + search bar */}
      <div className="mb-4 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[11px] text-sub uppercase font-semibold mr-1">Risk Tier:</span>
          {['', 'High', 'Medium', 'Low'].map((f) => (
            <button
              key={f}
              onClick={() => setTier(f)}
              className={`rounded border px-2.5 py-1 font-mono text-[11px] transition-colors ${
                tier === f
                  ? 'border-[#DC6B00]/60 bg-[#DC6B00]/10 text-[#DC6B00] font-bold'
                  : 'border-edge text-sub hover:bg-panel2 hover:text-fg'
              }`}
            >
              {f === '' ? 'All Tiers' : f}
            </button>
          ))}
          <span className="ml-3 font-mono text-[11px] text-mut">
            {rows.length} cases · click any row to open Case Audit Modal
          </span>
        </div>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Filter by Work ID, MP, Category, Description…"
          className="w-72 rounded border border-edge bg-panel px-3 py-1.5 text-[13px] placeholder:text-mut focus:border-[#138808] focus:outline-none focus:ring-1 focus:ring-[#138808]/20"
        />
      </div>

      <div className="overflow-x-auto rounded-lg border border-edge bg-panel shadow-sm">
        <table className="w-full border-collapse text-left">
          <thead className="bg-panel2 border-b border-edge">
            <tr>
              <SortTh label="Work ID"      field="work_id"              currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <SortTh label="Risk Score"   field="risk_score"           currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <SortTh label="Tier"         field="risk_tier"            currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <SortTh label="State / IDA"  field="ida"                  currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <SortTh label="MP Name"      field="mp_name"              currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <SortTh label="Category"     field="work_category_suffix" currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <SortTh label="Sanction Amt" field="sanction_amount"      currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <SortTh label="Work Status"  field="work_status"          currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <th className="px-3.5 py-2.5 text-left font-mono text-[10px] uppercase tracking-widest text-sub whitespace-nowrap">Work Description</th>
              <th className="px-3.5 py-2.5 text-left font-mono text-[10px] uppercase tracking-widest text-sub whitespace-nowrap">Action Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((a) => (
              <tr
                key={a.work_id}
                onClick={() => void select(a, true)}
                className={`cursor-pointer border-t border-edge/60 transition-colors ${
                  sel?.work_id === a.work_id
                    ? 'bg-[#138808]/8 font-medium'
                    : 'hover:bg-panel2/70'
                }`}
              >
                <td className={idCell}>{esc(a.work_id)}</td>
                <td className={tdNowrap}>
                  <TierDot tier={a.risk_tier} />
                  <span className="font-mono font-bold" style={{ color: riskColor(a.risk_tier) }}>
                    {Number(a.risk_score).toFixed(1)}
                  </span>
                </td>
                <td className={tdNowrap}>
                  <span className="font-mono text-xs text-sub">{a.risk_tier}</span>
                </td>
                <td className={`${tdNowrap} text-sub font-mono text-xs`}>
                  {esc(a.state || 'UP')} · <span className="text-fg font-semibold">{esc(a.ida || 'Bareilly')}</span>
                </td>
                <td className={`${tdNowrap} text-fg font-semibold`}>{esc(a.mp_name || '—')}</td>
                <td className={`${tdNowrap} text-sub font-mono text-xs`}>{esc(a.work_category_suffix || 'General')}</td>
                <td className={`${tdNowrap} font-mono font-bold text-fg`}>{amt(a.sanction_amount)}</td>
                <td className={tdNowrap}><StatusBadge status={a.work_status || 'Sanctioned'} /></td>
                <td className={descCell}>{esc(a.work_description)}</td>
                <td className={tdNowrap}>
                  {actioned.has(a.work_id) ? (
                    <span className="rounded bg-tier-low/12 border border-tier-low/30 px-2 py-0.5 font-mono text-[10px] text-tier-low font-semibold whitespace-nowrap">
                      ✓ Actioned
                    </span>
                  ) : (
                    <span className="font-mono text-[10px] text-mut whitespace-nowrap">Pending Review</span>
                  )}
                </td>
              </tr>
            ))}
            {!rows.length && (
              <tr>
                <td colSpan={10} className="border-t border-edge/60">
                  <Empty msg="No works match the current filters." />
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {isModalOpen && (
        <CaseModal
          data={detail}
          loading={loadingDetail}
          error={detailErr}
          onClose={() => setIsModalOpen(false)}
          onAction={act}
        />
      )}
    </>
  );
}
