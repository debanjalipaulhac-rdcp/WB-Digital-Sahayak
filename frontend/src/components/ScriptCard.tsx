'use client'

import { useState, useRef } from 'react'
import { motion } from 'framer-motion'

interface Props {
    bengaliText: string
    englishText?: string
    audioUrl?: string
}

export default function ScriptCard({ bengaliText, englishText, audioUrl }: Props) {
    const [copied, setCopied] = useState(false)
    const [playing, setPlaying] = useState(false)
    const audioRef = useRef<HTMLAudioElement | null>(null)

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(bengaliText)
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        } catch {
            const el = document.createElement('textarea')
            el.value = bengaliText
            document.body.appendChild(el)
            el.select()
            document.execCommand('copy')
            document.body.removeChild(el)
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        }
    }

    const handlePlay = () => {
        if (!audioRef.current) return
        if (playing) {
            audioRef.current.pause()
            audioRef.current.currentTime = 0
            setPlaying(false)
        } else {
            audioRef.current.play()
            setPlaying(true)
        }
    }

    return (
        <div className="rounded-xl bg-slate-900/80 border border-blue-500/20 p-4">
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                    <span className="text-blue-400 text-sm font-semibold">🗣️ Script</span>
                    <span className="text-xs text-slate-500 px-1.5 py-0.5 bg-slate-700/50 rounded">বাংলা</span>
                </div>
                <div className="flex items-center gap-2">
                    {audioUrl && (
                        <button
                            onClick={handlePlay}
                            className="text-xs px-2.5 py-1.5 rounded-lg bg-blue-500/20 text-blue-300 hover:bg-blue-500/30 transition-all flex items-center gap-1.5"
                        >
                            {playing ? '⏹ Stop' : '▶ Play'}
                        </button>
                    )}
                    <motion.button
                        onClick={handleCopy}
                        whileTap={{ scale: 0.95 }}
                        className={`text-xs px-2.5 py-1.5 rounded-lg font-semibold transition-all duration-200 flex items-center gap-1.5 ${copied
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-slate-700/60 text-slate-300 hover:bg-slate-600/60'
                            }`}
                    >
                        {copied ? '✓ Copied!' : '📋 Copy'}
                    </motion.button>
                </div>
            </div>

            {/* Bengali Script */}
            <div
                className="text-white text-sm leading-relaxed bg-slate-800/60 rounded-lg p-3 mb-3"
                style={{ fontFamily: "'Noto Sans Bengali', 'Arial Unicode MS', sans-serif", fontSize: '0.9rem', lineHeight: '1.8' }}
            >
                {bengaliText}
            </div>

            {/* English translation */}
            {englishText && (
                <div className="text-slate-400 text-xs italic border-t border-slate-700/50 pt-2 mt-2 leading-relaxed">
                    <span className="text-slate-500 font-semibold not-italic">English: </span>
                    {englishText}
                </div>
            )}

            {audioUrl && (
                <audio
                    ref={audioRef}
                    src={audioUrl}
                    onEnded={() => setPlaying(false)}
                    className="hidden"
                />
            )}
        </div>
    )
}
