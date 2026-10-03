import { useEffect, useRef, useState } from 'react'
import { Camera, RefreshCw, X } from 'lucide-react'

// The live camera needs a secure page (HTTPS or localhost). On plain http (a phone opening the laptop's
// address) the caller opens the phone's own camera app instead; check this at the tap, because the
// browser only lets a direct tap open it.
export const liveCameraAvailable = () => !!navigator.mediaDevices?.getUserMedia

// Full-screen live viewfinder. The shot is stamped with the date, time and (if shared) the location,
// shrunk like an uploaded photo (max 1280 px, JPEG), and handed to onCapture as a data URL.
// If the camera cannot start, onFallback (run from a tap) opens the phone's camera app.
export default function LiveCamera({ t, point, onCapture, onClose, onFallback }) {
  const video = useRef(null)
  const stream = useRef(null)
  const [facing, setFacing] = useState('environment')
  const [ready, setReady] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => {
    if (!liveCameraAvailable()) { setErr(t.cameraFail); return }
    let cancelled = false
    setReady(false)
    navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: facing }, width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false })
      .then((s) => {
        if (cancelled) { s.getTracks().forEach((x) => x.stop()); return }
        stream.current = s
        video.current.srcObject = s
        video.current.play().then(() => setReady(true)).catch(() => setReady(true))
      })
      .catch((e) => setErr(e.name === 'NotAllowedError' ? t.cameraBlocked : t.cameraFail))
    return () => { cancelled = true; stream.current?.getTracks().forEach((x) => x.stop()); stream.current = null }
  }, [facing])

  const shoot = () => {
    const v = video.current
    const scale = Math.min(1, 1280 / Math.max(v.videoWidth, v.videoHeight))
    const canvas = Object.assign(document.createElement('canvas'), { width: Math.round(v.videoWidth * scale), height: Math.round(v.videoHeight * scale) })
    const g = canvas.getContext('2d')
    g.drawImage(v, 0, 0, canvas.width, canvas.height)
    // evidence stamp: when (and where) the photo was taken
    const stamp = [`SamajSevak · ${new Date().toLocaleString()}`, point && `${point.lat.toFixed(5)}, ${point.lng.toFixed(5)}`].filter(Boolean).join('  ·  ')
    const size = Math.max(14, Math.round(canvas.width / 45))
    g.font = `600 ${size}px system-ui, sans-serif`
    g.fillStyle = 'rgba(0, 0, 0, .55)'
    g.fillRect(0, canvas.height - size * 2, canvas.width, size * 2)
    g.fillStyle = '#fff'
    g.fillText(stamp, size * 0.7, canvas.height - size * 0.65)
    onCapture(canvas.toDataURL('image/jpeg', 0.8))
  }

  return (
    <div className="camera">
      <video ref={video} playsInline muted autoPlay className={facing === 'user' ? 'mirror' : ''} />
      {err && <div className="camera-msg">{err}<button type="button" className="btn" style={{ marginTop: 14 }} onClick={onFallback}><Camera size={15} />{t.useCameraApp}</button></div>}
      {!err && !ready && <div className="camera-msg">{t.cameraStarting}</div>}
      <div className="camera-bar">
        <button type="button" className="camera-btn" onClick={onClose} aria-label={t.remove}><X size={22} /></button>
        <button type="button" className="camera-shutter" onClick={shoot} disabled={!ready} aria-label={t.capture}><Camera size={28} /></button>
        <button type="button" className="camera-btn" onClick={() => setFacing(facing === 'environment' ? 'user' : 'environment')} aria-label={t.switchCam}><RefreshCw size={22} /></button>
      </div>
    </div>
  )
}
