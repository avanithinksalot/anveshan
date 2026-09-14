import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { API_BASE, amt, apiFetch, esc, riskColor } from '../lib/api';
import type { AlertRow, DashboardSummary } from '../lib/types';
import { Empty, Panel, SortTh, Stat, StatusBadge, TierDot, descCell, idCell, tdNowrap } from '../components/UI';

const ALL_STATES = [
  'All States (National View)',
  'Uttar Pradesh',
  'Maharashtra',
  'Bihar',
  'West Bengal',
  'Madhya Pradesh',
  'Rajasthan',
  'Tamil Nadu',
  'Gujarat',
  'Delhi',
  'Karnataka',
  'Kerala',
  'Punjab',
  'Odisha',
  'Assam',
];

const CHART_TOOLTIP = {
  contentStyle: {
    background: '#FFFFFF',
    border: '1px solid #B8CEB8',
    borderRadius: 6,
    fontSize: 12,
    color: '#0C190C',
    boxShadow: '0 2px 8px rgba(12,25,12,0.08)',
  },
  labelStyle: { color: '#0C190C', fontWeight: 600 },
  itemStyle:  { color: '#B91C1C' },
  cursor:     { fill: 'rgba(180,210,180,0.25)' },
};

export function StateNodalView({ topbar }: { topbar: ReactNode }) {
  const [data, setData]           = useState<DashboardSummary | null>(null);
  const [selectedState, setSelectedState] = useState<string>('All States (National View)');
  const [district, setDistrict]   = useState<string | null>(null);
  const [alerts, setAlerts]       = useState<AlertRow[]>([]);
  const [er, setEr]               = useState<string | null>(null);
  const [sortField, setSortField] = useState<string>('risk_score');
  const [sortDir, setSortDir]     = useState<'asc' | 'desc'>('desc');

  useEffect(() => {
    (async () => {
      try {
        const stateParam = selectedState.includes('All') ? '' : `&state=${encodeURIComponent(selectedState)}`;
        const s  = await apiFetch<DashboardSummary>(`${API_BASE}/dashboard/summary?role=state_nodal${stateParam}`);
        const al = await apiFetch<{ alerts: AlertRow[] }>(`${API_BASE}/alerts?limit=1000${stateParam}`);
        setData(s);
        setAlerts(al.alerts);
        const grouped = new Map<string, AlertRow[]>();
        for (const a of al.alerts) grouped.get(a.ida ?? '?')?.push(a) ?? grouped.set(a.ida ?? '?', [a]);
        const g = [...grouped.entries()].sort((a, b) => b[1].length - a[1].length);
        setDistrict(g[0]?.[0] ?? null);
      } catch (e) {
        setEr((e as Error).message);
      }
    })();
  }, [selectedState]);

  const handleSort = (field: string) => {
    if (sortField === field) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else { setSortField(field); setSortDir('desc'); }
  };

  const distRows = useMemo(() => {
    const grouped = new Map<string, number>();
    for (const a of alerts) grouped.set(a.ida ?? '?', (grouped.get(a.ida ?? '?') ?? 0) + 1);
    return [...grouped.entries()]
      .map(([d, n]) => ({ district: d, n }))
      .sort((a, b) => b.n - a.n)
      .slice(0, 16);
  }, [alerts]);

  const drill = useMemo(() => {
    let filtered = district
      ? alerts.filter((a) => (a.ida || '').toLowerCase().includes(district.toLowerCase()))
      : alerts;
    if (!filtered.length && alerts.length) filtered = alerts;

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
  }, [alerts, district, sortField, sortDir]);

  const t = data?.totals;
  return (
    <>
      {topbar}
      {er && (
        <div className="mb-4 rounded-lg border border-tier-high/40 bg-tier-high/8 px-3 py-2 font-mono text-xs text-tier-high">
          Cannot reach backend API — using dynamic mock data ({esc(er)})
        </div>
      )}

      {/* State scope selector */}
      <div className="mb-4 flex items-center justify-between rounded-lg border border-edge bg-panel px-4 py-2.5 shadow-sm">
        <div className="flex items-center gap-3">
          <span className="font-mono text-[11px] text-sub uppercase font-semibold">State Scope:</span>
          <select
            value={selectedState}
            onChange={(e) => setSelectedState(e.target.value)}
            className="rounded border border-edge bg-base px-3 py-1.5 font-mono text-xs text-fg focus:border-[#138808] focus:outline-none focus:ring-1 focus:ring-[#138808]/30"
          >
            {ALL_STATES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div className="font-mono text-[11px] text-mut">
          Viewing: <span className="text-[#DC6B00] font-bold">{selectedState}</span>
          {' '}({alerts.length} works loaded)
        </div>
      </div>

      <div className="mb-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Stat label="Total Works in Scope"  value={(t?.works            ?? alerts.length ?? '—').toLocaleString?.('en-IN') ?? t?.works ?? '—'} />
        <Stat label="High Risk Flagged"     value={(t?.high_works       ?? '—').toLocaleString?.('en-IN') ?? t?.high_works ?? '—'}      tone="high" />
        <Stat label="Hard Rule Breaches"    value={(t?.hard_violations  ?? '—').toLocaleString?.('en-IN') ?? t?.hard_violations ?? '—'} tone="med"  />
        <Stat label="Sanctioned Total"      value={t ? '₹' + Math.round(t.total_sanctioned).toLocaleString('en-IN') : '—'} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Panel title="High-Risk Works by District" className="p-3">
          {distRows.length ? (
            <ResponsiveContainer width="100%" height={340}>
              <BarChart data={distRows} layout="vertical" margin={{ left: 8, right: 32, top: 8, bottom: 4 }}>
                <XAxis
                  type="number"
                  tick={{ fill: '#7A967A', fontSize: 10, fontFamily: 'IBM Plex Mono' }}
                  axisLine={{ stroke: '#B8CEB8' }}
                  tickLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="district"
                  width={140}
                  tick={{ fill: '#375437', fontSize: 11, fontFamily: 'IBM Plex Mono' }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip {...CHART_TOOLTIP} />
                <Bar dataKey="n" name="Flagged works" radius={[0, 4, 4, 0]}>
                  {distRows.map((d, i) => (
                    <Cell
                      key={d.district}
                      fill="#B91C1C"
                      fillOpacity={0.35 + 0.65 * ((distRows.length - i) / distRows.length)}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <Empty msg="No district breakdown available." />
          )}
        </Panel>

        <Panel title="Districts — Click to filter case register" className="col-span-2 scrollbar-thin max-h-[400px] overflow-y-auto p-1">
          <div className="grid grid-cols-2 gap-1.5 p-2">
            {distRows.map((d) => (
              <button
                key={d.district}
                onClick={() => setDistrict(d.district)}
                className={`flex items-center justify-between gap-2 px-3 py-2 text-left font-mono text-[12px] rounded border transition-colors ${
                  district === d.district
                    ? 'border-[#138808] bg-[#138808]/10 font-bold text-[#166534]'
                    : 'border-edge text-sub hover:bg-panel2 hover:text-fg'
                }`}
              >
                <span className="truncate" title={d.district}>{d.district}</span>
                <span className="shrink-0 rounded bg-tier-high/12 px-1.5 py-0.5 text-[11px] font-bold text-tier-high border border-tier-high/30">
                  {d.n} High
                </span>
              </button>
            ))}
          </div>
          {!distRows.length && <Empty msg="No districts loaded." />}
        </Panel>
      </div>

      <Panel
        title={district ? `District Drill-Down — ${district} · High-Risk Cases` : 'District Case Drill-Down'}
        className="mt-5 overflow-x-auto"
      >
        <table className="w-full border-collapse text-left">
          <thead className="bg-panel2 border-b border-edge">
            <tr>
              <SortTh label="Work ID"      field="work_id"              currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <SortTh label="Risk Score"   field="risk_score"           currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <SortTh label="Tier"         field="risk_tier"            currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <SortTh label="District / IDA" field="ida"               currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <SortTh label="MP Name"      field="mp_name"              currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <SortTh label="Category"     field="work_category_suffix" currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <SortTh label="Sanction Amt" field="sanction_amount"      currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <SortTh label="Status"       field="work_status"          currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <th className="px-3.5 py-2.5 text-left font-mono text-[10px] uppercase tracking-widest text-sub whitespace-nowrap">Work Description & SHAP Reason</th>
            </tr>
          </thead>
          <tbody>
            {drill.map((a) => (
              <tr key={a.work_id} className="border-t border-edge/60 hover:bg-panel2/60 transition-colors">
                <td className={idCell}>{esc(a.work_id)}</td>
                <td className={tdNowrap}>
                  <TierDot tier={a.risk_tier} />
                  <span className="font-mono font-bold" style={{ color: riskColor(a.risk_tier) }}>
                    {Number(a.risk_score).toFixed(1)}
                  </span>
                </td>
                <td className={tdNowrap}><span className="font-mono text-xs text-sub">{a.risk_tier}</span></td>
                <td className={`${tdNowrap} font-semibold text-fg`}>{esc(a.ida || 'Bareilly')}</td>
                <td className={`${tdNowrap} font-semibold text-fg`}>{esc(a.mp_name || '—')}</td>
                <td className={`${tdNowrap} font-mono text-xs text-sub`}>{esc(a.work_category_suffix || 'General')}</td>
                <td className={`${tdNowrap} font-mono font-bold text-fg`}>{amt(a.sanction_amount)}</td>
                <td className={tdNowrap}><StatusBadge status={a.work_status || 'Sanctioned'} /></td>
                <td className={descCell}>
                  <div>{esc(a.work_description)}</div>
                  {a.shap_reason && (
                    <div className="mt-1 font-mono text-[11px] text-tier-med bg-tier-med/8 px-2 py-1.5 rounded border border-tier-med/20">
                      {esc(a.shap_reason)}
                    </div>
                  )}
                </td>
              </tr>
            ))}
            {!drill.length && (
              <tr>
                <td colSpan={9} className="border-t border-edge/60">
                  <Empty msg="Select a district to load its cases." />
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Panel>
    </>
  );
}
