import { Camera, CameraOff, CircleCheck, Image as ImageIcon, RotateCcw } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { farmRepository } from '../data/farmRepository';

export interface CameraCapture {
  url: string;
  capturedAt: string;
}

export default function CameraPreview({ onCapture }: { onCapture?: (capture: CameraCapture) => void }) {
  const cropPreviewUrl = farmRepository.getCameraPreviewUrl();
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const capturedUrlRef = useRef<string | null>(null);
  const [live, setLive] = useState(false);
  const [capturedUrl, setCapturedUrl] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [capturedAt, setCapturedAt] = useState('');

  useEffect(() => {
    if (videoRef.current && streamRef.current) videoRef.current.srcObject = streamRef.current;
  }, [live]);

  useEffect(() => () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    if (capturedUrlRef.current) URL.revokeObjectURL(capturedUrlRef.current);
  }, []);

  async function startCamera() {
    setError('');
    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Camera is currently offline. This browser does not support camera access.');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false });
      streamRef.current = stream;
      setLive(true);
    } catch {
      setError('Camera is currently offline. Allow camera access in your browser, then try again.');
    }
  }

  function stopCamera() {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setLive(false);
  }

  function captureFrame() {
    const video = videoRef.current;
    if (!video || !video.videoWidth || !video.videoHeight) {
      setError('The camera preview is still starting. Try capturing again in a moment.');
      return;
    }
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d')?.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      if (capturedUrlRef.current) URL.revokeObjectURL(capturedUrlRef.current);
      capturedUrlRef.current = url;
      setCapturedUrl(url);
      const time = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(new Date());
      setCapturedAt(time);
      onCapture?.({ url, capturedAt: time });
      stopCamera();
    }, 'image/jpeg', 0.9);
  }

  return (
    <div className="camera-module">
      <div className={`camera-stage ${live ? 'is-live' : ''}`}>
        {live ? <video ref={videoRef} autoPlay playsInline muted aria-label="Live local camera preview" /> : <img src={capturedUrl ?? cropPreviewUrl} alt={capturedUrl ? 'Image captured from this device camera' : 'Illustrative sample image of green maize leaves in a crop field'} onError={(event) => { if (!capturedUrl && !event.currentTarget.src.endsWith('/crop-preview-fallback.svg')) event.currentTarget.src = '/crop-preview-fallback.svg'; }} />}
        {!live && !capturedUrl && <span className="camera-image-tag"><ImageIcon size={13} /> Illustrative demo image</span>}
        {live && <span className="camera-live-tag"><i /> Live camera · this device</span>}
        {error && <div className="camera-error" role="status"><CameraOff size={18} /><span>{error}</span></div>}
      </div>
      <div className="camera-actions">
        {live ? <button className="button button-primary" onClick={captureFrame}><Camera size={16} /> Capture Image</button> : <button className="button button-primary" onClick={startCamera}><Camera size={16} /> {capturedUrl ? 'Capture another' : 'Use device camera'}</button>}
        {live && <button className="button button-soft" onClick={stopCamera}>Stop camera</button>}
        {capturedUrl && !live && <span className="capture-confirmation"><CircleCheck size={16} /> Captured at {capturedAt} · session only</span>}
        {error && <button className="button button-quiet" onClick={startCamera}><RotateCcw size={15} /> Try again</button>}
      </div>
      <p className="camera-privacy">Camera access starts only when you choose it. Captures stay in this browser session and are not uploaded.</p>
    </div>
  );
}
