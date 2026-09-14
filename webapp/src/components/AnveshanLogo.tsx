export function AnveshanLogo({ size = 130 }: { size?: number }) {
  const petals = Array.from({ length: 16 }, (_, i) => i * 22.5);
  const dots8  = Array.from({ length: 8  }, (_, i) => i * 45);
  const rays   = Array.from({ length: 24 }, (_, i) => i * 15);
  const cx = 100, cy = 100;

  return (
    <svg width={size} height={size} viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="anvEyeGrad" cx="50%" cy="40%" r="60%">
          <stop offset="0%" stopColor="#4AA8D0" />
          <stop offset="100%" stopColor="#1A5BA0" />
        </radialGradient>
      </defs>

      {/* 16 outer saffron petals */}
      {petals.map((deg) => (
        <ellipse key={deg} cx={cx} cy={16} rx={7} ry={14} fill="#DC8A0A"
          transform={`rotate(${deg} ${cx} ${cy})`} />
      ))}

      {/* Tricolor concentric rings */}
      <circle cx={cx} cy={cy} r={76} fill="#FF9933" />
      <circle cx={cx} cy={cy} r={67} fill="#FFFFFF" />
      <circle cx={cx} cy={cy} r={58} fill="#138808" />

      {/* Dashed teal border */}
      <circle cx={cx} cy={cy} r={52} fill="none" stroke="#0C7A8A"
        strokeWidth={2} strokeDasharray="4 2.5" />

      {/* 8 accent dots */}
      {dots8.map((deg) => {
        const rad = (deg - 90) * Math.PI / 180;
        return (
          <circle key={deg} cx={cx + Math.cos(rad) * 52} cy={cy + Math.sin(rad) * 52}
            r={2.5} fill="#0C7A8A" />
        );
      })}

      {/* Inner white circle */}
      <circle cx={cx} cy={cy} r={48} fill="white" />

      {/* Radial sun-rays */}
      {rays.map((deg) => {
        const rad = (deg - 90) * Math.PI / 180;
        return (
          <line key={deg}
            x1={cx + Math.cos(rad) * 22} y1={cy + Math.sin(rad) * 22}
            x2={cx + Math.cos(rad) * 45} y2={cy + Math.sin(rad) * 45}
            stroke="#E0C890" strokeWidth={0.8} />
        );
      })}

      {/* Outer diamond (saffron) */}
      <polygon
        points={`${cx},${cy - 32} ${cx + 22},${cy - 10} ${cx},${cy + 12} ${cx - 22},${cy - 10}`}
        fill="#FF9933" stroke="#DC8A0A" strokeWidth={1}
      />

      {/* Inner diamond (white/teal border) */}
      <polygon
        points={`${cx},${cy - 23} ${cx + 15},${cy - 8} ${cx},${cy + 7} ${cx - 15},${cy - 8}`}
        fill="white" stroke="#0C7A8A" strokeWidth={1.5}
      />

      {/* Eye */}
      <circle cx={cx} cy={cy - 8} r={10} fill="#E8F5F8" stroke="#0C7A8A" strokeWidth={1.2} />
      <circle cx={cx} cy={cy - 8} r={6.5} fill="url(#anvEyeGrad)" />
      <circle cx={cx} cy={cy - 8} r={3}   fill="#0A1A35" />
      <circle cx={cx - 2.5} cy={cy - 11} r={1.8} fill="white" opacity={0.85} />
      <circle cx={cx + 1.5} cy={cy - 11} r={0.9} fill="white" opacity={0.6}  />

      {/* ANVESHAN text */}
      <text x={cx} y={cy + 22} textAnchor="middle"
        fontFamily="'IBM Plex Mono', monospace" fontWeight="800"
        fontSize={9.5} fill="#0C2B0C" letterSpacing="2.5">
        ANVESHAN
      </text>

      {/* Devanagari */}
      <text x={cx} y={cy + 33} textAnchor="middle"
        fontFamily="serif" fontWeight="600"
        fontSize={6.5} fill="#375437">
        अन्वेषण • ए आई
      </text>

      {/* Platform subtitle */}
      <text x={cx} y={cy + 43} textAnchor="middle"
        fontFamily="'IBM Plex Mono', monospace" fontWeight="400"
        fontSize={4.2} fill="#7A967A" letterSpacing="0.8">
        INTELLIGENT RISK &amp; AUDIT PLATFORM
      </text>
    </svg>
  );
}
