'use client'

import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'

const RADIUS = 90
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

function getBandColor(score: number) {
    if (score >= 80) return { stroke: '#22c55e', text: 'text-green-400', ring: '#22c55e' }
    if (score >= 50) return { stroke: '#f59e0b', text: 'text-amber-400', ring: '#f59e0b' }
    return { stroke: '#ef4444', text: 'text-red-400', ring: '#ef4444' }
}

interface Props {
    score?: number
    shouldAnimate?: boolean
}

export default function ScoreMeter({ score = 0, shouldAnimate = true }: Props) {
    const [displayScore, setDisplayScore] = useState(0)
    const [animDone, setAnimDone] = useState(!shouldAnimate)
    const colors = getBandColor(score)

    const targetDashOffset = CIRCUMFERENCE - (score / 100) * CIRCUMFERENCE

    useEffect(() => {
        if (!shouldAnimate) {
            setDisplayScore(score)
            setAnimDone(true)
            return
        }

        const duration = 1500
        const start = performance.now()
        const tick = (now: number) => {
            const elapsed = now - start
            const progress = Math.min(elapsed / duration, 1)
            const eased = 1 - Math.pow(1 - progress, 3)
            setDisplayScore(Math.round(eased * score))
            if (progress < 1) {
                requestAnimationFrame(tick)
            } else {
                setDisplayScore(score)
                setAnimDone(true)
            }
        }
        requestAnimationFrame(tick)
    }, [score, shouldAnimate])

    return (
        <div className="flex flex-col items-center">
            <div className="relative w-52 h-52">
                <svg className="w-full h-full -rotate-90" viewBox="0 0 220 220">
                    {/* Track */}
                    <circle cx="110" cy="110" r={RADIUS} fill="none" stroke="#1e293b" strokeWidth="16" />
                    {/* Animated progress */}
                    <motion.circle
                        cx="110" cy="110" r={RADIUS}
                        fill="none" stroke={colors.stroke} strokeWidth="16"
                        strokeLinecap="round"
                        strokeDasharray={CIRCUMFERENCE}
                        initial={{ strokeDashoffset: CIRCUMFERENCE }}
                        animate={{ strokeDashoffset: targetDashOffset }}
                        transition={{ duration: 1.5, ease: 'easeOut' }}
                    />
                    {/* Glow effect */}
                    <motion.circle
                        cx="110" cy="110" r={RADIUS}
                        fill="none" stroke={colors.stroke} strokeWidth="4"
                        strokeLinecap="round"
                        strokeDasharray={CIRCUMFERENCE}
                        initial={{ strokeDashoffset: CIRCUMFERENCE, opacity: 0.3 }}
                        animate={{ strokeDashoffset: targetDashOffset, opacity: 0.15 }}
                        transition={{ duration: 1.5, ease: 'easeOut' }}
                        style={{ filter: `blur(6px)` }}
                    />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className={`text-5xl font-black ${colors.text} tabular-nums`}>{displayScore}</span>
                    <span className="text-slate-400 text-xs mt-1 font-medium tracking-widest uppercase">Score</span>
                </div>
            </div>
        </div>
    )
}
