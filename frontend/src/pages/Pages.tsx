
import { useRef, useState } from 'react';
import {
  ArrowDown, ArrowRight, ArrowUpRight, Check, CheckCircle2, ChevronRight,
  Camera, CircleHelp, Cpu, Droplets, Eye, Leaf, Lightbulb, Radar, ShieldCheck,
  Sprout, Thermometer, Upload, Waves, type LucideIcon,
} from 'lucide-react';
import CameraPreview, { type CameraCapture } from '../components/CameraPreview';
import SensorCard from '../components/SensorCard';
import { farmRepository } from '../data/farmRepository';
import type { SensorId } from '../data/farm';
import { ConfidenceBar, StatusPill, TrendChart } from '../components/Visuals';

interface VisionDetection {
  class_name?: string;
  class?: string;
  label?: string;
  confidence?: number;
  [key: string]: unknown;
}

interface VisionAnalysis {
  model_name?: string | null;
  visual_state?: string | null;
  prediction?: string | null;
  model_confidence?: number | null;
  effective_confidence?: number | null;
  trusted?: boolean;
  detections?: VisionDetection[];
  detail?: string;
  message?: string;
}

function PageHeading({ eyebrow, title, description, children }: { eyebrow: string; title: string; description: string; children?: React.ReactNode }) {
  return <div className="page-heading"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p className="page-subtitle">{description}</p></div>{children && <div className="page-heading-actions">{children}</div>}</div>;
}

export function LiveSensorsPage() {
  const [selectedId, setSelectedId] = useState<SensorId>('soil');
  const sensors = farmRepository.getSensors();
  const selected = sensors.find((sensor) => sensor.id === selectedId)!;

  return <div className="page">
    <PageHeading eyebrow="MONITOR" title="Live sensor monitoring" description="A clear read on every sensor in your field.">
      <StatusPill tone="healthy">All systems operational · sample</StatusPill>
    </PageHeading>
    <div className="inline-note"><ShieldCheck size={17} /><span><strong>Demo readings</strong> · Connect field sensors to replace these sample values with live data.</span></div>
    <section className="sensor-grid-full" aria-label="Sample sensor readings">
      {sensors.map((sensor) => <SensorCard key={sensor.id} sensor={sensor} onClick={() => setSelectedId(sensor.id)} selected={sensor.id === selectedId} />)}
    </section>
    <SystemStateExamples />
    <section className="surface-card sensor-detail-panel" aria-live="polite">
      <div className="card-heading"><div><span className="eyebrow">SENSOR DETAIL</span><h2>{selected.name}</h2><p className="muted-copy">{selected.detail}</p></div><StatusPill tone={selected.tone}>{selected.status}</StatusPill></div>
      <div className="sensor-detail-grid">
        <div className="sensor-detail-reading"><strong>{selected.value}<small>{selected.unit}</small></strong><span>Current sample reading</span></div>
        <div className="sensor-detail-reliability"><div className="reliability-heading"><span><ShieldCheck size={16} /> Sensor reliability</span><strong>{selected.reliability}%</strong></div><ConfidenceBar value={selected.reliability} label="Sensor reliability" /><p>{selected.reliabilityText} · checked for stability, range validity, missing data and sudden changes.</p></div>
        <div className="sensor-detail-updated"><span>Last updated</span><strong>{selected.updated}</strong><span>Sample data</span></div>
      </div>
      <div className="sensor-chart-heading"><strong>Recent trend</strong><span>Past 24 hours · illustrative sample</span></div>
      <TrendChart values={selected.series} ariaLabel={`${selected.name} illustrative sample trend`} suffix={selected.unit === '%' ? '%' : ''} />
    </section>
  </div>;
}

