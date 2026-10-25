import { Cloud, CloudOff, CloudRain, Sun, Wind } from 'lucide-react';
import { useState } from 'react';
import { weatherOptions, type WeatherState } from '../data/farm';

const weatherCopy: Record<WeatherState, { title: string; subtitle: string; icon: typeof Sun; className: string }> = {
  SUNNY: { title: 'Sunny', subtitle: 'No rain expected', icon: Sun, className: 'sunny' },
  CLOUDY: { title: 'Cloudy', subtitle: 'No rain currently', icon: Cloud, className: 'cloudy' },
  RAIN: { title: 'Rain', subtitle: 'Rain detected', icon: CloudRain, className: 'rainy' },
  HEAVY_RAIN: { title: 'Heavy Rain', subtitle: 'Rain intensity: High', icon: Wind, className: 'heavy-rain' },
  NO_DATA: { title: 'Weather unavailable', subtitle: 'Waiting for weather data', icon: CloudOff, className: 'no-weather' },
};

export default function WeatherCard({ compact = false }: { compact?: boolean }) {
  const [state, setState] = useState<WeatherState>('SUNNY');
  const copy = weatherCopy[state];
  const Icon = copy.icon;
  return (
    <section className={`weather-card weather-${copy.className} ${compact ? 'weather-compact' : ''}`} aria-labelledby="weather-title">
      <div className="weather-topline"><span className="eyebrow">FIELD WEATHER</span><span className="sample-note">Sample state</span></div>
      <div className="weather-content" aria-live="polite">
        <div className="weather-visual" aria-hidden="true">
          <Icon size={39} strokeWidth={1.45} className="weather-icon" />
          {state === 'RAIN' || state === 'HEAVY_RAIN' ? <span className="rain-streaks"><i /><i /><i /></span> : null}
        </div>
        <div className="weather-text"><h3 id="weather-title">{copy.title}</h3><p>{copy.subtitle}</p></div>
      </div>
      <label className="weather-preview-control"><span>Preview state</span><select value={state} onChange={(event) => setState(event.target.value as WeatherState)} aria-label="Preview weather state">{weatherOptions.map((option) => <option key={option.state} value={option.state}>{option.label}</option>)}</select></label>
    </section>
  );
}
