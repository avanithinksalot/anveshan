import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { API_BASE, amt, apiFetch, esc, riskColor } from '../lib/api';
import type { DashboardSummary, RiskResponse, WorkRow } from '../lib/types';
import { DetailPanel } from '../components/DetailPanel';
import { Empty, SortTh, Stat, StatusBadge, TierDot, descCell, idCell, tdNowrap } from '../components/UI';

const ALL_MPS = [
  'All MPs (Nationwide Portfolio)',
  'Shri Hardeep Singh Puri',
  'Shri Santosh Kumar Gangwar',
  'Shri Rajnath Singh',
  'Shri Narendra Modi',
  'Shri Girish Bapat',
  'Shri Ravi Shankar Prasad',
  'Shri Sudip Bandyopadhyay',
  'Sadhvi Pragya Singh Thakur',
  'Shri Ramcharan Bohra',
  'Dr. T. Sumathy (Thamachi Thangapandian)',
  'Shri Hasmukhbhai Patel',
  'Shri Tejasvi Surya',
  'Shri Shashi Tharoor',
];

export function MPView({ topbar }: { topbar: ReactNode }) {
  const [data, setData]           = useState<DashboardSummary | null>(null);
  const [selectedMp, setSelectedMp] = useState<string>('All MPs (Nationwide Portfolio)');
  const [er, setEr]               = useState<string | null>(null);
  const [q, setQ]                 = useState('');
  const [tier, setTier]           = useState('');
  const [sel, setSel]             = useState<WorkRow | null>(null);
  const [detail, setDetail]       = useState<RiskResponse | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailErr, setDetailErr] = useState<string | null>(null);
  const [sortField, setSortField] = useState<string>('risk_score');
  const [sortDir, setSortDir]     = useState<'asc' | 'desc'>('desc');

  useEffect(() => {
    (async () => {
      try {
        const mpParam = selectedMp.includes('All') ? '' : `&mp=${encodeURIComponent(selectedMp)}`;
        const s = await apiFetch<DashboardSummary>(`${API_BASE}/dashboard/summary?role=mp${mpParam}&limit=1000`);
        setData(s);
        if (s.works && s.works.length > 0) void select(s.works[0]);
      } catch (e) {
        setEr((e as Error).message);
      }
    })();
  }, [selectedMp]);

  const handleSort = (field: string) => {
    if (sortField === field) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else { setSortField(field); setSortDir('desc'); }
  };

  const works = data?.works ?? [];
  const rows = useMemo(() => {
    const needle = q.toLowerCase().trim();
    const filtered = works.filter((w) => {
      if (tier && String(w.risk_tier ?? '').toLowerCase() !== tier.toLowerCase()) return false;
      if (!needle) return true;
      return [w.work_id, w.work_description, w.work_category_suffix, w.ida, w.state]
        .some((v) => String(v ?? '').toLowerCase().includes(needle));
    });
    return filtered.sort((a, b) => {
      let va: unknown = a[sortField as keyof WorkRow];
      let vb: unknown = b[sortField as keyof WorkRow];
      if (typeof va === 'number' && typeof vb === 'number')
        return sortDir === 'asc' ? va - vb : vb - va;
      va = String(va ?? '').toLowerCase();
      vb = String(vb ?? '').toLowerCase();
      return sortDir === 'asc'
        ? (va as string).localeCompare(vb as string)
        : (vb as string).localeCompare(va as string);
    });
  }, [works, q, tier, sortField, sortDir]);

  const select = async (w: WorkRow) => {
    setSel(w);
    setLoadingDetail(true);
    setDetailErr(null);
    try {
      const d = await apiFetch<RiskResponse>(`${API_BASE}/works/${encodeURIComponent(w.work_id)}/risk`);
      setDetail(d);
    } catch (e) {
      setDetailErr((e as Error).message);
    } finally {
      setLoadingDetail(false);
    }
  };

  const t = data?.totals;
  return (
    <>
      {topbar}
      {er && (
        <div className="mb-4 rounded-lg border border-tier-high/40 bg-tier-high/8 px-3 py-2 font-mono text-xs text-tier-high">
          Cannot reach API backend — displaying dynamic offline portfolio ({esc(er)})
        </div>
      )}

      {/* Informational notice — MP view is self-verification, not accusation */}
      <div className="mb-4 rounded-lg border border-[#138808]/30 bg-[#138808]/8 px-4 py-2.5 font-mono text-[11px] text-[#166534]">
        <span className="font-bold">Self-verification view:</span> This dashboard shows your MPLADS portfolio compliance status.
        Flagged works represent risk signals for your review — not confirmed irregularities.
      </div>

      {/* MP selector */}
      <div className="mb-4 flex items-center justify-between rounded-lg border border-edge bg-panel px-4 py-2.5 shadow-sm">
        <div className="flex items-center gap-3">
          <span className="font-mono text-[11px] text-sub uppercase font-semibold">Select MP:</span>
          <select
            value={selectedMp}
            onChange={(e) => setSelectedMp(e.target.value)}
            className="rounded border border-edge bg-base px-3 py-1.5 font-mono text-xs text-fg focus:border-[#138808] focus:outline-none focus:ring-1 focus:ring-[#138808]/30"
          >
            {ALL_MPS.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>
        <div className="font-mono text-[11px] text-mut">
          Portfolio: <span className="text-[#DC6B00] font-bold">{selectedMp}</span>
          {' '}({works.length} works)
        </div>
      </div>

      <div className="mb-4 grid grid-cols-4 gap-3">
        <Stat label="Sanctioned Portfolio Works"      value={(t?.works ?? works.length ?? '—').toLocaleString?.('en-IN') ?? t?.works ?? '—'} />
        <Stat label="High Risk Flagged"              value={(t?.high_works ?? '—').toLocaleString?.('en-IN') ?? t?.high_works ?? '—'}      tone="high" />
        <Stat label="Hard Rule Breaches"             value={(t?.hard_violations ?? '—').toLocaleString?.('en-IN') ?? t?.hard_violations ?? '—'} tone="med" />
        <Stat label="Total Portfolio Funds Sanctioned" value={t ? '₹' + Math.round(t.total_sanctioned).toLocaleString('en-IN') : '—'} />
      </div>

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
              {f === '' ? 'All Portfolio Works' : f}
            </button>
          ))}
          <span className="ml-3 font-mono text-[11px] text-mut">{rows.length} works shown</span>
        </div>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search work ID, category, description…"
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
              <SortTh label="State / District" field="ida"              currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <SortTh label="Category"     field="work_category_suffix" currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <SortTh label="Sanction Amt" field="sanction_amount"      currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <SortTh label="Status"       field="work_status"          currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <th className="px-3.5 py-2.5 text-left font-mono text-[10px] uppercase tracking-widest text-sub whitespace-nowrap">Work Description</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((w) => (
              <tr
                key={w.work_id}
                onClick={() => void select(w)}
                className={`cursor-pointer border-t border-edge/60 transition-colors ${
                  sel?.work_id === w.work_id ? 'bg-[#138808]/8 font-medium' : 'hover:bg-panel2/70'
                }`}
              >
                <td className={idCell}>{esc(w.work_id)}</td>
                <td className={tdNowrap}>
                  <TierDot tier={w.risk_tier} />
                  <span className="font-mono font-bold" style={{ color: riskColor(w.risk_tier) }}>
                    {Number(w.risk_score).toFixed(1)}
                  </span>
                </td>
                <td className={tdNowrap}><span className="font-mono text-xs text-sub">{w.risk_tier}</span></td>
                <td className={`${tdNowrap} font-mono text-xs text-sub`}>
                  {esc(w.state || 'Delhi')} · <span className="text-fg font-semibold">{esc(w.ida || 'New Delhi')}</span>
                </td>
                <td className={`${tdNowrap} font-mono text-xs text-sub`}>{esc(w.work_category_suffix || 'Parks')}</td>
                <td className={`${tdNowrap} font-mono font-bold text-fg`}>{amt(w.sanction_amount)}</td>
                <td className={tdNowrap}><StatusBadge status={w.work_status || 'Sanctioned'} /></td>
                <td className={descCell}>{esc(w.work_description)}</td>
              </tr>
            ))}
            {!rows.length && (
              <tr>
                <td colSpan={8} className="border-t border-edge/60">
                  <Empty msg="No works match the current filters." />
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-6">
        <div className="mb-2 font-mono text-[10px] uppercase tracking-widest text-[#166534] font-semibold">
          Self-Verification Case File & Compliance Panel
        </div>
        <DetailPanel data={detail} error={detailErr} loading={loadingDetail} onAction={async () => {}} />
      </div>
    </>
  );
}