export function CameraPage() {
  const [recentCapture, setRecentCapture] = useState<CameraCapture | null>(null);
  const [analysis, setAnalysis] = useState<VisionAnalysis | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState('');
  const [deviceId, setDeviceId] = useState('agrisight-esp32-01');
  const [sourceName, setSourceName] = useState('');
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadedUrlRef = useRef<string | null>(null);

  function clearPreviousUploadUrl() {
    if (uploadedUrlRef.current) {
      URL.revokeObjectURL(uploadedUrlRef.current);
      uploadedUrlRef.current = null;
    }
  }

  function handleCapture(capture: CameraCapture) {
    clearPreviousUploadUrl();
    setRecentCapture(capture);
    setSourceName('Webcam capture');
    setAnalysis(null);
    setAnalysisComplete(false);
    setError('');
  }

  function handleFileSelect(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setError('');
    setAnalysis(null);
    setAnalysisComplete(false);

    if (!file.type.startsWith('image/')) {
      setError('Please select an image file.');
      event.target.value = '';
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setError('The image is larger than 10 MB. Please choose a smaller image.');
      event.target.value = '';
      return;
    }

    clearPreviousUploadUrl();

    const url = URL.createObjectURL(file);
    uploadedUrlRef.current = url;

    setRecentCapture({
      url,
      blob: file,
      capturedAt: new Intl.DateTimeFormat(undefined, {
        hour: 'numeric',
        minute: '2-digit',
      }).format(new Date()),
    });

    setSourceName(file.name);
    event.target.value = '';
  }

  async function analyzeImage() {
    if (!recentCapture) {
      setError('Capture an image or upload a plant photo first.');
      return;
    }

    setAnalyzing(true);
    setError('');
    setAnalysis(null);
    setAnalysisComplete(false);

    try {
      const formData = new FormData();
      const filename = sourceName && sourceName !== 'Webcam capture'
        ? sourceName
        : 'plant-capture.jpg';

      formData.append('file', recentCapture.blob, filename);
      formData.append('device_id', deviceId.trim() || 'agrisight-esp32-01');

      const response = await fetch('/api/vision/analyze', {
        method: 'POST',
        body: formData,
      });

      const rawResponse = await response.text();
      let result: VisionAnalysis;

      try {
        result = JSON.parse(rawResponse) as VisionAnalysis;
      } catch {
        throw new Error(
          response.ok
            ? 'The server returned an unexpected response. Check the backend API.'
            : `Analysis failed with HTTP ${response.status}. Check that the backend is running.`,
        );
      }

      if (!response.ok) {
        throw new Error(
          result.detail ||
          result.message ||
          `Analysis failed with HTTP ${response.status}.`,
        );
      }

      setAnalysis(result);
      setAnalysisComplete(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Could not analyze the image. Check your backend connection.',
      );
    } finally {
      setAnalyzing(false);
    }
  }

  function formatConfidence(value: number | null | undefined) {
    if (value == null || !Number.isFinite(value)) return 'Not provided';
    return `${Math.round((value <= 1 ? value * 100 : value))}%`;
  }

  return <div className="page">
    <PageHeading
      eyebrow="MONITOR"
      title="Crop camera"
      description="Capture a plant image or upload a photo to request analysis from AgriSight."
    >
      <StatusPill tone={analysisComplete ? 'healthy' : 'warning'}>
        {analysisComplete ? 'Analysis received' : 'Analysis on demand'}
      </StatusPill>
    </PageHeading>

    <div className="camera-page-grid">
      <section className="surface-card camera-main-card">
        <div className="card-heading">
          <div>
            <span className="eyebrow">FIELD CAMERA</span>
            <h2>Capture a plant image</h2>
          </div>
          <span className="camera-time">
            <span className="camera-indicator" />
            {recentCapture ? `Captured ${recentCapture.capturedAt}` : 'Ready to capture'}
          </span>
        </div>

        <CameraPreview onCapture={handleCapture} />

        <div style={{ marginTop: 20 }}>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/*"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
            aria-label="Choose a plant image"
          />

          <button
            type="button"
            className="button button-soft"
            onClick={() => fileInputRef.current?.click()}
            disabled={analyzing}
          >
            <Upload size={16} />
            Upload plant photo
          </button>

          <p className="muted-copy" style={{ marginTop: 10 }}>
            JPEG, PNG or WebP · Maximum 10 MB. You choose when to send an image for analysis.
          </p>
        </div>

        {recentCapture && (
          <div style={{ marginTop: 20 }}>
            <div className="camera-info-row">
              <span>Selected image</span>
              <strong>{sourceName || 'Plant image'}</strong>
            </div>

            <div className="camera-info-row">
              <span>Device ID</span>
              <strong>{deviceId}</strong>
            </div>

            <label
              htmlFor="vision-device-id"
              style={{ display: 'block', marginTop: 16, marginBottom: 8 }}
            >
              Device ID
            </label>
            <input
              id="vision-device-id"
              value={deviceId}
              onChange={(event) => setDeviceId(event.target.value)}
              disabled={analyzing}
              placeholder="agrisight-esp32-01"
              style={{
                width: '100%',
                boxSizing: 'border-box',
                padding: '10px 12px',
                border: '1px solid var(--border, #d9e2d9)',
                borderRadius: 8,
                background: 'var(--surface, #fff)',
                color: 'inherit',
              }}
            />

            <button
              type="button"
              className="button button-primary"
              onClick={() => void analyzeImage()}
              disabled={analyzing}
              style={{ marginTop: 16 }}
            >
              <Eye size={16} />
              {analyzing ? 'Analyzing image…' : 'Analyze plant image'}
            </button>
          </div>
        )}

        {error && (
          <div
            role="alert"
            style={{
              marginTop: 16,
              padding: 12,
              borderRadius: 8,
              color: '#a52828',
              background: '#fff0f0',
              overflowWrap: 'anywhere',
            }}
          >
            <strong>Could not complete analysis</strong>
            <p style={{ marginBottom: 0 }}>{error}</p>
          </div>
        )}
      </section>

      <aside className="surface-card vision-card">
        <div className="vision-card-icon"><Eye size={18} /></div>
        <span className="eyebrow">VISION ANALYSIS</span>
        <h2>{analysis ? 'Analysis result' : 'Your result will appear here'}</h2>

        <p>
          Results are displayed from the backend response. A model prediction is not
          automatically a verified crop diagnosis.
        </p>

        {!analysis && !analyzing && (
          <div className="vision-empty-state">
            <Radar size={21} />
            <span>{recentCapture ? 'Image ready for analysis' : 'No image analyzed yet'}</span>
          </div>
        )}

        {analyzing && (
          <div className="vision-empty-state" aria-live="polite">
            <Radar size={21} />
            <span>Sending image to AgriSight…</span>
          </div>
        )}

        {analysis && (
          <div style={{ marginTop: 18 }}>
            <div className="camera-info-row">
              <span>Prediction</span>
              <strong>{analysis.prediction || 'Not provided'}</strong>
            </div>

            <div className="camera-info-row">
              <span>Visual state</span>
              <strong>{analysis.visual_state || 'Not provided'}</strong>
            </div>

            <div className="camera-info-row">
              <span>Model</span>
              <strong>{analysis.model_name || 'Not provided'}</strong>
            </div>

            <div className="camera-info-row">
              <span>Model confidence</span>
              <strong>{formatConfidence(analysis.model_confidence)}</strong>
            </div>

            <div className="camera-info-row">
              <span>Effective confidence</span>
              <strong>{formatConfidence(analysis.effective_confidence)}</strong>
            </div>

            <div className="camera-info-row">
              <span>Trusted by backend</span>
              <strong>{analysis.trusted == null ? 'Not provided' : analysis.trusted ? 'Yes' : 'No'}</strong>
            </div>

            <div
              style={{
                marginTop: 16,
                padding: 12,
                borderRadius: 8,
                background: analysis.trusted
                  ? '#edf8ef'
                  : '#fff5e5',
                color: '#344638',
              }}
            >
              <strong>
                {analysis.trusted
                  ? 'Backend marked this result as trusted'
                  : 'Review this result before relying on it'}
              </strong>
              <p style={{ marginBottom: 0, fontSize: 13 }}>
                Trust status is reported by the backend and does not replace field verification.
              </p>
            </div>

            {analysis.detections && analysis.detections.length > 0 && (
              <div style={{ marginTop: 18 }}>
                <h3>Detections</h3>
                <div className="table-scroll">
                  <table className="intervention-table">
                    <thead>
                      <tr>
                        <th scope="col">Class</th>
                        <th scope="col">Confidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analysis.detections.map((detection, index) => (
                        <tr key={`${detection.class_name || detection.class || detection.label || 'detection'}-${index}`}>
                          <td>
                            {detection.class_name ||
                              detection.class ||
                              detection.label ||
                              `Detection ${index + 1}`}
                          </td>
                          <td>{formatConfidence(detection.confidence)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {analysis.detections?.length === 0 && (
              <p className="muted-copy" style={{ marginTop: 14 }}>
                The backend returned no detections.
              </p>
            )}
          </div>
        )}

        <div className="camera-info-row" style={{ marginTop: 20 }}>
          <span>Current source</span>
          <strong>{sourceName || 'No image selected'}</strong>
        </div>
      </aside>
    </div>

    <section className="surface-card recent-observations">
      <div className="card-heading">
        <div>
          <span className="eyebrow">OBSERVATIONS</span>
          <h2>Current observation</h2>
          <p className="muted-copy">
            The image remains in this browser session until you replace it or leave the page.
          </p>
        </div>
        <span className="sample-note">
          {recentCapture ? 'Image selected' : 'Awaiting image'}
        </span>
      </div>

      {recentCapture ? (
        <div className="observation-row">
          <span className="observation-thumb">
            <img src={recentCapture.url} alt="Selected plant for analysis" />
          </span>
          <div className="observation-copy">
            <strong>{sourceName || 'Plant image'}</strong>
            <span>
              {analysisComplete
                ? 'Backend response received'
                : 'Ready to analyze when you choose'}
            </span>
          </div>
          <div className="observation-meta">
            <span>{recentCapture.capturedAt}</span>
            <StatusPill tone={analysisComplete ? 'healthy' : 'info'}>
              {analysisComplete ? 'Analyzed' : 'Not analyzed yet'}
            </StatusPill>
          </div>
        </div>
      ) : (
        <div className="observation-row observation-empty">
          <span className="observation-thumb"><Camera size={18} /></span>
          <div className="observation-copy">
            <strong>Your next capture will appear here</strong>
            <span>Start the camera or upload a plant image to begin.</span>
          </div>
        </div>
      )}
    </section>
  </div>;
}

const decisionSteps: Array<{ title: string; value: string; note: string; Icon: LucideIcon; tone: string }> = [
  { title: 'Sensor data', value: 'Field readings collected', note: 'Soil 38% · Water 1,700 L · Rain none', Icon: Waves, tone: 'tone-sage' },
  { title: 'Sensor reliability', value: '94% · Stable', note: 'Readings are currently trustworthy', Icon: ShieldCheck, tone: 'tone-blue' },
  { title: 'Environmental state', value: 'Soil is dry', note: 'No rain expected · water sufficient', Icon: Thermometer, tone: 'tone-amber' },
  { title: 'Experience memory', value: '8 similar situations', note: 'Similarity-based retrieval found relevant examples', Icon: Sprout, tone: 'tone-violet' },
  { title: 'Crop Resilience Index · CRI', value: '76 / 100', note: 'Sample resilience context', Icon: Leaf, tone: 'tone-sage' },
  { title: 'Adaptive Confidence Index · ACI', value: '91%', note: 'Strong agreement across current evidence', Icon: Radar, tone: 'tone-blue' },
];

export function DecisionPage() {
  return <div className="page">
    <PageHeading eyebrow="INTELLIGENCE" title="Decision center" description="A transparent look at how AgriSight reaches a recommendation."><StatusPill tone="info">Sample reasoning</StatusPill></PageHeading>
    <div className="decision-intro"><span className="decision-intro-icon"><Lightbulb size={20} /></span><p><strong>One clear recommendation, built from several checks.</strong><br />AgriSight first checks the sensor readings, then compares conditions with relevant experience before weighing its confidence.</p></div>
    <section className="decision-flow" aria-label="Sample decision path">
      {decisionSteps.map(({ title, value, note, Icon, tone }, index) => <div className="decision-flow-item" key={title}>
        <article className="decision-node"><span className={`decision-node-icon ${tone}`}><Icon size={19} /></span><div className="decision-node-copy"><span className="eyebrow">STEP {String(index + 1).padStart(2, '0')}</span><h2>{title}</h2><strong>{value}</strong><p>{note}</p></div><span className="decision-node-check"><Check size={15} /></span></article>
        {index < decisionSteps.length - 1 && <div className="flow-connector"><span /><ArrowDown size={14} /></div>}
      </div>)}
      <div className="decision-final"><span className="final-decision-icon"><Droplets size={23} /></span><div><span className="eyebrow">SAFETY-CONSTRAINED DECISION</span><h2>Irrigation recommended</h2><p>Soil is dry, water is sufficient, and no rain is expected in this sample scenario.</p></div><div className="final-confidence"><strong>91%</strong><span>Confidence</span></div></div>
    </section>
    <p className="disclaimer-line"><CircleHelp size={15} /> All figures on this page are illustrative sample values, not live hardware readings.</p>
    <p className="decision-technical-note">Under the hood: Sensor Reliability Engine · Environmental State Engine · Experience Memory Engine · Similarity-based Experience Retrieval · Self-Learning Recalibration.</p>
  </div>;
}

export function ExperiencePage() {
  const experienceEntries = farmRepository.getExperienceEntries();

  return <div className="page">
    <PageHeading eyebrow="INTELLIGENCE" title="Experience memory" description="Learn from what happened before."><StatusPill tone="info">8 similar situations · sample</StatusPill></PageHeading>
    <section className="current-situation surface-card"><div className="current-situation-title"><div className="decision-node-icon tone-sage"><Sprout size={19} /></div><div><span className="eyebrow">CURRENT SITUATION</span><h2>Today in the field</h2></div></div><div className="situation-values"><div><span>Soil</span><strong>36%</strong><StatusPill tone="warning">Dry</StatusPill></div><div><span>Temperature</span><strong>31°C</strong><StatusPill tone="healthy">Normal</StatusPill></div><div><span>Humidity</span><strong>65%</strong><StatusPill tone="healthy">Normal</StatusPill></div><div><span>Rain</span><strong>None</strong><StatusPill tone="neutral">Sunny</StatusPill></div></div><span className="sample-note">Demo data</span></section>
    <div className="section-heading section-heading-spaced"><div><span className="eyebrow">HISTORICAL CONTEXT</span><h2>Similar experiences</h2><p className="muted-copy">Past interventions help AgriSight understand what tends to work.</p></div><span className="similarity-count"><strong>8</strong><span>similar situations found</span></span></div>
    <section className="experience-timeline" aria-label="Historical sample experiences">{experienceEntries.map((entry, index) => <article className="experience-card surface-card" key={entry.date}><div className="experience-timeline-rail"><span className={entry.result === 'Successful' ? 'timeline-dot timeline-good' : 'timeline-dot timeline-warning'} />{index < experienceEntries.length - 1 && <i />}</div><div className="experience-body"><div className="experience-header"><div><span className="eyebrow">{entry.date.toUpperCase()}</span><h3>{entry.action}</h3></div><span className="similarity-badge">{entry.similarity}<small>similar</small></span></div><div className="experience-conditions"><span>{entry.conditions}</span><ArrowRight size={14} /><span>Past intervention</span></div><div className="experience-outcome"><div><span>Outcome</span><strong>{entry.before} <ArrowRight size={13} /> {entry.after}</strong></div><StatusPill tone={entry.result === 'Successful' ? 'healthy' : 'warning'}>{entry.result}</StatusPill></div></div></article>)}</section>
    <NoExperienceExample />
  </div>;
}

export function LearningPage() {
  return <div className="page">
    <PageHeading eyebrow="INTELLIGENCE" title="Self-learning" description="See how AgriSight adjusts its expectations as the field changes."><StatusPill tone="info">Example recalibration</StatusPill></PageHeading>
    <div className="learning-banner"><span className="learning-banner-icon"><Lightbulb size={20} /></span><div><strong>AgriSight updated its expected response for similar conditions.</strong><p>Past outcomes help improve future estimates; they don't replace current sensor checks.</p></div></div>
    <section className="learning-flow" aria-label="Sample prediction learning sequence">
      <LearningStep number="01" eyebrow="PREDICTION" title="Expected soil response" value="30% → 60%" note="What the earlier model expected after irrigation" tone="tone-blue" Icon={Radar} />
      <LearningStep number="02" eyebrow="ACTUAL OUTCOME" title="Measured soil response" value="30% → 48%" note="What happened in a similar sample situation" tone="tone-sage" Icon={Waves} />
      <LearningStep number="03" eyebrow="PREDICTION ERROR" title="A difference to learn from" value="−12%" note="The actual response was lower than expected" tone="tone-amber" Icon={ArrowUpRight} />
      <LearningStep number="04" eyebrow="UPDATED EXPECTATION" title="A more careful estimate" value="Expectation recalibrated" note="Similar conditions will use the new reference" tone="tone-violet" Icon={CheckCircle2} last />
    </section>
    <div className="learning-note surface-card"><ShieldCheck size={18} /><p><strong>Transparent by design.</strong> This is an illustrative learning example. AgriSight does not infer an actual crop response until real intervention and sensor outcome data are connected.</p></div>
  </div>;
}

function LearningStep({ number, eyebrow, title, value, note, tone, Icon, last = false }: { number: string; eyebrow: string; title: string; value: string; note: string; tone: string; Icon: LucideIcon; last?: boolean }) {
  return <div className="learning-step-wrap"><article className="learning-step surface-card"><span className={`learning-step-icon ${tone}`}><Icon size={19} /></span><div className="learning-step-copy"><span className="eyebrow">{eyebrow} · {number}</span><h2>{title}</h2><strong>{value}</strong><p>{note}</p></div><CheckCircle2 size={18} className="learning-step-check" /></article>{!last && <div className="learning-connector"><span /><ArrowDown size={14} /></div>}</div>;
}

const historyTabs = ['Overview', 'Soil', 'Weather', 'Water', 'Interventions'] as const;
type HistoryTab = typeof historyTabs[number];
const rangeOptions = ['24 Hours', '7 Days', '30 Days'] as const;
const historyConfig: Record<Exclude<HistoryTab, 'Interventions'>, { key: keyof ReturnType<typeof farmRepository.getChartSeries>; title: string; value: string; unit: string; color: 'green' | 'blue' | 'amber'; series: string }> = {
  Overview: { key: 'soil', title: 'Soil moisture', value: '38%', unit: '%', color: 'green', series: 'Soil moisture' },
  Soil: { key: 'soil', title: 'Soil moisture', value: '38%', unit: '%', color: 'green', series: 'Soil moisture' },
  Weather: { key: 'temperature', title: 'Temperature', value: '31.4°C', unit: '°C', color: 'blue', series: 'Temperature' },
  Water: { key: 'waterUsage', title: 'Water usage', value: '55 L', unit: 'L', color: 'amber', series: 'Water used' },
};

const historyRangeSeries: Record<keyof ReturnType<typeof farmRepository.getChartSeries>, Record<'7 Days' | '30 Days', number[]>> = {
  soil: { '7 Days': [53, 51, 48, 46, 44, 42, 40, 41, 40, 39, 38, 38], '30 Days': [62, 58, 54, 51, 49, 47, 44, 42, 40, 39, 38, 38] },
  temperature: { '7 Days': [27, 28, 27, 29, 30, 31, 32, 31, 33, 32, 31, 31.4], '30 Days': [26, 27, 29, 28, 30, 31, 30, 32, 34, 32, 31, 31.4] },
  humidity: { '7 Days': [61, 63, 64, 62, 65, 66, 64, 68, 69, 67, 66, 67], '30 Days': [59, 61, 62, 64, 63, 65, 67, 66, 68, 69, 66, 67] },
  water: { '7 Days': [2130, 2070, 2000, 1950, 1880, 1830, 1790, 1750, 1720, 1700, 1700, 1700], '30 Days': [2400, 2320, 2260, 2190, 2120, 2050, 1990, 1900, 1840, 1770, 1730, 1700] },
  waterUsage: { '7 Days': [35, 42, 48, 0, 54, 40, 55, 32, 0, 46, 51, 55], '30 Days': [30, 35, 32, 42, 38, 0, 44, 47, 39, 0, 48, 55] },
};

export function HistoryPage() {
  const [tab, setTab] = useState<HistoryTab>('Overview');
  const [range, setRange] = useState<typeof rangeOptions[number]>('24 Hours');
  const chartSeries = farmRepository.getChartSeries();
  const config = tab === 'Interventions' ? historyConfig.Overview : historyConfig[tab];
  const labels = range === '24 Hours' ? ['6 AM', '10 AM', '2 PM', '6 PM', '10 PM', 'Now'] : range === '7 Days' ? ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Today'] : ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'This week'];
  const rangeValues = range === '24 Hours' ? chartSeries[config.key] : historyRangeSeries[config.key][range];
  const humidityValues = range === '24 Hours' ? chartSeries.humidity : historyRangeSeries.humidity[range];

  return <div className="page">
    <PageHeading eyebrow="ANALYTICS" title="History & trends" description="A simple picture of how field conditions are changing."><span className="sample-note">Demo data</span></PageHeading>
    <div className="history-toolbar">
      <div className="history-tabs" role="tablist" aria-label="Analytics category">
        {historyTabs.map((item) => {
          const selected = tab === item;
          const id = `analytics-tab-${item.toLowerCase()}`;
          return <button key={item} id={id} type="button" role="tab" aria-selected={selected} aria-controls="analytics-panel" tabIndex={selected ? 0 : -1} className={selected ? 'history-tab active' : 'history-tab'} onClick={() => setTab(item)} onKeyDown={(event) => {
            if (!['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) return;
            event.preventDefault();
            const currentIndex = historyTabs.indexOf(item);
            const nextIndex = event.key === 'Home' ? 0 : event.key === 'End' ? historyTabs.length - 1 : (currentIndex + (event.key === 'ArrowRight' ? 1 : -1) + historyTabs.length) % historyTabs.length;
            const nextTab = historyTabs[nextIndex];
            setTab(nextTab);
            document.getElementById(`analytics-tab-${nextTab.toLowerCase()}`)?.focus();
          }}>{item}</button>;
        })}
      </div>
      <div className="range-picker" role="group" aria-label="Time range">
        {rangeOptions.map((item) => <button key={item} type="button" aria-pressed={range === item} className={range === item ? 'range-active' : ''} onClick={() => setRange(item)}>{item}</button>)}
      </div>
    </div>
    <div id="analytics-panel" role="tabpanel" aria-labelledby={`analytics-tab-${tab.toLowerCase()}`} tabIndex={0}>
      {tab === 'Interventions' && <IrrigationEventsTrend />}
      {tab === 'Interventions' ? <InterventionHistory /> : <section className="surface-card analytics-chart-card"><div className="card-heading"><div><span className="eyebrow">{tab === 'Overview' ? 'FIELD TRENDS' : tab.toUpperCase()}</span><h2>{config.title}</h2><p className="muted-copy">{range} · illustrative sample values</p></div><div className="analytics-current"><strong>{config.value}</strong><span>Current sample</span></div></div><TrendChart values={rangeValues} labels={labels} ariaLabel={`${config.series} sample history over ${range}`} color={config.color} suffix={config.unit} /><div className="chart-footer"><span><i className={`legend-dot legend-${config.color}`} />{config.series}</span><span>Updated just now</span></div></section>}
      {tab === 'Weather' && <section className="surface-card analytics-chart-card secondary-analytics"><div className="card-heading"><div><span className="eyebrow">WEATHER</span><h2>Humidity trend</h2><p className="muted-copy">{range} · illustrative sample values</p></div><div className="analytics-current"><strong>67%</strong><span>Current sample</span></div></div><TrendChart values={humidityValues} labels={labels} ariaLabel={`Humidity sample history over ${range}`} color="blue" suffix="%" /><div className="chart-footer"><span><i className="legend-dot legend-blue" />Humidity</span><span>Updated just now</span></div></section>}
      {tab === 'Overview' && <section className="analytics-summary-row"><article className="summary-metric"><span>Temperature</span><strong>31.4°C</strong><StatusPill tone="healthy">Normal</StatusPill></article><article className="summary-metric"><span>Humidity</span><strong>67%</strong><StatusPill tone="healthy">Normal</StatusPill></article><article className="summary-metric"><span>Water available</span><strong>1,700 L</strong><StatusPill tone="healthy">Sufficient</StatusPill></article></section>}
    </div>
  </div>;
}

function InterventionHistory() {
  const interventions = farmRepository.getInterventions();

  return <section className="surface-card intervention-card">
    <div className="card-heading"><div><span className="eyebrow">FIELD ACTIVITY</span><h2>Intervention history</h2><p className="muted-copy">Sample outcomes from recent field decisions.</p></div><StatusPill tone="neutral">3 sample events</StatusPill></div>
    <div className="table-scroll"><table className="intervention-table"><thead><tr><th scope="col">Date</th><th scope="col">Action</th><th scope="col">Before</th><th scope="col">After</th><th scope="col">Result</th></tr></thead><tbody>{interventions.map((item) => <tr key={item.date}><td data-label="Date">{item.date}</td><td data-label="Action">{item.action}</td><td data-label="Before">{item.before}</td><td data-label="After">{item.after}</td><td data-label="Result"><StatusPill tone={item.result === 'Successful' ? 'healthy' : 'warning'}>{item.result}</StatusPill></td></tr>)}</tbody></table></div>
  </section>;
}

export function HardwarePage() {
  const components = [
    { name: 'Soil Sensor', label: 'Moisture', value: '38%', Icon: Droplets },
    { name: 'DHT Sensor', label: 'Temperature & humidity', value: '31.4°C · 67%', Icon: Thermometer },
    { name: 'Rain Sensor', label: 'Rain detection', value: 'No rain', Icon: Waves },
    { name: 'Water Level Sensor', label: 'Available water', value: '1,700 L', Icon: Waves },
    { name: 'Light Sensor', label: 'Ambient light', value: '420 lux', Icon: Lightbulb },
  ];

  return <div className="page">
    <PageHeading eyebrow="SYSTEM" title="Hardware" description="A simple view of the devices and sensors that support field decisions."><StatusPill tone="neutral">Sample status</StatusPill></PageHeading>
    <div className="inline-note"><ShieldCheck size={17} /><span>These are illustrative statuses. No physical hardware is connected to this demo.</span></div>
    <section className="hardware-overview surface-card"><div className="hardware-device-icon"><Cpu size={24} /></div><div className="hardware-device-copy"><span className="eyebrow">CONTROLLER · SAMPLE</span><h2>ESP32</h2><p>Sample last communication <strong>2 seconds ago</strong> · Sample uptime <strong>4h 32m</strong></p></div><StatusPill tone="neutral">Demo connected</StatusPill></section>
    <div className="section-heading section-heading-spaced"><div><span className="eyebrow">FIELD EQUIPMENT</span><h2>Sensor status examples</h2></div><span className="sample-note">Demo data</span></div>
    <section className="hardware-grid">{components.map(({ name, label, value, Icon }) => <article className="hardware-sensor surface-card" key={name}><div className="hardware-sensor-top"><span className="hardware-sensor-icon"><Icon size={17} /></span><StatusPill tone="neutral">Demo connected</StatusPill></div><h3>{name}</h3><p>{label}</p><strong>{value}</strong></article>)}</section>
    <section className="actuator-card surface-card"><div className="actuator-icon"><Cpu size={20} /></div><div><span className="eyebrow">ACTUATOR · SAMPLE</span><h2>Pump</h2><p>Demo ready state only. Pump actions are unavailable until a verified backend and device are connected.</p></div><StatusPill tone="neutral">Demo ready</StatusPill></section>
  </div>;
}

export function SettingsPage() {
  const [units, setUnits] = useState<'Metric' | 'Imperial'>('Metric');
  const [updates, setUpdates] = useState(true);

  return <div className="page">
    <PageHeading eyebrow="SYSTEM" title="Settings" description="A few simple preferences for this AgriSight preview."><span className="sample-note">Saved in this browser session</span></PageHeading>
    <section className="settings-section surface-card"><div className="settings-section-heading"><div className="settings-icon"><Sprout size={18} /></div><div><span className="eyebrow">FIELD PROFILE</span><h2>Field overview</h2><p>Sample field · No connected account or device configuration</p></div></div><div className="settings-row"><div><strong>Measurement units</strong><span>Preview preference only; the illustrative readings remain metric.</span></div><div className="segmented-control" role="group" aria-label="Measurement units">{(['Metric', 'Imperial'] as const).map((unit) => <button key={unit} type="button" aria-pressed={units === unit} className={units === unit ? 'selected' : ''} onClick={() => setUnits(unit)}>{unit}</button>)}</div></div><div className="settings-row"><div><strong>System updates</strong><span>Visual preference only; no messages are sent.</span></div><button type="button" className={`toggle ${updates ? 'toggle-on' : ''}`} aria-pressed={updates} onClick={() => setUpdates((value) => !value)}><span /> <span className="sr-only">{updates ? 'On' : 'Off'}</span></button></div></section>
    <section className="settings-section surface-card"><div className="settings-section-heading"><div className="settings-icon settings-icon-blue"><CircleHelp size={18} /></div><div><span className="eyebrow">ABOUT AGRISIGHT</span><h2>Clear guidance for the growing season.</h2><p>Sample interface · No live sensor, camera or hardware connection is configured.</p></div></div><div className="about-foot"><span>AgriSight dashboard</span><span>Preview build · 1.0</span></div></section>
  </div>;
}

function SystemStateExamples() {
  return <details className="states-details"><summary>See sensor and connection states</summary><div className="system-state-grid">
    <article className="system-state-card"><span className="state-icon state-waiting"><Waves size={16} /></span><div><strong>Waiting for sensor data…</strong><p>No recent reading has arrived yet. AgriSight will show it when available.</p></div></article>
    <article className="system-state-card"><span className="state-icon state-offline"><CircleHelp size={16} /></span><div><strong>Connection lost. Reconnecting…</strong><p>Recent readings remain labelled as sample data until the connection returns.</p></div></article>
    <article className="system-state-card"><span className="state-icon state-unreliable"><ShieldCheck size={16} /></span><div><strong>Sensor reading may be unreliable.</strong><p>AgriSight checks unusual changes and missing readings before using a value.</p></div></article>
  </div></details>;
}

function NoExperienceExample() {
  return <details className="states-details"><summary>Preview the no-history state</summary><div className="empty-experience-state"><span><Sprout size={18} /></span><div><strong>AgriSight hasn't encountered a similar situation yet.</strong><p>As more field observations are recorded, relevant experiences can appear here.</p></div></div></details>;
}

function IrrigationEventsTrend() {
  const eventDays = farmRepository.getInterventions().map((item) => ({ day: item.date, count: item.action === 'Irrigation' ? 1 : 0 }));

  return <section className="surface-card irrigation-events-card"><div className="card-heading"><div><span className="eyebrow">INTERVENTIONS</span><h2>Irrigation events</h2><p className="muted-copy">Counts are derived from the sample history below.</p></div><span className="sample-note">3 sample days</span></div><div className="event-bars" role="img" aria-label="Sample irrigation events: none on October 5, one on October 6, and one on October 7.">{eventDays.map(({ day, count }) => <div className="event-bar-column" key={day}><strong>{count}</strong><span className="event-bar-track"><i style={{ height: count ? '30px' : '5px' }} /></span><small>{day}</small></div>)}</div></section>;
}
