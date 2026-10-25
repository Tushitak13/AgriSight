import { useId } from 'react';

export type Tone = 'healthy' | 'warning' | 'info' | 'neutral' | 'critical';

export function StatusPill({ children, tone = 'neutral', dot = true }: { children: React.ReactNode; tone?: Tone; dot?: boolean }) {
  return <span className={`status-pill tone-${tone}`}>{dot && <i aria-hidden="true" />}{children}</span>;
}

export function Sparkline({ values, tone = 'green', className = '' }: { values: number[]; tone?: 'green' | 'amber' | 'blue'; className?: string }) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const points = values.map((value, index) => `${(index / Math.max(values.length - 1, 1)) * 100},${26 - ((value - min) / range) * 21}`).join(' ');
  return (
    <svg className={`sparkline spark-${tone} ${className}`} viewBox="0 0 100 30" preserveAspectRatio="none" aria-hidden="true">
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function ConfidenceBar({ value, label = 'Reliability', tone = 'green' }: { value: number; label?: string; tone?: 'green' | 'amber' }) {
  return (
    <div className="confidence-wrap">
      <div className="confidence-label"><span>{label}</span><strong>{value}%</strong></div>
      <div className="confidence-track" role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={value}>
        <span className={tone === 'amber' ? 'bar-amber' : ''} style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

export function HealthArc({ value }: { value: number }) {
  const id = useId();
  const circumference = 2 * Math.PI * 44;
  const offset = circumference * (1 - value / 100);
  return (
    <div className="health-arc-wrap" role="img" aria-label={`Farm health ${value} out of 100`}>
      <svg viewBox="0 0 112 112" className="health-arc">
        <defs><linearGradient id={id} x1="0" x2="1"><stop stopColor="#71B68C" /><stop offset="1" stopColor="#176B4D" /></linearGradient></defs>
        <circle cx="56" cy="56" r="44" className="arc-track" />
        <circle cx="56" cy="56" r="44" className="arc-value" stroke={`url(#${id})`} strokeDasharray={circumference} strokeDashoffset={offset} />
      </svg>
      <div className="arc-copy"><strong>{value}</strong><span>/ 100</span></div>
    </div>
  );
}

export function TrendChart({ values, labels, color = 'green', ariaLabel, suffix = '' }: { values: number[]; labels?: string[]; color?: 'green' | 'blue' | 'amber'; ariaLabel: string; suffix?: string }) {
  const id = useId();
  const width = 640;
  const height = 210;
  const left = 42;
  const right = 10;
  const top = 14;
  const bottom = 28;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const spread = max - min || 1;
  const x = (i: number) => left + (i / Math.max(1, values.length - 1)) * plotWidth;
  const y = (value: number) => top + (1 - (value - min) / spread) * plotHeight;
  const line = values.map((value, i) => `${x(i)},${y(value)}`).join(' ');
  const area = `${left},${top + plotHeight} ${line} ${left + plotWidth},${top + plotHeight}`;
  const axisValues = [max, min + spread / 2, min];
  const timeLabels = labels ?? ['6 AM', '10 AM', '2 PM', '6 PM', '10 PM', 'Now'];
  const accent = color === 'blue' ? '#6687B9' : color === 'amber' ? '#CB9A45' : '#2D805D';
  return (
    <div className="trend-chart-wrap">
      <svg className="trend-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={ariaLabel}>
        <defs><linearGradient id={id} x1="0" x2="0" y1="0" y2="1"><stop stopColor={accent} stopOpacity=".17" /><stop offset="1" stopColor={accent} stopOpacity="0" /></linearGradient></defs>
        {axisValues.map((value, i) => {
          const gy = top + (i / 2) * plotHeight;
          return <g key={i}><line x1={left} x2={width - right} y1={gy} y2={gy} className="chart-grid" /><text x="2" y={gy + 4} className="chart-axis">{Math.round(value)}{suffix}</text></g>;
        })}
        <polygon points={area} fill={`url(#${id})`} />
        <polyline points={line} fill="none" stroke={accent} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        <circle cx={x(values.length - 1)} cy={y(values[values.length - 1])} r="4.6" fill={accent} stroke="white" strokeWidth="2" />
        {timeLabels.slice(0, 6).map((label, i) => <text key={label} x={left + (i / Math.max(timeLabels.length - 1, 1)) * plotWidth} y={height - 5} textAnchor={i === 0 ? 'start' : i === timeLabels.length - 1 ? 'end' : 'middle'} className="chart-axis">{label}</text>)}
      </svg>
    </div>
  );
}
