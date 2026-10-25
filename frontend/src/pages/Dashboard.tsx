import { ArrowRight, Camera, Check, Droplets, Leaf, ShieldCheck, Sprout } from 'lucide-react';
import { useState } from 'react';
import { farmRepository } from '../data/farmRepository';
import SensorCard from '../components/SensorCard';
import WeatherCard from '../components/WeatherCard';
import { ConfidenceBar, HealthArc, StatusPill, TrendChart } from '../components/Visuals';

export default function Dashboard() {
  const [showWhy, setShowWhy] = useState(false);
  const dashboardSensors = farmRepository.getDashboardSensors();
  const recommendationReasons = farmRepository.getRecommendationReasons();
  const chartSeries = farmRepository.getChartSeries();
  const cropPreviewUrl = farmRepository.getCameraPreviewUrl();
  const today = new Intl.DateTimeFormat('en-US', { weekday: 'long', month: 'long', day: 'numeric' }).format(new Date()).toUpperCase();
  return (
    <div className="page dashboard-page">
      <div className="page-heading dashboard-heading">
        <div><span className="eyebrow">{today}</span><h1>Good evening, Farmer</h1><p className="page-subtitle">Here’s the latest from your farm.</p></div>
        <StatusPill tone="neutral">Demo status · online</StatusPill>
      </div>

      <section className="hero-grid" aria-label="Farm health and recommendation">
        <article className="health-card">
          <div className="health-card-heading"><div><span className="eyebrow">FARM HEALTH</span><h2>Looking steady</h2></div><span className="health-leaf"><Leaf size={20} /></span></div>
          <div className="health-card-main"><div className="health-copy"><div className="health-score-line"><strong>82</strong><span>/ 100</span></div><StatusPill tone="healthy">Healthy</StatusPill><p>Current environmental conditions are generally supportive.</p></div><HealthArc value={82} /></div>
          <div className="health-support">
            <div><span>Environmental stability</span><strong>Good</strong><i><b style={{ width: '82%' }} /></i></div>
            <div><span>Crop condition</span><strong>Healthy</strong><i><b style={{ width: '86%' }} /></i></div>
            <div><span>Water availability</span><strong>Sufficient</strong><i><b style={{ width: '74%' }} /></i></div>
          </div>
        </article>

        <article className="recommendation-card">
          <div className="recommendation-heading"><span className="recommendation-icon"><Droplets size={21} /></span><span className="eyebrow">AGRISIGHT RECOMMENDS</span><span className="confidence-chip"><ShieldCheck size={14} /> High confidence</span></div>
          <h2>Irrigation<br className="desktop-break" /> recommended</h2>
          <p className="recommendation-copy">Current soil moisture is low and water availability is sufficient.</p>
          <div className="recommendation-confidence"><div><span>Confidence</span><strong>91%</strong></div><ConfidenceBar value={91} label="AgriSight confidence" /></div>
          <p className="confidence-explanation">AgriSight is highly confident in this recommendation.</p>
          <div className="recommendation-actions"><a href="/decisions" className="button button-primary">View decision <ArrowRight size={16} /></a><button type="button" className="button button-soft" onClick={() => setShowWhy((open) => !open)} aria-expanded={showWhy}>{showWhy ? 'Hide why' : 'Why?'}</button></div>
          {showWhy && <div className="why-panel" aria-live="polite"><div className="why-panel-title"><span>Why this recommendation?</span><span className="sample-note">Sample reasoning</span></div><ul>{recommendationReasons.map((reason) => <li key={reason.label}><span>{reason.label}</span><strong>{reason.value}<Check size={13} /></strong></li>)}</ul></div>}
          <span className="rec-footnote"><span className="pulse-dot" /> No rain expected · water sufficient</span>
        </article>
      </section>

      <div className="section-heading"><div><span className="eyebrow">RIGHT NOW</span><h2>Field conditions</h2></div><a href="/sensors" className="text-link">All sensors <ArrowRight size={15} /></a></div>
      <section className="dashboard-reading-grid" aria-label="Current sample sensor readings">{dashboardSensors.map((sensor) => <SensorCard key={sensor.id} sensor={sensor} compact />)}<WeatherCard compact /></section>

      <section className="dashboard-lower-grid">
        <article className="surface-card trend-card">
          <div className="card-heading"><div><span className="eyebrow">SOIL MOISTURE</span><h3>A little drier each day</h3><p className="muted-copy">A steady decline over the last 24 hours</p></div><StatusPill tone="warning">38% · Dry</StatusPill></div>
          <TrendChart values={chartSeries.soil} ariaLabel="Sample soil moisture trend declining to 38 percent" suffix="%" />
          <div className="chart-footer"><span><i className="legend-dot" /> Soil moisture</span><span>Past 24 hours <ArrowRight size={13} /></span></div>
        </article>
        <article className="surface-card camera-card">
          <div className="card-heading"><div><span className="eyebrow">CROP CAMERA</span><h3>A closer look</h3></div><a href="/camera" className="round-link" aria-label="Open crop camera"><ArrowRight size={17} /></a></div>
          <a className="camera-teaser" href="/camera"><img src={cropPreviewUrl} alt="Illustrative sample image from a crop field camera" onError={(event) => { if (!event.currentTarget.src.endsWith('/crop-preview-fallback.svg')) event.currentTarget.src = '/crop-preview-fallback.svg'; }} /><span className="camera-photo-label"><Sprout size={14} /> Illustrative preview</span><span className="camera-overlay"><span><i className="camera-indicator" />Sample crop view</span><span>Field camera</span></span></a>
          <div className="camera-card-meta"><span>Last captured <strong>2 min ago</strong></span></div>
          <div className="camera-card-actions"><a href="/camera" className="button button-primary"><Camera size={14} /> Capture Image</a><a href="/camera" className="button button-soft">Open Camera <ArrowRight size={14} /></a></div>
          <p className="camera-disclaimer">Sample image · not a live camera feed</p>
        </article>
      </section>

      <div className="dashboard-footnote"><span><ShieldCheck size={15} /> This is a sample dashboard</span><span>Connect your field sensors to see live readings</span></div>
    </div>
  );
}
