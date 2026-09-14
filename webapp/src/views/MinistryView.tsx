import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import * as d3 from 'd3';
import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { API_BASE, amt, apiFetch, esc, riskColor } from '../lib/api';
import type { AlertRow, DashboardSummary } from '../lib/types';
import { Empty, Panel, SortTh, Stat, StatusBadge, TierDot, descCell, idCell, tdNowrap } from '../components/UI';
import { IndiaMap } from '../components/IndiaMap';
import { MOCK_STATE_RISK } from '../data/indiaStates';

const TIER_COLORS: Record<string, string> = {
  Low:    '#166534',
  Medium: '#B45309',
  High:   '#B91C1C',
};

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

function NationalBars({ data }: { data: DashboardSummary | null }) {
  const rows = useMemo(
    () =>
      Object.entries(data?.top_states_by_high ?? {})
        .map(([state, n]) => ({ state, n }))
        .sort((a, b) => b.n - a.n)
        .slice(0, 12),
    [data],
  );
  if (!rows.length) return <Empty msg="No per-state data available." />;
  return (
    <ResponsiveContainer width="100%" height={340}>
      <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 32, top: 8, bottom: 4 }}>
        <XAxis
          type="number"
          tick={{ fill: '#7A967A', fontSize: 10, fontFamily: 'IBM Plex Mono' }}
          axisLine={{ stroke: '#B8CEB8' }}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="state"
          width={130}
          tick={{ fill: '#375437', fontSize: 11, fontFamily: 'IBM Plex Mono' }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip {...CHART_TOOLTIP} itemStyle={{ color: '#B91C1C' }} />
        <Bar dataKey="n" name="High-flagged works" radius={[0, 4, 4, 0]}>
          {rows.map((r, i) => (
            <Cell
              key={r.state}
              fill="#B91C1C"
              fillOpacity={0.4 + 0.6 * ((rows.length - i) / rows.length)}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function TierDonut({ data }: { data: DashboardSummary | null }) {
  const rows = useMemo(() => {
    const t = data?.tiers;
    if (!t) return [];
    return [
      { name: 'Low',    value: t.low    },
      { name: 'Medium', value: t.medium },
      { name: 'High',   value: t.high   },
    ];
  }, [data]);
  if (!rows.length || rows.every((r) => r.value === 0)) return <Empty msg="No tier data." />;
  return (
    <div>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={rows}
            dataKey="value"
            nameKey="name"
            innerRadius={54}
            outerRadius={78}
            paddingAngle={3}
            stroke="#FFFFFF"
            strokeWidth={2}
          >
            {rows.map((r) => (
              <Cell key={r.name} fill={TIER_COLORS[r.name]} />
            ))}
          </Pie>
          <Tooltip {...CHART_TOOLTIP} />
        </PieChart>
      </ResponsiveContainer>
      <div className="flex justify-center gap-4 font-mono text-[11px] text-sub">
        {rows.map((r) => (
          <span key={r.name} className="flex items-center gap-1">
            <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: TIER_COLORS[r.name] }} />
            {r.name} {r.value?.toLocaleString?.('en-IN')}
          </span>
        ))}
      </div>
    </div>
  );
}

interface SimNode extends d3.SimulationNodeDatum {
  id: string;
  name: string;
  kind: 'mp' | 'ida';
  workCount: number;
}

interface SimLink extends d3.SimulationLinkDatum<SimNode> {
  source: string | SimNode;
  target: string | SimNode;
  value: number;
}

function MpNetwork({ alerts }: { alerts: AlertRow[] }) {
  const svgRef = useRef<SVGSVGElement>(null);
  const zoomBehaviorRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const [hoveredNode, setHoveredNode] = useState<SimNode | null>(null);

  const rawGraph = useMemo(() => {
    const nodeMap = new Map<string, { id: string; name: string; kind: 'mp' | 'ida'; workCount: number }>();
    const edgeMap = new Map<string, { source: string; target: string; value: number }>();

    for (const a of alerts) {
      const mpName  = a.mp_name || 'Unknown MP';
      const idaName = a.ida || 'Unknown IDA';
      const mpId    = 'mp:'  + mpName;
      const idaId   = 'ida:' + idaName;

      if (!nodeMap.has(mpId))  nodeMap.set(mpId,  { id: mpId,  name: mpName,  kind: 'mp',  workCount: 0 });
      if (!nodeMap.has(idaId)) nodeMap.set(idaId, { id: idaId, name: idaName, kind: 'ida', workCount: 0 });

      nodeMap.get(mpId)!.workCount  += 1;
      nodeMap.get(idaId)!.workCount += 1;

      const edgeKey = mpId + '->' + idaId;
      const edge = edgeMap.get(edgeKey) ?? { source: mpId, target: idaId, value: 0 };
      edge.value += 1;
      edgeMap.set(edgeKey, edge);
    }

    return {
      nodes: Array.from(nodeMap.values()),
      links: Array.from(edgeMap.values()),
    };
  }, [alerts]);

  const resetZoom = () => {
    if (!svgRef.current || !zoomBehaviorRef.current) return;
    d3.select(svgRef.current)
      .transition().duration(500)
      .call(zoomBehaviorRef.current.transform, d3.zoomIdentity);
  };

  const zoomIn = () => {
    if (!svgRef.current || !zoomBehaviorRef.current) return;
    d3.select(svgRef.current).transition().duration(250).call(zoomBehaviorRef.current.scaleBy, 1.35);
  };

  const zoomOut = () => {
    if (!svgRef.current || !zoomBehaviorRef.current) return;
    d3.select(svgRef.current).transition().duration(250).call(zoomBehaviorRef.current.scaleBy, 0.75);
  };

  useEffect(() => {
    if (!svgRef.current || !rawGraph.nodes.length) return;

    const nodes: SimNode[] = rawGraph.nodes.map((n) => ({ ...n }));
    const links: SimLink[] = rawGraph.links.map((l) => ({ ...l }));

    const W = 900, H = 480;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    svg.attr('viewBox', `0 0 ${W} ${H}`);

    /* ── Dot-grid background ──────────────────────────────── */
    const defs = svg.append('defs');
    const pat = defs.append('pattern')
      .attr('id', 'dot-grid')
      .attr('width', 24).attr('height', 24)
      .attr('patternUnits', 'userSpaceOnUse');
    pat.append('circle')
      .attr('cx', 12).attr('cy', 12).attr('r', 0.9)
      .attr('fill', '#B8CEB8').attr('opacity', 0.5);

    svg.append('rect').attr('width', W).attr('height', H).attr('fill', 'url(#dot-grid)');

    /* ── Zoomable group ─────────────────────────────────────── */
    const g = svg.append('g').attr('class', 'network-g');

    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.25, 5])
      .on('zoom', (evt) => g.attr('transform', evt.transform));
    zoomBehaviorRef.current = zoom;
    svg.call(zoom);

    /* ── Link color scale: faint green → saffron ───────────── */
    const maxVal = Math.max(...links.map((l) => l.value), 1);
    const linkStroke = (v: number) => {
      const t = v / maxVal;
      return t < 0.4 ? '#B8CEB8' : t < 0.7 ? '#DC6B00' : '#B91C1C';
    };

    /* ── Curved link paths ──────────────────────────────────── */
    const linkGroup = g.append('g').attr('class', 'links');
    const link = linkGroup
      .selectAll<SVGPathElement, SimLink>('path')
      .data(links)
      .join('path')
      .attr('fill', 'none')
      .attr('stroke', (d) => linkStroke(d.value))
      .attr('stroke-opacity', 0.75)
      .attr('stroke-width', (d) => Math.min(5, 0.8 + Math.sqrt(d.value) * 1.4));

    /* ── Nodes ──────────────────────────────────────────────── */
    const nodeGroup = g.append('g').attr('class', 'nodes');
    const node = nodeGroup
      .selectAll<SVGGElement, SimNode>('g')
      .data(nodes)
      .join('g')
      .attr('cursor', 'grab');

    /* Halo for high-volume nodes */
    node.filter((d) => d.workCount >= 3)
      .append('circle')
      .attr('r', (d) => (d.kind === 'mp' ? 14 : 10) + Math.min(d.workCount, 8) + 5)
      .attr('fill', (d) => (d.kind === 'mp' ? '#DC6B00' : '#138808'))
      .attr('fill-opacity', 0.1);

    /* Main circle */
    node.append('circle')
      .attr('r', (d) => (d.kind === 'mp' ? 13 : 9) + Math.min(d.workCount, 7))
      .attr('fill', (d) => (d.kind === 'mp' ? '#DC6B00' : '#138808'))
      .attr('stroke', '#FFFFFF')
      .attr('stroke-width', 2.5);

    /* Initials inside node */
    node.append('text')
      .text((d) => d.kind === 'mp' ? 'MP' : 'IDA')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('font-size', '7px')
      .attr('font-family', 'IBM Plex Mono, monospace')
      .attr('font-weight', '600')
      .attr('fill', '#FFFFFF')
      .attr('pointer-events', 'none');

    /* Label alongside node */
    node.append('text')
      .text((d) => {
        const max = 20;
        return d.name.length > max ? d.name.slice(0, max - 1) + '…' : d.name;
      })
      .attr('x', (d) => (d.kind === 'mp' ? 16 : 12) + Math.min(d.workCount, 7))
      .attr('y', 4)
      .attr('font-size', '9.5px')
      .attr('font-family', 'IBM Plex Mono, monospace')
      .attr('fill', (d) => (d.kind === 'mp' ? '#B45309' : '#166534'))
      .attr('font-weight', (d) => (d.workCount >= 3 ? '600' : '400'))
      .attr('pointer-events', 'none');

    /* Hover events */
    node
      .on('mouseenter', (_evt, d) => setHoveredNode(d))
      .on('mouseleave', () => setHoveredNode(null));

    /* Drag */
    const drag = d3.drag<SVGGElement, SimNode>()
      .on('start', (evt, d) => {
        if (!evt.active) sim.alphaTarget(0.3).restart();
        d.fx = d.x; d.fy = d.y;
      })
      .on('drag', (evt, d) => { d.fx = evt.x; d.fy = evt.y; })
      .on('end', (evt, d) => {
        if (!evt.active) sim.alphaTarget(0);
        d.fx = null; d.fy = null;
      });
    node.call(drag);

    /* Force simulation */
    const sim = d3
      .forceSimulation<SimNode>(nodes)
      .force('link', d3.forceLink<SimNode, SimLink>(links).id((d) => d.id).distance(130))
      .force('charge', d3.forceManyBody().strength(-350))
      .force('center', d3.forceCenter(W / 2, H / 2))
      .force('collide', d3.forceCollide(32))
      .on('tick', () => {
        link.attr('d', (d) => {
          const s = d.source as SimNode;
          const t = d.target as SimNode;
          const dx = t.x! - s.x!;
          const dy = t.y! - s.y!;
          const dr = Math.sqrt(dx * dx + dy * dy) * 0.65;
          return `M${s.x},${s.y} A${dr},${dr} 0 0,1 ${t.x},${t.y}`;
        });
        node.attr('transform', (d) => `translate(${d.x!},${d.y!})`);
      });

    return () => { sim.stop(); };
  }, [rawGraph]);

  return (
    <div className="relative w-full rounded-lg border border-edge bg-base overflow-hidden">
      {/* Controls bar */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-edge bg-panel">
        <div className="flex items-center gap-5 font-mono text-[10px] text-sub">
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-3 w-3 rounded-full bg-[#DC6B00] border-2 border-white shadow-sm" />
            MP Node
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#138808] border-2 border-white shadow-sm" />
            IDA / District Node
          </span>
          <span className="text-mut">Arc thickness = high-risk alert volume · Drag to rearrange · Scroll to zoom</span>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            onClick={zoomIn}
            className="rounded border border-edge bg-panel2 px-2.5 py-1 font-mono text-[10px] text-sub hover:text-fg hover:bg-edge/30 transition-colors"
          >
            + Zoom
          </button>
          <button
            onClick={zoomOut}
            className="rounded border border-edge bg-panel2 px-2.5 py-1 font-mono text-[10px] text-sub hover:text-fg hover:bg-edge/30 transition-colors"
          >
            − Zoom
          </button>
          <button
            onClick={resetZoom}
            className="rounded border border-[#DC6B00]/40 bg-[#DC6B00]/8 px-2.5 py-1 font-mono text-[10px] text-[#DC6B00] hover:bg-[#DC6B00]/15 transition-colors font-semibold"
          >
            Reset View
          </button>
        </div>
      </div>

      <svg
        ref={svgRef}
        className="w-full h-[440px] cursor-grab active:cursor-grabbing"
        role="img"
        aria-label="MP–IDA exposure and concentration network"
      />

      {/* Hover tooltip */}
      {hoveredNode && (
        <div className="pointer-events-none absolute bottom-4 left-4 rounded-lg border border-edge bg-white px-4 py-3 font-mono text-xs shadow-xl">
          <div className="flex items-center gap-2 mb-1">
            <span
              className="inline-block h-3 w-3 rounded-full border-2 border-white"
              style={{ background: hoveredNode.kind === 'mp' ? '#DC6B00' : '#138808' }}
            />
            <span className="text-[13px] font-bold text-fg">{hoveredNode.name}</span>
          </div>
          <div className="text-sub text-[11px]">
            {hoveredNode.kind === 'mp' ? 'Member of Parliament' : 'District Authority (IDA)'}
          </div>
          <div className="mt-1 font-semibold" style={{ color: hoveredNode.workCount >= 5 ? '#B91C1C' : '#B45309' }}>
            {hoveredNode.workCount} high-risk {hoveredNode.workCount === 1 ? 'work' : 'works'} flagged
          </div>
        </div>
      )}
    </div>
  );
}

export function MinistryView({ topbar }: { topbar: ReactNode }) {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [alerts, setAlerts] = useState<AlertRow[]>([]);
  const [er, setEr] = useState<string | null>(null);
  const [sortField, setSortField] = useState<string>('risk_score');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  useEffect(() => {
    (async () => {
      try {
        const s  = await apiFetch<DashboardSummary>(`${API_BASE}/dashboard/summary?role=ministry`);
        const al = await apiFetch<{ alerts: AlertRow[] }>(`${API_BASE}/alerts?tier=High&limit=50`);
        setData(s);
        setAlerts(al.alerts);
      } catch (e) {
        setEr((e as Error).message);
      }
    })();
  }, []);

  const handleSort = (field: string) => {
    if (sortField === field) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else { setSortField(field); setSortDir('desc'); }
  };

  const sortedAlerts = useMemo(() => {
    return [...alerts].sort((a, b) => {
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
  }, [alerts, sortField, sortDir]);

  // Merge mock state risk with API data
  const stateRiskData = useMemo(() => {
    const fromApi = data?.top_states_by_high ?? {};
    // Use API data if available, otherwise fallback to mock
    return Object.keys(MOCK_STATE_RISK).length > 0 && Object.keys(fromApi).length === 0
      ? MOCK_STATE_RISK
      : { ...MOCK_STATE_RISK, ...fromApi };
  }, [data]);

  const t = data?.totals;
  return (
    <>
      {topbar}
      {er && (
        <div className="mb-4 rounded-lg border border-tier-high/40 bg-tier-high/8 px-3 py-2 font-mono text-xs text-tier-high">
          Cannot reach backend — running on dynamic mock data ({esc(er)})
        </div>
      )}

      <div className="mb-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Stat label="Total Works Monitored (National)" value={(t?.works ?? '—').toLocaleString?.('en-IN') ?? t?.works ?? '—'} />
        <Stat label="High Risk Flagged"     value={(t?.high_works     ?? '—').toLocaleString?.('en-IN') ?? t?.high_works     ?? '—'} tone="high" />
        <Stat label="Hard Rule Breaches"    value={(t?.hard_violations ?? '—').toLocaleString?.('en-IN') ?? t?.hard_violations ?? '—'} tone="med"  />
        <Stat label="Total Sanctioned Value" value={t ? '₹' + Math.round(t.total_sanctioned).toLocaleString('en-IN') : '—'} />
      </div>

      {/* Geographic density map + tier donut */}
      <div className="mb-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Panel title="Geographic Risk Density Map — All States" className="lg:col-span-2 p-3">
          <IndiaMap
            data={stateRiskData}
            subtitle="Click any state to highlight · Hover for details · Darker = more flagged works"
            colorHigh="#B91C1C"
          />
        </Panel>
        <div className="space-y-4">
          <Panel title="National Risk-Tier Distribution" className="p-3">
            <TierDonut data={data} />
          </Panel>
          <Panel title="Top Flagged Districts" className="p-3">
            <div className="space-y-1.5">
              {Object.entries(data?.districts_by_risk ?? { Bareilly:42,Lucknow:38,Varanasi:31,Gorakhpur:27,Kanpur:24,Agra:19 })
                .sort(([,a],[,b]) => b - a)
                .slice(0, 6)
                .map(([dist, n], i) => (
                  <div key={dist} className="flex items-center gap-2">
                    <span className="font-mono text-[9px] text-mut w-4">{i+1}.</span>
                    <div className="flex-1">
                      <div className="flex justify-between font-mono text-[11px]">
                        <span className="text-fg font-semibold">{dist}</span>
                        <span className="text-tier-high font-bold">{n}</span>
                      </div>
                      <div className="mt-0.5 h-1 rounded-full bg-panel2 overflow-hidden">
                        <div className="h-full bg-tier-high/70 rounded-full" style={{ width: `${Math.min(100, n/42*100)}%` }} />
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          </Panel>
        </div>
      </div>

      {/* Per-state bar chart */}
      <Panel title="High-Risk Works by State — All States" className="mb-4 p-3">
        <NationalBars data={data} />
      </Panel>

      <div className="mb-4">
        <Panel title="Interactive MP ↔ IDA Exposure & Concentration Network" className="p-0 overflow-hidden">
          <MpNetwork alerts={alerts} />
        </Panel>
      </div>

      <Panel title="National High-Risk Alerts Register — Top Priority Works" className="mt-5 overflow-x-auto">
        <table className="w-full border-collapse text-left">
          <thead className="bg-panel2 border-b border-edge">
            <tr>
              <SortTh label="Work ID"      field="work_id"              currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <SortTh label="Risk Score"   field="risk_score"           currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <SortTh label="Tier"         field="risk_tier"            currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <SortTh label="State"        field="state"                currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <SortTh label="IDA / District" field="ida"               currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <SortTh label="MP Name"      field="mp_name"              currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <SortTh label="Category"     field="work_category_suffix" currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <SortTh label="Sanction Amt" field="sanction_amount"      currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <SortTh label="Status"       field="work_status"          currentSort={sortField} currentDir={sortDir} onSort={handleSort} />
              <th className="px-3.5 py-2.5 text-left font-mono text-[10px] uppercase tracking-widest text-sub whitespace-nowrap">Work Description & SHAP Reason</th>
            </tr>
          </thead>
          <tbody>
            {sortedAlerts.map((a) => (
              <tr key={a.work_id} className="border-t border-edge/60 hover:bg-panel2/70 transition-colors">
                <td className={idCell}>{esc(a.work_id)}</td>
                <td className={tdNowrap}>
                  <TierDot tier={a.risk_tier} />
                  <span className="font-mono font-bold" style={{ color: riskColor(a.risk_tier) }}>
                    {Number(a.risk_score).toFixed(1)}
                  </span>
                </td>
                <td className={tdNowrap}><span className="font-mono text-xs text-sub">{a.risk_tier}</span></td>
                <td className={`${tdNowrap} font-mono text-xs text-sub`}>{esc(a.state || 'UP')}</td>
                <td className={`${tdNowrap} font-semibold text-fg`}>{esc(a.ida || 'Bareilly')}</td>
                <td className={`${tdNowrap} text-fg font-semibold`}>{esc(a.mp_name || '—')}</td>
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
            {!sortedAlerts.length && (
              <tr>
                <td colSpan={10} className="border-t border-edge/60">
                  <Empty msg="No national alerts loaded." />
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Panel>
    </>
  );
}
