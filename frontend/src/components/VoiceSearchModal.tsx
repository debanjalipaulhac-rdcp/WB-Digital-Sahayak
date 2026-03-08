'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { X, Mic } from 'lucide-react'
import { useRouter } from 'next/navigation'

// ─── Tuning knobs ─────────────────────────────────────────────────────────────
// RMS scale: 0.0 = dead silence, ~0.04 = quiet room, 0.1+ = clear speech
const SPEECH_ONSET_RMS    = 0.035  // RMS must exceed this to count as "speech started"
const SILENCE_RMS         = 0.018  // RMS below this counts as "silence"
const MIN_SPEECH_MS       = 500    // must hear speech for this long before arming
const SILENCE_TRIGGER_MS  = 1400   // silence for this long → stop recording
const POLL_MS             = 60     // silence-check interval — independent of canvas fps

// ─── Visual constants ─────────────────────────────────────────────────────────
const PHRASES = [
    '"Bicycle scheme for students"',
    '"Scholarship for OBC students"',
    '"Health insurance scheme"',
]
const LANG_OPTIONS = [
    { code: 'en', label: 'English', stt: 'en-IN' },
    { code: 'bn', label: 'বাংলা',   stt: 'bn-IN' },
    { code: 'hi', label: 'हिंदी',   stt: 'hi-IN' },
]
const COLORS = ['#3B82F6','#7C3AED','#EC4899','#3B82F6','#7C3AED','#EC4899','#3B82F6','#7C3AED']

// ─── Types ────────────────────────────────────────────────────────────────────
interface Props { isOpen: boolean; onClose: () => void }
declare global { interface Window { webkitAudioContext?: typeof AudioContext } }

// ─── RMS using TIME-DOMAIN waveform (not FFT frequency) ──────────────────────
// Time-domain reacts to silence INSTANTLY. FFT has smoothing lag — useless here.
// 128 = centre (silence). Deviation from 128 = loudness.
function rms(analyser: AnalyserNode, buf: any): number {
    analyser.getByteTimeDomainData(buf)
    let s = 0
    for (let i = 0; i < buf.length; i++) {
        const n = (buf[i] - 128) / 128   // -1..+1
        s += n * n
    }
    return Math.sqrt(s / buf.length)     // 0.0 = silence, 1.0 = max
}

