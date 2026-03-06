'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { X, Mic } from 'lucide-react'
import { useRouter } from 'next/navigation'

const PHRASES = [
    '"Bicycle scheme for students"',
    '"Scholarship for OBC students"',
    '"Health insurance scheme"',
]

const LANG_OPTIONS = [
    { code: 'en', label: 'English', stt: 'en-IN' },
    { code: 'bn', label: 'বাংলা', stt: 'bn-IN' },
    { code: 'hi', label: 'हिंदी', stt: 'hi-IN' },
]

const PARTICLE_COLORS = ['#3B82F6', '#7C3AED', '#EC4899', '#3B82F6', '#7C3AED', '#EC4899', '#3B82F6', '#7C3AED']

interface Props {
    isOpen: boolean
    onClose: () => void
}

// Extend Window for webkit prefixed APIs
declare global {
    interface Window {
        webkitAudioContext?: typeof AudioContext
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        webkitSpeechRecognition?: any
    }
}

export default function VoiceSearchModal({ isOpen, onClose }: Props) {
    const router = useRouter()
    const canvasRef = useRef<HTMLCanvasElement | null>(null)
    const animFrameRef = useRef<number>(0)
    const audioCtxRef = useRef<AudioContext | null>(null)
    const analyserRef = useRef<AnalyserNode | null>(null)
    const dataRef = useRef<Uint8Array | null>(null)
    const anglesRef = useRef<number[]>(Array.from({ length: 8 }, (_, i) => (i / 8) * Math.PI * 2))
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const recognitionRef = useRef<any>(null)
    const [lang, setLang] = useState('en')
    const [phraseIdx, setPhraseIdx] = useState(0)
    const [micBlocked, setMicBlocked] = useState(false)

    // Cycle phrases every 3s
    useEffect(() => {
        if (!isOpen) return
        const id = setInterval(() => setPhraseIdx(i => (i + 1) % PHRASES.length), 3000)
        return () => clearInterval(id)
    }, [isOpen])

    // Escape key
    useEffect(() => {
        if (!isOpen) return
        const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') cleanup() }
        document.addEventListener('keydown', handler)
        return () => document.removeEventListener('keydown', handler)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isOpen])

    function cleanup() {
        cancelAnimationFrame(animFrameRef.current)
        if (audioCtxRef.current) { try { audioCtxRef.current.close() } catch { } audioCtxRef.current = null }
        if (recognitionRef.current) { try { recognitionRef.current.stop() } catch { } recognitionRef.current = null }
        onClose()
    }

    const drawFrame = useCallback((t: number) => {
        const canvas = canvasRef.current
        if (!canvas) return
        const ctx2d = canvas.getContext('2d')
        if (!ctx2d) return
        const W = canvas.width, H = canvas.height, cx = W / 2, cy = H / 2

        ctx2d.clearRect(0, 0, W, H)

        let freqData: Uint8Array | null = null
        if (analyserRef.current && dataRef.current) {
            analyserRef.current.getByteFrequencyData(dataRef.current as Uint8Array<ArrayBuffer>)
            freqData = dataRef.current
        }

        // Outer circle
        ctx2d.beginPath(); ctx2d.arc(cx, cy, 70, 0, Math.PI * 2)
        ctx2d.fillStyle = '#EEF2FF'; ctx2d.fill()
        ctx2d.strokeStyle = '#C7D2FE'; ctx2d.lineWidth = 2; ctx2d.stroke()

        // Inner glow
        const grad = ctx2d.createRadialGradient(cx, cy, 0, cx, cy, 50)
        grad.addColorStop(0, 'rgba(129,140,248,0.4)')
        grad.addColorStop(1, 'rgba(129,140,248,0)')
        ctx2d.beginPath(); ctx2d.arc(cx, cy, 50, 0, Math.PI * 2)
        ctx2d.fillStyle = grad; ctx2d.fill()

        // Particles
        anglesRef.current = anglesRef.current.map((angle, i) => {
            const freq = freqData ? freqData[i * 4] / 255 : (Math.sin(t / 300 + i) * 0.5 + 0.5)
            const radius = 70 + freq * 40
            const size = 5 + freq * 6
            const px = cx + Math.cos(angle) * radius
            const py = cy + Math.sin(angle) * radius
            ctx2d.beginPath(); ctx2d.arc(px, py, size, 0, Math.PI * 2)
            ctx2d.fillStyle = PARTICLE_COLORS[i]; ctx2d.globalAlpha = 0.85; ctx2d.fill()
            ctx2d.globalAlpha = 1
            return angle + 0.018
        })

        animFrameRef.current = requestAnimationFrame(drawFrame)
    }, [])

    useEffect(() => {
        if (!isOpen) return
        animFrameRef.current = requestAnimationFrame(drawFrame)

        navigator.mediaDevices?.getUserMedia({ audio: true }).then(stream => {
            const AudioCtx = window.AudioContext || window.webkitAudioContext
            if (!AudioCtx) return
            const audioCtx = new AudioCtx()
            const analyser = audioCtx.createAnalyser()
            analyser.fftSize = 64
            const src = audioCtx.createMediaStreamSource(stream)
            src.connect(analyser)
            analyserRef.current = analyser
            dataRef.current = new Uint8Array(analyser.frequencyBinCount)
            audioCtxRef.current = audioCtx
        }).catch(() => setMicBlocked(true))

        return () => { cancelAnimationFrame(animFrameRef.current) }
    }, [isOpen, drawFrame])

    useEffect(() => {
        if (!isOpen || micBlocked) return
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const SR: any = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
        if (!SR) return
        const rec = new SR()
        rec.continuous = false
        rec.interimResults = false
        rec.lang = LANG_OPTIONS.find((l: { code: string }) => l.code === lang)?.stt || 'en-IN'
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        rec.onresult = (e: any) => {
            const transcript = e.results[0][0].transcript
            cleanup()
            router.push('/search?q=' + encodeURIComponent(transcript))
        }
        rec.onerror = () => { }
        try { rec.start() } catch { }
        recognitionRef.current = rec
        return () => { try { rec.stop() } catch { } }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isOpen, lang, micBlocked])

    if (!isOpen) return null

    return (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && cleanup()}>
            <div className="modal-box" style={{ maxWidth: 480, padding: '40px 32px', textAlign: 'center' }}>

                <button onClick={cleanup} style={{
                    position: 'absolute', top: 16, right: 16,
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: '#9CA3AF', display: 'flex', borderRadius: '50%', padding: 4,
                }}>
                    <X size={20} />
                </button>

                {/* Title with animated dots */}
                <div style={{ fontSize: 20, fontWeight: 600, marginBottom: 24, color: 'var(--color-text)' }}>
                    Listening
                    <span className="dot1" style={{ display: 'inline-block', width: 6, height: 6, background: 'var(--color-text)', borderRadius: '50%', margin: '0 2px', verticalAlign: 'middle' }} />
                    <span className="dot2" style={{ display: 'inline-block', width: 6, height: 6, background: 'var(--color-text)', borderRadius: '50%', margin: '0 2px', verticalAlign: 'middle' }} />
                    <span className="dot3" style={{ display: 'inline-block', width: 6, height: 6, background: 'var(--color-text)', borderRadius: '50%', margin: '0 2px', verticalAlign: 'middle' }} />
                </div>

                {/* Canvas globe */}
                <div style={{ position: 'relative', display: 'inline-block', marginBottom: 24 }}>
                    <canvas ref={canvasRef} width={200} height={200} />
                    <div style={{
                        position: 'absolute', top: '50%', left: '50%',
                        transform: 'translate(-50%, -50%)',
                        width: 44, height: 44,
                        background: '#EEF2FF', borderRadius: '50%',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                        <Mic size={22} color="#1A56DB" />
                    </div>
                    <svg
                        className="voice-ring"
                        width={200} height={200}
                        style={{ position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }}
                    >
                        <circle
                            cx={100} cy={100} r={92}
                            fill="none" stroke="#E0E7FF" strokeWidth={1.5}
                            strokeDasharray="6 5" opacity={0.6}
                        />
                    </svg>
                </div>

                {micBlocked && (
                    <p style={{ fontSize: 13, color: '#C81E1E', marginBottom: 16 }}>
                        Microphone access denied. Please allow microphone access and try again.
                    </p>
                )}

                {/* Hint box */}
                <div style={{
                    background: '#F9FAFB', borderRadius: 10, padding: '10px 20px', marginBottom: 20,
                    border: '1px solid #F3F4F6',
                }}>
                    <p style={{ fontSize: 13, color: '#6B7280', margin: 0, fontStyle: 'italic' }}>
                        Try saying: <strong>{PHRASES[phraseIdx]}</strong>
                    </p>
                </div>

                {/* Language row */}
                <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
                    {LANG_OPTIONS.map(opt => (
                        <button
                            key={opt.code}
                            onClick={() => setLang(opt.code)}
                            style={{
                                padding: '6px 14px',
                                borderRadius: 999,
                                border: 'none',
                                fontSize: 13,
                                cursor: 'pointer',
                                fontWeight: lang === opt.code ? 600 : 400,
                                background: lang === opt.code ? '#EEF2FF' : 'transparent',
                                color: lang === opt.code ? '#1A56DB' : '#6B7280',
                            }}
                        >
                            {opt.label}
                        </button>
                    ))}
                </div>
            </div>
        </div>
    )
}
