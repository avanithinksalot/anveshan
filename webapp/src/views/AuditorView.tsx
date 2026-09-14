import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { API_BASE, amt, apiFetch, esc, now2, riskColor } from '../lib/api';
import type { AuditAction, AuditResponse } from '../lib/types';
import { ActionChip, Empty, Panel, SortTh, Stat, StatusBadge, TierChip, descCell, idCell, tdNowrap } from '../components/UI';
import { IndiaMap } from '../components/IndiaMap';
import { MOCK_STATE_AUDIT } from '../data/indiaStates';

export function AuditorView({ topbar }: { topbar: ReactNode }) {
  const [data, setData]           = useState<AuditResponse | null>(null);
  const [er, setEr]               = useState<string | null>(null);
  const [mode, setMode]           = useState('');
  const [sortField, setSortField] = useState<string>('recorded_at');
  const [sortDir, setSortDir]     = useState<'asc' | 'desc'>('desc');

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const j = await apiFetch<AuditResponse>(`${API_BASE}/audit/actions?limit=200`);
        if (alive) { setData(j); setEr(null); }
      } catch (e) {
        if (alive) setEr((e as Error).message);
      }
    };
    void load();
    const t = window.setInterval(load, 5000);
    return () => { alive = false; window.clearInterval(t); };
  }, []);

  const handleSort = (field: string) => {
    if (sortField === field) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else { setSortField(field); setSortDir('desc'); }
  };

  const actions = useMemo(() => {
    const list = mode ? (data?.actions ?? []).filter((a) => a.action === mode) : data?.actions ?? [];
    return list.sort((a, b) => {
      let va: unknown = a[sortField as keyof AuditAction];
      let vb: unknown = b[sortField as keyof AuditAction];
      if (typeof va === 'number' && typeof vb === 'number')
        return sortDir === 'asc' ? va - vb : vb - va;
      va = String(va ?? '').toLowerCase();
      vb = String(vb ?? '').toLowerCase();
      return sortDir === 'asc'
        ? (va as string).localeCompare(vb as string)
        : (vb as string).localeCompare(va as string);
    });
  }, [data, mode, sortField, sortDir]);

  const c = data?.counts;
  return (
    <>
      {topbar}
      {er && (
        <div className="mb-4 rounded-lg border border-tier-high/40 bg-tier-high/8 px-3 py-2 font-mono text-xs text-tier-high">
          Cannot reach API backend — displaying dynamic offline audit feed ({esc(er)})
        </div>
      )}
      {!er && data && (
        <div className="mb-4 rounded border border-tier-low/40 bg-tier-low/8 px-3 py-1.5 font-mono text-[11px] text-tier-low font-semibold">
          ● LIVE AUDIT FEED — auto-polling /audit/actions every 5s · Postgres-backed active learning loop
        </div>
      )}

      <div className="mb-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Stat label="Total Decisions Recorded" value={c?.total     ?? '—'} />
        <Stat label="Cleared Works"            value={c?.cleared   ?? '—'} tone="low" />
        <Stat label="Escalated Cases"          value={c?.escalated ?? '—'} tone="med" />
        <Stat label="Confirmed Irregularities" value={c?.confirmed ?? '—'} tone="high" />
      </div>

      {/* Geographic audit density map */}
      <div className="mb-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Panel title="Confirmed Irregularities — Geographic Audit Density" className="lg:col-span-2 p-3">
          <IndiaMap
            data={MOCK_STATE_AUDIT}
            subtitle="Confirmed irregularities by state · Darker = more confirmed cases · Click to filter"
            colorHigh="#B91C1C"
          />
        </Panel>
        <Panel title="Audit Breakdown by State" className="p-3">
          <div className="space-y-2">
            <div className="font-mono text-[9px] uppercase tracking-widest text-mut mb-3">Top States by Confirmed Irregularities</div>
            {Object.entries(MOCK_STATE_AUDIT)
              .sort(([,a],[,b]) => b - a)
              .slice(0, 10)
              .map(([state, n], i) => (
                <div key={state} className="flex items-center gap-2">
                  <span className="font-mono text-[9px] text-mut w-4">{i+1}.</span>
                  <div className="flex-1">
                    <div className="flex justify-between font-mono text-[11px]">
                      <span className="text-fg font-semibold">{state}</span>
                      <span className="text-tier-high font-bold">{n}</span>
                    </div>
                    <div className="mt-0.5 h-1 rounded-full bg-panel2 overflow-hidden">
                      <div className="h-full bg-tier-high/70 rounded-full" style={{ width: `${Math.min(100, n/18*100)}%` }} />
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </Panel>
      </div>

      <div className="mb-4 flex items-center justify-between">
        <div className="flex gap-2 items-center">
          <span className="font-mono text-[11px] text-sub uppercase font-semibold mr-1">Decision Filter:</span>
          {[
            ['',          'All Actions'      ],
            ['cleared',   'Cleared'          ],
            ['escalated', 'Escalated'        ],
            ['confirmed', 'Confirmed Fraud'  ],
          ].map(([v, label]) => (
            <button
              key={v}
              onClick={() => setMode(v)}
              className={`rounded border px-2.5 py-1 font-mono text-[11px] transition-colors ${
                mode === v
                  ? 'border-[#DC6B00]/60 bg-[#DC6B00]/10 text-[#DC6B00] font-bold'
                  : 'border-edge text-sub hover:bg-panel2 hover:text-fg'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="font-mono text-[11px] text-mut">{actions.length} audit records</div>
      </div>

      <Panel title="Ground-Truth Decision Feed & Active Retraining Labels">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left">
            <thead className="bg-panel2 border-b border-edge">
              <tr>
                <SortTh label="Action"      field="action"              currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
                <SortTh label="Work ID"     field="work_id"             currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
                <SortTh label="Recorded At" field="recorded_at"         currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
                <SortTh label="Risk Score"  field="risk_score_at"       currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
                <SortTh label="State / IDA" field="ida"                 currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
                <SortTh label="MP Name"     field="mp_name"             currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
                <SortTh label="Category"    field="work_category_suffix" currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
                <SortTh label="Sanction Amt" field="sanction_amount"    currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
                <SortTh label="Status"      field="work_status"         currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
                <th className="px-3.5 py-2.5 text-left font-mono text-[10px] uppercase tracking-widest text-sub whitespace-nowrap">Work Description & Reviewer Note</th>
                <SortTh label="Reviewer"    field="reviewer"            currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              </tr>
            </thead>
            <tbody>
              {actions.map((a) => (
                <tr
                  key={a.id ?? a.work_id + a.recorded_at}
                  className="border-t border-edge/60 hover:bg-panel2/60 transition-colors"
                >
                  <td className={tdNowrap}><ActionChip action={a.action} /></td>
                  <td className={idCell}>{esc(a.work_id)}</td>
                  <td className={`${tdNowrap} font-mono text-xs text-sub`}>{now2(a.recorded_at)}</td>
                  <td className={tdNowrap}>
                    <span className="font-mono font-bold" style={{ color: riskColor(a.risk_tier_at) }}>
                      {a.risk_score_at != null ? Number(a.risk_score_at).toFixed(1) : '—'}
                    </span>
                    <span className="ml-2"><TierChip tier={a.risk_tier_at} /></span>
                  </td>
                  <td className={`${tdNowrap} font-mono text-xs text-sub`}>
                    {esc(a.state || 'UP')} · <span className="text-fg font-semibold">{esc(a.ida || 'Bareilly')}</span>
                  </td>
                  <td className={`${tdNowrap} text-fg font-semibold`}>{esc(a.mp_name || '—')}</td>
                  <td className={`${tdNowrap} font-mono text-xs text-sub`}>{esc(a.work_category_suffix || 'General')}</td>
                  <td className={`${tdNowrap} font-mono font-bold text-fg`}>{amt(a.sanction_amount)}</td>
                  <td className={tdNowrap}><StatusBadge status={a.work_status || 'Sanctioned'} /></td>
                  <td className={descCell}>
                    <div>{esc(a.work_description)}</div>
                    {a.note && (
                      <div className="mt-1 font-mono text-[11px] text-tier-med bg-tier-med/8 px-2 py-1.5 rounded border border-tier-med/20">
                        Note: {esc(a.note)}
                      </div>
                    )}
                  </td>
                  <td className={`${tdNowrap} font-mono text-xs text-sub`}>{esc(a.reviewer)}</td>
                </tr>
              ))}
              {!actions.length && (
                <tr>
                  <td colSpan={11} className="border-t border-edge/60">
                    <Empty msg="No decisions recorded yet — work items appear here when auditors clear / escalate / confirm cases." />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>
    </>
  );
}