// ─── Component ────────────────────────────────────────────────────────────────
export default function VoiceSearchModal({ isOpen, onClose }: Props) {
    const router = useRouter()

    // Audio/canvas refs
    const canvasRef   = useRef<HTMLCanvasElement | null>(null)
    const rafRef      = useRef<number>(0)
    const ctxRef      = useRef<AudioContext | null>(null)
    const analyserRef = useRef<AnalyserNode | null>(null)
    const streamRef   = useRef<MediaStream | null>(null)
    const anglesRef   = useRef(Array.from({ length: 8 }, (_, i) => (i / 8) * Math.PI * 2))

    // Two separate buffers — freq for canvas visuals, time for RMS silence check
    const freqBuf = useRef<Uint8Array | null>(null)   // frequencyBinCount bins
    const timeBuf = useRef<Uint8Array | null>(null)   // fftSize samples

    // Recorder refs
    const recRef    = useRef<MediaRecorder | null>(null)
    const chunks    = useRef<Blob[]>([])

    // ── Silence detection state — ALL REFS, never React state ────────────────
    // Reason: setInterval callback captures refs, not state. No stale closure.
    const processing    = useRef(false)
    const speechArmed   = useRef(false)   // true after MIN_SPEECH_MS of real speech
    const speechStart   = useRef(0)
    const silenceStart  = useRef<number | null>(null)
    const pollRef       = useRef<ReturnType<typeof setInterval> | null>(null)

    // React state — rendering only
    const [lang,       setLang      ] = useState('en')
    const [phraseIdx,  setPhraseIdx ] = useState(0)
    const [micBlocked, setMicBlocked] = useState(false)
    const [status,     setStatus    ] = useState<'listening'|'processing'|'error'>('listening')
    const [errorMsg,   setErrorMsg  ] = useState('')

    // Phrase cycling
    useEffect(() => {
        if (!isOpen) return
        const id = setInterval(() => setPhraseIdx(i => (i + 1) % PHRASES.length), 3000)
        return () => clearInterval(id)
    }, [isOpen])

    // Escape key
    useEffect(() => {
        if (!isOpen) return
        const h = (e: KeyboardEvent) => { if (e.key === 'Escape') close() }
        document.addEventListener('keydown', h)
        return () => document.removeEventListener('keydown', h)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isOpen])

    // ── Hard reset all detection state ───────────────────────────────────────
    function resetDetection() {
        chunks.current      = []
        processing.current  = false
        speechArmed.current = false
        speechStart.current = 0
        silenceStart.current= null
    }

    // ── Full cleanup ──────────────────────────────────────────────────────────
    function close() {
        stopPoll()
        cancelAnimationFrame(rafRef.current)
        if (ctxRef.current) { try { ctxRef.current.close() } catch {} ctxRef.current = null }
        if (recRef.current?.state !== 'inactive') { try { recRef.current!.stop() } catch {} }
        recRef.current = null
        streamRef.current?.getTracks().forEach(t => t.stop())
        streamRef.current = null
        resetDetection()
        onClose()
    }

    function stopPoll() {
        if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
    }

    // ── Submit blob → STT API ────────────────────────────────────────────────
    const submit = useCallback(async (blob: Blob) => {
        if (processing.current) return
        processing.current = true
        setStatus('processing')
        stopPoll()

        try {
            const sttLang = LANG_OPTIONS.find(l => l.code === lang)?.stt ?? 'en-IN'
            const form = new FormData()
            form.append('audio', blob, 'recording.webm')

            const res = await fetch(`/api/search-from-audio?lang=${sttLang}`, {
                method: 'POST', credentials: 'include', body: form
                // ⚠️ NO Content-Type header — browser sets multipart boundary
            })
            if (!res.ok) {
                const e = await res.json().catch(() => ({ detail: 'STT failed' }))
                throw new Error((e as { detail?: string }).detail ?? 'STT failed')
            }
            const data = await res.json() as {
                transcript: string; language_code: string
                confidence: number; is_fallback: boolean; detail?: string
            }
            if (data.is_fallback || !data.transcript?.trim()) {
                setErrorMsg(data.detail ?? "Couldn't understand. Speak clearly and try again.")
                setStatus('error')
                processing.current = false
                setTimeout(() => { setStatus('listening'); setErrorMsg(''); resetDetection(); startPoll() }, 2200)
                return
            }
            close()
            router.push(`/search?q=${encodeURIComponent(data.transcript.trim())}`)
        } catch (e) {
            setErrorMsg((e as Error).message ?? 'Failed')
            setStatus('error')
            processing.current = false
            setTimeout(() => { setStatus('listening'); setErrorMsg(''); resetDetection(); startPoll() }, 2500)
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [lang, router])

    // ── Silence detection — setInterval, reads ONLY refs ─────────────────────
    const startPoll = useCallback(() => {
        stopPoll()
        pollRef.current = setInterval(() => {
            const analyser = analyserRef.current
            const buf      = timeBuf.current
            const rec      = recRef.current
            if (!analyser || !buf || !rec)   return
            if (processing.current)          return
            if (rec.state !== 'recording')   return

            const level = rms(analyser, buf)

            if (!speechArmed.current) {
                // Phase 1 — waiting for speech onset
                if (level >= SPEECH_ONSET_RMS) {
                    if (!speechStart.current) speechStart.current = Date.now()
                    else if (Date.now() - speechStart.current >= MIN_SPEECH_MS) {
                        speechArmed.current  = true
                        silenceStart.current = null
                    }
                } else {
                    speechStart.current = 0   // reset — not sustained
                }
            } else {
                // Phase 2 — speech happened, now watch for silence
                if (level < SILENCE_RMS) {
                    if (!silenceStart.current) silenceStart.current = Date.now()
                    else if (Date.now() - silenceStart.current >= SILENCE_TRIGGER_MS) {
                        // ✅ STOP
                        silenceStart.current = null
                        speechArmed.current  = false
                        stopPoll()
                        try { rec.stop() } catch {}   // → onstop → submit()
                    }
                } else {
                    silenceStart.current = null   // still talking, reset timer
                }
            }
        }, POLL_MS)
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])   // zero deps — only uses refs

    // ── Canvas draw — VISUALS ONLY, zero silence logic ────────────────────────
    const draw = useCallback((t: number) => {
        const canvas = canvasRef.current; if (!canvas) return
        const ctx = canvas.getContext('2d'); if (!ctx) return
        const W = canvas.width, H = canvas.height, cx = W/2, cy = H/2
        ctx.clearRect(0, 0, W, H)

        let fd: Uint8Array | null = null
        if (analyserRef.current && freqBuf.current) {
            analyserRef.current.getByteFrequencyData(freqBuf.current as Uint8Array<ArrayBuffer>)
            fd = freqBuf.current
        }

        ctx.beginPath(); ctx.arc(cx, cy, 70, 0, Math.PI*2)
        ctx.fillStyle = '#EEF2FF'; ctx.fill()
        ctx.strokeStyle = '#C7D2FE'; ctx.lineWidth = 2; ctx.stroke()

        const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, 50)
        g.addColorStop(0, 'rgba(129,140,248,0.4)'); g.addColorStop(1, 'rgba(129,140,248,0)')
        ctx.beginPath(); ctx.arc(cx, cy, 50, 0, Math.PI*2); ctx.fillStyle = g; ctx.fill()

        anglesRef.current = anglesRef.current.map((a, i) => {
            const f = fd ? fd[i*4]/255 : (Math.sin(t/300+i)*0.5+0.5)
            const r = 70 + f*40, s = 5 + f*6
            const px = cx + Math.cos(a)*r, py = cy + Math.sin(a)*r
            ctx.beginPath(); ctx.arc(px, py, s, 0, Math.PI*2)
            ctx.fillStyle = COLORS[i]; ctx.globalAlpha = 0.85; ctx.fill(); ctx.globalAlpha = 1
            return a + 0.018
        })
        rafRef.current = requestAnimationFrame(draw)
    }, [])   // zero deps — pure visual

    // ── Mic setup ─────────────────────────────────────────────────────────────
    useEffect(() => {
        if (!isOpen) return
        setStatus('listening'); setMicBlocked(false); setErrorMsg(''); resetDetection()
        rafRef.current = requestAnimationFrame(draw)

        navigator.mediaDevices?.getUserMedia({ audio: true })
            .then(stream => {
                streamRef.current = stream
                const AC = window.AudioContext || window.webkitAudioContext
                if (!AC) return
                const ac = new AC()
                const an = ac.createAnalyser()
                an.fftSize = 256
                an.smoothingTimeConstant = 0.1   // LOW smoothing = fast silence response
                ac.createMediaStreamSource(stream).connect(an)
                analyserRef.current = an
                ctxRef.current      = ac
                freqBuf.current     = new Uint8Array(an.frequencyBinCount)  // 128 — visuals
                timeBuf.current     = new Uint8Array(an.fftSize)             // 256 — RMS

                const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
                    ? 'audio/webm;codecs=opus'
                    : MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : ''
                const rec = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined)
                rec.ondataavailable = e => { if (e.data.size > 0) chunks.current.push(e.data) }
                rec.onstop = () => {
                    if (processing.current) return
                    const blob = new Blob(chunks.current, { type: mime || 'audio/webm' })
                    chunks.current = []
                    submit(blob)
                }
                rec.start(100)
                recRef.current = rec
                startPoll()
            })
            .catch(() => setMicBlocked(true))

        return () => {
            stopPoll()
            cancelAnimationFrame(rafRef.current)
            if (recRef.current?.state !== 'inactive') { try { recRef.current?.stop() } catch {} }
            streamRef.current?.getTracks().forEach(t => t.stop())
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isOpen])   // only re-run when modal opens/closes

    if (!isOpen) return null

    const title = status === 'processing' ? 'Processing' : status === 'error' ? 'Try again' : 'Listening'

    return (
        <div className="modal-overlay" onClick={e => e.target === e.currentTarget && close()}>
            <div className="modal-box" style={{ maxWidth: 480, padding: '40px 32px', textAlign: 'center' }}>

                <button onClick={close} style={{
                    position:'absolute', top:16, right:16, background:'none', border:'none',
                    cursor:'pointer', color:'#9CA3AF', display:'flex', borderRadius:'50%', padding:4,
                }}>
                    <X size={20} />
                </button>

                <div style={{ fontSize:20, fontWeight:600, marginBottom:24, color:'var(--color-text)' }}>
                    {title}
                    {status === 'listening' && (<>
                        <span className="dot1" style={{ display:'inline-block', width:6, height:6, background:'var(--color-text)', borderRadius:'50%', margin:'0 2px', verticalAlign:'middle' }} />
                        <span className="dot2" style={{ display:'inline-block', width:6, height:6, background:'var(--color-text)', borderRadius:'50%', margin:'0 2px', verticalAlign:'middle' }} />
                        <span className="dot3" style={{ display:'inline-block', width:6, height:6, background:'var(--color-text)', borderRadius:'50%', margin:'0 2px', verticalAlign:'middle' }} />
                    </>)}
                    {status === 'processing' && (
                        <span style={{ fontSize:14, fontWeight:400, color:'#6B7280', marginLeft:8 }}>converting speech…</span>
                    )}
                </div>

                <div style={{ position:'relative', display:'inline-block', marginBottom:24 }}>
                    <canvas ref={canvasRef} width={240} height={240} />
                    <div style={{
                        position:'absolute', top:'50%', left:'50%', transform:'translate(-50%,-50%)',
                        width:44, height:44, background:'#EEF2FF', borderRadius:'50%',
                        display:'flex', alignItems:'center', justifyContent:'center',
                    }}>
                        <Mic size={22} color={status === 'processing' ? '#9CA3AF' : '#1A56DB'} />
                    </div>
                    <svg className="voice-ring" width={200} height={200}
                        style={{ position:'absolute', top:0, left:0, pointerEvents:'none' }}>
                        <circle cx={100} cy={100} r={92} fill="none"
                            stroke="#E0E7FF" strokeWidth={1.5} strokeDasharray="6 5" opacity={0.6} />
                    </svg>
                </div>

                {micBlocked && (
                    <p style={{ fontSize:13, color:'#C81E1E', marginBottom:16 }}>
                        Microphone access denied. Please allow microphone access and try again.
                    </p>
                )}
                {status === 'error' && errorMsg && (
                    <p style={{ fontSize:13, color:'#C81E1E', marginBottom:16 }}>{errorMsg}</p>
                )}

                <div style={{ background:'#F9FAFB', borderRadius:10, padding:'10px 20px', marginBottom:20, border:'1px solid #F3F4F6' }}>
                    <p style={{ fontSize:13, color:'#6B7280', margin:0, fontStyle:'italic' }}>
                        {status === 'processing'
                            ? 'Understanding your request…'
                            : <>Try saying: <strong>{PHRASES[phraseIdx]}</strong></>}
                    </p>
                </div>

                <div style={{ display:'flex', gap:8, justifyContent:'center' }}>
                    {LANG_OPTIONS.map(opt => (
                        <button key={opt.code} onClick={() => setLang(opt.code)}
                            disabled={status === 'processing'}
                            style={{
                                padding:'6px 14px', borderRadius:999, border:'none', fontSize:13,
                                cursor:     status === 'processing' ? 'not-allowed' : 'pointer',
                                fontWeight: lang === opt.code ? 600 : 400,
                                background: lang === opt.code ? '#EEF2FF' : 'transparent',
                                color:      lang === opt.code ? '#1A56DB' : '#6B7280',
                                opacity:    status === 'processing' ? 0.5 : 1,
                            }}>
                            {opt.label}
                        </button>
                    ))}
                </div>

            </div>
        </div>
    )
}
