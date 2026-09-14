import { amt, esc, riskColor } from '../lib/api';
import type { RiskResponse } from '../lib/types';
import { BypassBadge, StatusBadge } from './UI';

export type ActionKind = 'cleared' | 'escalated' | 'confirmed';

export function DetailPanel({
  data,
  error,
  loading,
  onAction,
}: {
  data:    RiskResponse | null;
  error:   string | null;
  loading: boolean;
  onAction: (action: ActionKind) => Promise<void>;
}) {
  if (loading) return (
    <div className="rounded-lg border border-edge bg-panel px-4 py-6 font-mono text-xs text-sub">
      Loading SHAP risk payload…
    </div>
  );
  if (error) return (
    <div className="rounded-lg border border-tier-high/40 bg-tier-high/8 px-4 py-6 font-mono text-xs text-tier-high">
      {esc(error)}
    </div>
  );
  if (!data) return (
    <div className="rounded-lg border border-edge bg-panel px-4 py-6 font-mono text-xs text-sub">
      Select any work from the table to view its full SHAP case file and anomaly breakdown.
    </div>
  );

  const c    = riskColor(data.risk_tier);
  const comps = data.components ?? {};
  const keys = [
    { key: 'xgboost',    label: 'XGBoost Risk Probability (Supervised)',       color: '#B91C1C' },
    { key: 'isolforest', label: 'Isolation Forest Anomaly Score (Unsupervised)',color: '#B45309' },
    { key: 'similarity', label: 'Text / Image Similarity Score',                color: '#138808' },
  ];

  const bars = keys.map(({ key, label, color }) => {
    const w   = Number(comps[key] ?? comps[key + '_risk'] ?? comps[key + '_anomaly'] ?? 0);
    const pct = Math.max(0, Math.min(1, w)) * 100;
    return (
      <div key={key} className="space-y-1">
        <div className="flex justify-between font-mono text-[11px]">
          <span className="text-sub">{label}</span>
          <span className="text-fg font-semibold">{w.toFixed(4)}</span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-panel2">
          <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
        </div>
      </div>
    );
  });

  const meta: Array<[string, string]> = [
    ['Risk Score',     `${Number(data.risk_score).toFixed(1)} / 100`],
    ['Risk Tier',      data.risk_tier],
    ['Category',       data.work_category_suffix || 'General Infrastructure'],
    ['Sanction Amount',amt(data.sanction_amount)],
    ['Disbursed Amount',amt(data.disbursed_amount || data.sanction_amount)],
    ['State / District',`${data.state || 'UP'} · ${data.ida || 'Bareilly'}`],
    ['MP Name',        data.mp_name || '—'],
  ];

  return (
    <div className="rounded-lg border border-edge bg-panel p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-edge pb-3">
        <div className="flex flex-wrap items-center gap-3">
          <span className="font-mono text-[15px] font-bold text-fg">{esc(data.work_id)}</span>
          <BypassBadge bypass={!!data.bypass_ml} />
          <StatusBadge status={data.work_status || 'Sanctioned'} />
        </div>
        <div className="font-mono text-xs text-sub">
          Source: <span className="text-fg font-semibold">{esc(data.source_table ?? 'Works_Sanctioned')}</span>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
        {meta.map(([k, v]) => (
          <div key={k} className="rounded border border-edge bg-base px-2.5 py-2">
            <div className="font-mono text-[9px] uppercase tracking-widest text-mut">{k}</div>
            <div
              className="mt-0.5 truncate font-mono text-[12px] font-semibold"
              style={k === 'Risk Score' ? { color: c } : { color: '#0C190C' }}
              title={v}
            >
              {v || '—'}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 rounded-md border border-[#DC6B00]/30 bg-[#DC6B00]/6 p-3.5">
        <div className="font-mono text-[10px] uppercase tracking-widest text-[#DC6B00] font-bold mb-1">
          SHAP Plain-Language Reason Code
        </div>
        <div className="text-[13px] leading-relaxed text-fg">
          {esc(data.shap_reason || 'No anomaly indicators flagged for this work.')}
        </div>
      </div>

      <div className="mt-4 font-mono text-[10px] uppercase tracking-widest text-sub font-bold mb-2">
        Model Component Contributions (0–1 Scale)
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">{bars}</div>

      <div className="mt-5 flex items-center justify-between border-t border-edge pt-4">
        <div className="font-mono text-[11px] text-mut">Auditor actions feed back into retraining:</div>
        <div className="flex gap-2.5">
          {([
            ['cleared',   'Clear Case',          'border-tier-low/40  bg-tier-low/10  text-tier-low  hover:bg-tier-low/20'],
            ['escalated', 'Escalate to Nodal',   'border-tier-med/40  bg-tier-med/10  text-tier-med  hover:bg-tier-med/20'],
            ['confirmed', 'Confirm Irregularity','border-tier-high/60 bg-tier-high    text-white      hover:bg-tier-high/90 shadow'],
          ] as Array<[ActionKind, string, string]>).map(([a, label, cls]) => (
            <button
              key={a}
              onClick={() => void onAction(a)}
              className={`rounded border px-3.5 py-1.5 font-mono text-xs font-semibold transition-colors ${cls}`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
