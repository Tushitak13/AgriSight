import type { SensorReading } from '../data/farm';
import { Sparkline, StatusPill } from './Visuals';

export default function SensorCard({ sensor, onClick, selected = false, compact = false }: { sensor: SensorReading; onClick?: () => void; selected?: boolean; compact?: boolean }) {
  const Icon = sensor.Icon;
  const content = (
    <>
      <div className="sensor-card-top"><span className="sensor-icon"><Icon size={18} strokeWidth={1.8} /></span><span className="sensor-updated">{sensor.updated}</span></div>
      <div className="sensor-name">{sensor.name}</div>
      <div className="sensor-reading"><strong>{sensor.value}</strong><span>{sensor.unit}</span></div>
      <div className="sensor-card-bottom"><StatusPill tone={sensor.tone}>{sensor.status}</StatusPill><Sparkline values={sensor.series} tone={sensor.tone === 'warning' ? 'amber' : sensor.tone === 'info' ? 'blue' : 'green'} /></div>
      {!compact && <div className="sensor-reliability-line"><span>Sensor reliability</span><strong>{sensor.reliability}%</strong></div>}
    </>
  );
  const className = `sensor-card ${selected ? 'sensor-selected' : ''} ${compact ? 'sensor-compact' : ''}`;
  return onClick ? <button type="button" className={className} onClick={onClick} aria-pressed={selected}>{content}</button> : <article className={className}>{content}</article>;
}
