import { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, Cloud, Leaf, RefreshCw, ShieldCheck, Upload, WifiOff } from 'lucide-react';

type SensorReading = {
  device_id: string; temperature: number | null; humidity: number | null;
  soil: number | null; rain: number | null; water: number | null; light: number | null;
  device_timestamp: string; received_at: string; missing_fields: string[]; range_flags: string[];
};
type VisionContext = {
  captured_at: string; age_minutes: number; model_name: string; visual_state: string;
  prediction: string; model_confidence: number | null; trusted: boolean;
  is_placeholder_model: boolean; interpretation: string;
};
type TomatoAssessment = {
  device_id: string; crop: string; as_of: string; reading_age_minutes: number;
  data_status: 'available' | 'limited'; missing_inputs: string[]; unreliable_inputs: string[];
  range_flags: string[]; environmental_warnings: string[]; preventive_recommendations: string[];
  disease_probability: number | null; diagnosis: string | null; advisory_only: boolean;
  actuation_enabled: boolean; model_validation_status: string;
  vision_context: VisionContext | null; flai_integration_status: string; flai_integration_note: string;
};

const DEVICE_DEFAULT = 'agrisight-esp32-01';
function formatTime(value?: string) {
  if (!value) return 'Not available';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}
function value(value: number | null, unit = '') {
  return value === null || value === undefined ? 'Unavailable' : `${value}${unit}`;
}

