
import { useEffect, useRef, useState } from 'react';
import { Camera, CameraOff, CheckCircle2, RefreshCw } from 'lucide-react';

export interface CameraCapture {
  url: string;
  capturedAt: string;
  blob: Blob;
}

interface CameraPreviewProps {
  onCapture?: (capture: CameraCapture) => void;
}

export default function CameraPreview({ onCapture }: CameraPreviewProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const capturedUrlRef = useRef<string | null>(null);

  const [cameraActive, setCameraActive] = useState(false);
  const [starting, setStarting] = useState(false);
  const [capturedUrl, setCapturedUrl] = useState<string | null>(null);
  const [capturedAt, setCapturedAt] = useState<string | null>(null);
  const [error, setError] = useState('');

  function stopCamera() {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setCameraActive(false);
  }

  async function startCamera() {
    setError('');

    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Camera access is unavailable. Use HTTPS or localhost and a supported browser.');
      return;
    }

    setStarting(true);

    try {
      stopCamera();

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' } },
        audio: false,
      });

      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      setCameraActive(true);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Unknown camera error';

      setError(
        message.includes('NotAllowedError')
          ? 'Camera permission was denied. Allow camera access in your browser settings.'
          : message.includes('NotFoundError')
            ? 'No camera was found on this device.'
            : `Could not start the camera: ${message}`,
      );
    } finally {
      setStarting(false);
    }
  }

  function captureFrame() {
    const video = videoRef.current;

    if (!video || !video.videoWidth || !video.videoHeight) {
      setError('The camera is not ready yet. Please wait and try again.');
      return;
    }

    setError('');

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const context = canvas.getContext('2d');

    if (!context) {
      setError('Could not prepare the image for capture.');
      return;
    }

    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      (blob) => {
        if (!blob) {
          setError('Could not capture the image. Please try again.');
          return;
        }

        const url = URL.createObjectURL(blob);

        if (capturedUrlRef.current) {
          URL.revokeObjectURL(capturedUrlRef.current);
        }

        capturedUrlRef.current = url;
        setCapturedUrl(url);

        const time = new Intl.DateTimeFormat(undefined, {
          hour: 'numeric',
          minute: '2-digit',
        }).format(new Date());

        setCapturedAt(time);
        onCapture?.({ url, capturedAt: time, blob });
        stopCamera();
      },
      'image/jpeg',
      0.9,
    );
  }

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());

      if (capturedUrlRef.current) {
        URL.revokeObjectURL(capturedUrlRef.current);
      }
    };
  }, []);

  return (
    <div className="camera-preview">
      <div className="camera-preview-frame">
        {cameraActive ? (
          <video
            ref={videoRef}
            autoPlay
            muted
            playsInline
            aria-label="Live camera preview"
            className="camera-preview-video"
          />
        ) : capturedUrl ? (
          <img
            src={capturedUrl}
            alt="Most recently captured plant image"
            className="camera-preview-video"
          />
        ) : (
          <div className="camera-preview-placeholder">
            <Camera size={36} />
            <strong>Ready to observe</strong>
            <span>Start the camera to capture a plant image.</span>
          </div>
        )}
      </div>

      {error && (
        <p className="camera-preview-error" role="alert">
          {error}
        </p>
      )}

      <div className="camera-preview-actions">
        {!cameraActive ? (
          <button
            type="button"
            className="button button-primary"
            onClick={() => void startCamera()}
            disabled={starting}
          >
            <Camera size={15} />
            {starting ? 'Starting camera…' : 'Start camera'}
          </button>
        ) : (
          <>
            <button
              type="button"
              className="button button-primary"
              onClick={captureFrame}
            >
              <CheckCircle2 size={15} />
              Capture image
            </button>

            <button
              type="button"
              className="button button-soft"
              onClick={stopCamera}
            >
              <CameraOff size={15} />
              Stop camera
            </button>
          </>
        )}

        {capturedUrl && !cameraActive && (
          <button
            type="button"
            className="button button-soft"
            onClick={() => void startCamera()}
            disabled={starting}
          >
            <RefreshCw size={15} />
            Retake
          </button>
        )}
      </div>

      <p className="camera-preview-note">
        Camera access starts only when you choose it. Images are uploaded to
        AgriSight only when you request analysis.
        {capturedAt ? ` Last captured at ${capturedAt}.` : ''}
      </p>
    </div>
  );
}
