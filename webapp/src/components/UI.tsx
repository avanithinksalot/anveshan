import type { ReactNode } from 'react';
import { riskColor } from '../lib/api';

export function Stat({
  label,
  value,
  tone = '',
}: {
  label: string;
  value: ReactNode;
  tone?: '' | 'high' | 'med' | 'low';
}) {
  const textColors = {
    '':    'text-fg',
    high:  'text-tier-high',
    med:   'text-tier-med',
    low:   'text-tier-low',
  };
  const borderColors = {
    '':    'border-l-edge',
    high:  'border-l-tier-high',
    med:   'border-l-tier-med',
    low:   'border-l-tier-low',
  };
  return (
    <div className={`rounded-lg border border-edge bg-panel px-4 py-3 border-l-4 ${borderColors[tone]}`}>
      <div className="text-[10px] uppercase tracking-wider text-sub font-medium">{label}</div>
      <div className={`mt-1 font-mono text-2xl font-bold ${textColors[tone]}`}>{value}</div>
    </div>
  );
}

export function TierDot({ tier }: { tier?: string | null }) {
  return (
    <span
      className="mr-2 inline-block h-2 w-2 rounded-full align-middle border border-white shadow-sm"
      style={{ background: riskColor(tier) }}
    />
  );
}

export function TierChip({ tier }: { tier?: string | null }) {
  return (
    <span className="inline-flex items-center whitespace-nowrap rounded border border-edge bg-panel px-1.5 py-0.5 font-mono text-[11px] text-sub">
      <TierDot tier={tier} />
      {tier ?? '—'}
    </span>
  );
}

export function ActionChip({ action }: { action: string }) {
  const map: Record<string, string> = {
    cleared:   'border-tier-low/50  bg-tier-low/10  text-tier-low',
    escalated: 'border-tier-med/50  bg-tier-med/10  text-tier-med',
    confirmed: 'border-tier-high/50 bg-tier-high/10 text-tier-high',
  };
  return (
    <span
      className={`mr-2 inline-flex rounded border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider font-semibold ${
        map[action] ?? 'border-edge text-sub'
      }`}
    >
      {action}
    </span>
  );
}

export function StatusBadge({ status }: { status?: string | null }) {
  if (!status) return <span className="text-mut">—</span>;
  const s = status.toLowerCase();
  let cls = 'border-edge text-sub bg-panel2';
  if (s.includes('completed'))
    cls = 'border-tier-low/40 text-tier-low bg-tier-low/10';
  else if (s.includes('sanctioned'))
    cls = 'border-[#DC6B00]/30 text-[#DC6B00] bg-[#DC6B00]/8';
  else if (s.includes('inspection') || s.includes('vendor'))
    cls = 'border-tier-med/40 text-tier-med bg-tier-med/10';

  return (
    <span
      className={`inline-flex items-center rounded border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide font-medium ${cls}`}
    >
      {status}
    </span>
  );
}

export function BypassBadge({ bypass }: { bypass: boolean }) {
  return bypass ? (
    <span className="inline-flex whitespace-nowrap rounded border border-color-rule/50 bg-color-rule/10 px-1.5 py-0.5 font-mono text-[10px] tracking-wide text-color-rule font-semibold">
      HARD RULE BREACH — ML BYPASSED
    </span>
  ) : (
    <span className="inline-flex whitespace-nowrap rounded border border-edge px-1.5 py-0.5 font-mono text-[10px] tracking-wide text-mut">
      ML-DELIBERATED
    </span>
  );
}

export function Panel({
  title,
  children,
  className = '',
}: {
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-lg border border-edge bg-panel shadow-sm ${className}`}>
      {title && (
        <h3 className="border-b border-edge px-4 py-2.5 font-mono text-[10px] uppercase tracking-widest text-sub font-semibold bg-panel2 rounded-t-lg">
          {title}
        </h3>
      )}
      {children}
    </section>
  );
}

export function Banner({ hidden, children }: { hidden: boolean; children: ReactNode }) {
  if (hidden) return null;
  return (
    <div className="mb-4 rounded-lg border border-tier-high/40 bg-tier-high/8 px-3 py-2 font-mono text-xs text-tier-high">
      {children}
    </div>
  );
}

export function Empty({ msg }: { msg: string }) {
  return (
    <div className="px-4 py-8 text-center font-mono text-xs text-mut">{msg}</div>
  );
}

export function SortTh({
  label,
  field,
  currentSort,
  currentDir,
  onSort,
}: {
  label: string;
  field: string;
  currentSort: string;
  currentDir: 'asc' | 'desc';
  onSort: (field: string) => void;
}) {
  const active = currentSort === field;
  return (
    <th
      onClick={() => onSort(field)}
      className={`cursor-pointer select-none px-3.5 py-2.5 text-left font-mono text-[10px] uppercase tracking-widest hover:text-fg transition-colors whitespace-nowrap ${
        active ? 'text-[#DC6B00]' : 'text-sub'
      }`}
    >
      <div className="flex items-center gap-1">
        <span>{label}</span>
        {active && (
          <span className="text-[#DC6B00] font-bold">
            {currentDir === 'asc' ? '↑' : '↓'}
          </span>
        )}
      </div>
    </th>
  );
}

export const th       = 'px-3.5 py-2.5 text-left font-mono text-[10px] uppercase tracking-widest text-sub whitespace-nowrap align-middle';
export const td       = 'px-3.5 py-2.5 text-[13px] align-middle';
export const tdNowrap = 'px-3.5 py-2.5 text-[13px] align-middle whitespace-nowrap';
export const idCell   = 'px-3.5 py-2.5 font-mono text-[12px] text-[#138808] font-bold align-middle whitespace-nowrap';
export const rankCell = 'px-3.5 py-2.5 font-mono text-[12px] text-mut align-middle whitespace-nowrap';
export const descCell = 'px-3.5 py-2.5 text-[12.5px] leading-relaxed text-fg align-middle whitespace-normal break-words max-w-md min-w-[260px]';