export default function TomatoHealthPage() {
  const [deviceId, setDeviceId] = useState(DEVICE_DEFAULT);
  const [assessment, setAssessment] = useState<TomatoAssessment | null>(null);
  const [reading, setReading] = useState<SensorReading | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<VisionContext | null>(null);
  const [uploadMessage, setUploadMessage] = useState('');

  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const query = `device_id=${encodeURIComponent(deviceId.trim())}`;
      const [riskResponse, sensorResponse] = await Promise.all([
        fetch(`/api/tomato-risk/current?${query}`),
        fetch(`/api/sensors/latest?${query}`),
      ]);
      if (!riskResponse.ok) {
        const body = await riskResponse.json().catch(() => null);
        throw new Error(body?.detail ?? `Risk endpoint returned HTTP ${riskResponse.status}`);
      }
      const riskBody = await riskResponse.json() as TomatoAssessment;
      setAssessment(riskBody);
      if (sensorResponse.ok) setReading(await sensorResponse.json() as SensorReading);
      else setReading(null);
    } catch (e) {
      setAssessment(null);
      setReading(null);
      setError(e instanceof Error ? e.message : 'Unable to connect to the AgriSight backend.');
    } finally {
      setLoading(false);
    }
  }, [deviceId]);

  useEffect(() => { void refresh(); }, [refresh]);

  async function analyzeImage() {
    if (!selectedFile) return;
    setUploading(true);
    setUploadMessage('');
    setUploadResult(null);
    try {
      const form = new FormData();
      form.append('file', selectedFile);
      form.append('device_id', deviceId.trim());
      const response = await fetch('/api/vision/analyze', { method: 'POST', body: form });
      const body = await response.json().catch(() => null);
      if (!response.ok) throw new Error(body?.detail ?? `Image analysis returned HTTP ${response.status}`);
      setUploadResult({
        captured_at: body.captured_at,
        age_minutes: 0,
        model_name: body.model_name,
        visual_state: body.visual_state,
        prediction: body.prediction,
        model_confidence: body.model_confidence,
        trusted: Boolean(body.trusted),
        is_placeholder_model: String(body.model_name ?? '').startsWith('placeholder_'),
        interpretation: String(body.model_name ?? '').startsWith('placeholder_')
          ? 'This is a vegetation-colour heuristic, not a tomato disease classifier.'
          : 'Model output is shown as recorded; disease validity depends on model training and validation.',
      });
      setUploadMessage('Image uploaded and processed by the configured vision pipeline.');
      await refresh();
    } catch (e) {
      setUploadMessage(e instanceof Error ? e.message : 'Image analysis failed.');
    } finally {
      setUploading(false);
    }
  }

  return <div className="page tomato-health-page">
    <div className="page-heading">
      <div><span className="eyebrow">CROP HEALTH · TOMATO</span><h1>Tomato health assessment</h1><p className="page-subtitle">Environmental warnings and optional plant-image review, with data quality shown explicitly.</p></div>
      <span className={`status-pill ${assessment?.data_status === 'available' ? 'tone-healthy' : 'tone-warning'}`}>{assessment ? assessment.data_status === 'available' ? 'Inputs available' : 'Limited data' : 'Not connected'}</span>
    </div>

    <section className="surface-card tomato-control-card">
      <label htmlFor="tomato-device-id">Device ID</label>
      <input id="tomato-device-id" value={deviceId} onChange={(event) => setDeviceId(event.target.value)} maxLength={64} />
      <button type="button" className="button button-primary" onClick={() => void refresh()} disabled={loading || !deviceId.trim()}><RefreshCw size={15} /> {loading ? 'Refreshing…' : 'Refresh readings'}</button>
      <p>Choose the device ID that is sending sensor readings to this backend. An ESP32 that is disconnected will show its last stored reading as stale.</p>
    </section>

    {error && <div className="tomato-alert tomato-alert-error" role="alert"><WifiOff size={18} /><div><strong>Backend data unavailable</strong><p>{error}. Confirm the backend is running and the Vite proxy is configured.</p></div></div>}

    {assessment && <>
      <div className={`tomato-alert ${assessment.data_status === 'available' ? 'tomato-alert-info' : 'tomato-alert-warning'}`} role="status">
        {assessment.data_status === 'available' ? <CheckCircle2 size={19} /> : <AlertTriangle size={19} />}
        <div><strong>{assessment.data_status === 'available' ? 'Sensor inputs appear available' : 'Do not rely on this as a current assessment'}</strong>
          <p>Latest sensor timestamp: {formatTime(assessment.as_of)} · {assessment.reading_age_minutes.toFixed(1)} minutes old. Data status is {assessment.data_status}.</p></div>
      </div>

      <section className="tomato-sensor-grid" aria-label="Latest sensor values">
        <article className="surface-card tomato-metric"><span>Temperature</span><strong>{value(reading?.temperature ?? null, ' °C')}</strong></article>
        <article className="surface-card tomato-metric"><span>Relative humidity</span><strong>{value(reading?.humidity ?? null, '%')}</strong></article>
        <article className="surface-card tomato-metric"><span>Soil sensor · raw</span><strong>{value(reading?.soil ?? null)}</strong></article>
        <article className="surface-card tomato-metric"><span>Rain sensor · raw</span><strong>{value(reading?.rain ?? null)}</strong></article>
        <article className="surface-card tomato-metric"><span>Water sensor · raw</span><strong>{value(reading?.water ?? null)}</strong></article>
        <article className="surface-card tomato-metric"><span>Light sensor · reported</span><strong>{value(reading?.light ?? null)}</strong></article>
      </section>
      <p className="tomato-caption">Soil, rain, water, and light values are displayed as reported by the device; they are not assumed to be calibrated physical measurements.</p>

      <section className="tomato-two-column">
        <article className="surface-card tomato-content-card"><div className="tomato-card-title"><Cloud size={19} /><div><span className="eyebrow">ENVIRONMENT</span><h2>Environmental warnings</h2></div></div>
          <ul className="tomato-list">{assessment.environmental_warnings.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}</ul>
        </article>
        <article className="surface-card tomato-content-card"><div className="tomato-card-title"><Leaf size={19} /><div><span className="eyebrow">PREVENTION</span><h2>Suggested checks</h2></div></div>
          {assessment.preventive_recommendations.length ? <ul className="tomato-list">{assessment.preventive_recommendations.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}</ul> : <p>No additional suggestions were returned.</p>}
        </article>
      </section>

      <section className="surface-card tomato-content-card"><div className="tomato-card-title"><ShieldCheck size={19} /><div><span className="eyebrow">EVIDENCE QUALITY</span><h2>What the system can conclude</h2></div></div>
        <div className="tomato-evidence-grid"><div><span>Missing inputs</span><strong>{assessment.missing_inputs.length ? assessment.missing_inputs.join(', ') : 'None reported'}</strong></div><div><span>Unreliable inputs</span><strong>{assessment.unreliable_inputs.length ? assessment.unreliable_inputs.join(', ') : 'None flagged'}</strong></div><div><span>Range flags</span><strong>{assessment.range_flags.length ? assessment.range_flags.join(', ') : 'None reported'}</strong></div></div>
        <p className="tomato-caption">Disease probability: unavailable. Diagnosis: unavailable. These provisional rules are not validated to predict tomato disease.</p>
      </section>

      <section className="surface-card tomato-content-card"><div className="tomato-card-title"><Upload size={19} /><div><span className="eyebrow">PLANT IMAGE</span><h2>Upload a leaf image</h2></div></div>
        <p>Choose a JPEG, PNG, or WEBP image. It will be sent to the existing backend vision endpoint and stored according to backend configuration.</p>
        <div className="tomato-upload-row"><input aria-label="Select plant image" type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)} /><button className="button button-primary" type="button" disabled={!selectedFile || uploading || !deviceId.trim()} onClick={() => void analyzeImage()}><Upload size={15} /> {uploading ? 'Analyzing…' : 'Upload and analyze'}</button></div>
        {uploadMessage && <p className="tomato-upload-message" role="status">{uploadMessage}</p>}
        {uploadResult && <div className="tomato-vision-result"><strong>Recorded vision output: {uploadResult.prediction} · {uploadResult.visual_state}</strong><span>Model: {uploadResult.model_name} · confidence: {uploadResult.model_confidence === null ? 'not supplied' : `${Math.round(uploadResult.model_confidence * 100)}%`} · trusted: {String(uploadResult.trusted)}</span><p>{uploadResult.interpretation}</p></div>}
        {assessment.vision_context && <div className="tomato-vision-result"><strong>Latest stored observation: {assessment.vision_context.prediction} · {assessment.vision_context.visual_state}</strong><span>Captured: {formatTime(assessment.vision_context.captured_at)} · model: {assessment.vision_context.model_name}</span><p>{assessment.vision_context.interpretation}</p></div>}
      </section>

      <div className="tomato-alert tomato-alert-warning"><AlertTriangle size={19} /><div><strong>FLAI disease decision integration is deliberately gated</strong><p>{assessment.flai_integration_note} FLAI's existing endpoint remains available separately; no uncalibrated disease evidence is being submitted as a probability.</p></div></div>
      <div className="tomato-safety-note"><ShieldCheck size={16} /><span>Advisory only: hardware actuation is disabled. Pump and relay are not controlled by this feature.</span></div>
    </>}
  </div>;
}
