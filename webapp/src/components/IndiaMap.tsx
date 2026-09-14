import * as d3 from 'd3';
import { useEffect, useRef, useState } from 'react';
import type { GeoPermissibleObjects } from 'd3-geo';
import { INDIA_STATES } from '../data/indiaStates';
import type { StateFeature } from '../data/indiaStates';

interface Props {
  data: Record<string, number>;       // stateName → count
  title?: string;
  subtitle?: string;
  colorHigh?: string;                  // color for max value
  onStateClick?: (name: string, value: number) => void;
}

export function IndiaMap({ data, title, subtitle, colorHigh = '#B91C1C', onStateClick }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; name: string; value: number } | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [dims, setDims] = useState({ w: 600, h: 520 });

  // Responsive sizing
  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0].contentRect.width || 600;
      setDims({ w, h: Math.min(560, w * 0.86) });
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (!svgRef.current) return;
    const { w, h } = dims;

    const svg = d3.select(svgRef.current)
      .attr('width', w)
      .attr('height', h)
      .attr('viewBox', `0 0 ${w} ${h}`);

    svg.selectAll('*').remove();

    // Projection — fit to India bounds
    const projection = d3.geoMercator()
      .fitExtent([[20, 20], [w - 20, h - 20]], INDIA_STATES as unknown as GeoPermissibleObjects);

    const path = d3.geoPath().projection(projection);

    const maxVal = Math.max(1, ...Object.values(data));

    // Color scale: light cream → colorHigh
    const colorScale = d3.scaleSequential()
      .domain([0, maxVal])
      .interpolator(d3.interpolateRgb('#F0F7F0', colorHigh));

    // Dot-grid background
    const defs = svg.append('defs');
    const dotPat = defs.append('pattern')
      .attr('id', 'map-dot-grid')
      .attr('patternUnits', 'userSpaceOnUse')
      .attr('width', 16).attr('height', 16);
    dotPat.append('circle')
      .attr('cx', 8).attr('cy', 8).attr('r', 0.8)
      .attr('fill', '#D1E5D1');

    svg.append('rect')
      .attr('width', w).attr('height', h)
      .attr('fill', 'url(#map-dot-grid)');

    const g = svg.append('g');

    // Draw states
    g.selectAll('path')
      .data(INDIA_STATES.features as StateFeature[])
      .join('path')
      .attr('d', (f) => path(f.geometry as GeoPermissibleObjects) ?? '')
      .attr('fill', (f) => {
        const v = data[f.properties.name] ?? 0;
        return v > 0 ? colorScale(v) : '#EDF4ED';
      })
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.2)
      .attr('stroke-linejoin', 'round')
      .style('cursor', 'pointer')
      .style('transition', 'opacity 0.15s')
      .on('mouseenter', function (event: MouseEvent, f: StateFeature) {
        d3.select(this).attr('stroke', '#0C190C').attr('stroke-width', 2);
        const val = data[f.properties.name] ?? 0;
        const rect = svgRef.current!.getBoundingClientRect();
        setTooltip({
          x: event.clientX - rect.left,
          y: event.clientY - rect.top,
          name: f.properties.name,
          value: val,
        });
      })
      .on('mousemove', function (event: MouseEvent) {
        const rect = svgRef.current!.getBoundingClientRect();
        setTooltip((t) => t ? { ...t, x: event.clientX - rect.left, y: event.clientY - rect.top } : t);
      })
      .on('mouseleave', function (_, f: StateFeature) {
        d3.select(this)
          .attr('stroke', f.properties.name === selected ? '#DC6B00' : '#fff')
          .attr('stroke-width', f.properties.name === selected ? 2.5 : 1.2);
        setTooltip(null);
      })
      .on('click', function (_, f: StateFeature) {
        const name = f.properties.name;
        setSelected((s) => s === name ? null : name);
        onStateClick?.(name, data[name] ?? 0);
      });

    // Selected state highlight
    if (selected) {
      g.selectAll('path')
        .filter((f) => (f as StateFeature).properties.name === selected)
        .attr('stroke', '#DC6B00')
        .attr('stroke-width', 2.5);
    }

    // State code labels for larger states only
    const LABEL_STATES = new Set([
      'Rajasthan','Gujarat','Madhya Pradesh','Maharashtra','Uttar Pradesh',
      'Bihar','West Bengal','Odisha','Chhattisgarh','Karnataka','Andhra Pradesh',
      'Tamil Nadu','Telangana','Assam','Jharkhand','Kerala',
    ]);

    g.selectAll('text')
      .data(INDIA_STATES.features.filter((f) => LABEL_STATES.has(f.properties.name)) as StateFeature[])
      .join('text')
      .attr('x', (f) => {
        const c = path.centroid(f.geometry as GeoPermissibleObjects);
        return c[0] || 0;
      })
      .attr('y', (f) => {
        const c = path.centroid(f.geometry as GeoPermissibleObjects);
        return c[1] || 0;
      })
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'middle')
      .attr('fill', (f) => {
        const v = data[f.properties.name] ?? 0;
        return v > maxVal * 0.5 ? '#fff' : '#375437';
      })
      .attr('font-family', 'IBM Plex Mono, monospace')
      .attr('font-size', 8)
      .attr('font-weight', '700')
      .attr('pointer-events', 'none')
      .text((f) => f.properties.code);

  }, [data, dims, colorHigh, selected, onStateClick]);

  const maxVal = Math.max(1, ...Object.values(data));

  return (
    <div ref={containerRef} className="relative w-full">
      {(title || subtitle) && (
        <div className="mb-2">
          {title && <div className="font-mono text-[11px] uppercase tracking-widest text-sub font-bold">{title}</div>}
          {subtitle && <div className="font-mono text-[10px] text-mut mt-0.5">{subtitle}</div>}
        </div>
      )}

      <div className="relative overflow-hidden rounded-lg border border-edge bg-base">
        <svg ref={svgRef} className="block w-full" />

        {/* Tooltip */}
        {tooltip && (
          <div
            className="pointer-events-none absolute z-10 rounded border border-edge bg-white px-3 py-2 shadow-lg"
            style={{ left: Math.min(tooltip.x + 10, dims.w - 160), top: Math.max(tooltip.y - 40, 0) }}
          >
            <div className="font-mono text-[11px] font-bold text-fg">{tooltip.name}</div>
            <div className="font-mono text-[10px] text-sub">
              {tooltip.value > 0
                ? `High-risk: ${tooltip.value.toLocaleString('en-IN')}`
                : 'No flagged works'}
            </div>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="mt-2 flex items-center gap-2">
        <div className="font-mono text-[9px] text-mut uppercase tracking-widest">Risk Density:</div>
        <div className="flex items-center gap-1">
          <div className="h-2.5 w-20 rounded-sm" style={{
            background: `linear-gradient(to right, #F0F7F0, ${colorHigh})`,
          }} />
        </div>
        <div className="font-mono text-[9px] text-mut">0</div>
        <div className="font-mono text-[9px] text-mut ml-auto">
          Max: {maxVal.toLocaleString('en-IN')} flagged
        </div>
      </div>

      {selected && (
        <div className="mt-2 flex items-center gap-2 rounded border border-[#DC6B00]/40 bg-[#DC6B00]/8 px-3 py-1.5">
          <span className="font-mono text-[11px] text-[#DC6B00] font-bold">
            Selected: {selected} — {(data[selected] ?? 0).toLocaleString('en-IN')} high-risk works
          </span>
          <button
            onClick={() => setSelected(null)}
            className="ml-auto font-mono text-[10px] text-sub hover:text-fg"
          >
            ✕ Clear
          </button>
        </div>
      )}
    </div>
  );
}
