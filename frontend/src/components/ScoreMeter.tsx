'use client'

import { useEffect, useState } from 'react'
import type { Band } from '@/types'

interface ScoreMeterProps {
  score: number
  band: Band
  band_label: string
  band_label_bn?: string
  animate?: boolean
}

export default function ScoreMeter({
  score,
  band,
  band_label,
  band_label_bn,
  animate = true,
}: ScoreMeterProps) {
  const [displayScore, setDisplayScore] = useState(0)
  const [dashOffset, setDashOffset] = useState(502.65)

  const RADIUS = 80
  const CIRCUMFERENCE = 2 * Math.PI * RADIUS // 502.65

  // Band colors
  const colors = {
    RED: { stroke: '#EF4444', bg: '#FEE2E2', text: '#DC2626', border: '#FECACA' },
    AMBER: { stroke: '#F59E0B', bg: '#FEF3C7', text: '#D97706', border: '#FDE68A' },
    GREEN: { stroke: '#22C55E', bg: '#DCFCE7', text: '#16A34A', border: '#BBF7D0' },
  }

  const color = colors[band]

  useEffect(() => {
    if (!animate) {
      setDisplayScore(score)
      setDashOffset(CIRCUMFERENCE - (score / 100) * CIRCUMFERENCE)
      return
    }

    const duration = 1200
    const start = performance.now()

    const tick = (now: number) => {
      const elapsed = now - start
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3) // ease-out cubic

      const currentScore = Math.round(eased * score)
      const currentOffset = CIRCUMFERENCE - (currentScore / 100) * CIRCUMFERENCE

      setDisplayScore(currentScore)
      setDashOffset(currentOffset)

      if (progress < 1) {
        requestAnimationFrame(tick)
      }
    }

    requestAnimationFrame(tick)
  }, [score, animate, CIRCUMFERENCE])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
      {/* SVG Circle Meter */}
      <div style={{ position: 'relative', width: 180, height: 180 }}>
        <svg width="180" height="180" viewBox="0 0 180 180">
          {/* Background track */}
          <circle
            cx="90"
            cy="90"
            r={RADIUS}
            fill="none"
            stroke="#E5E7EB"
            strokeWidth="12"
          />
          {/* Animated arc */}
          <circle
            cx="90"
            cy="90"
            r={RADIUS}
            fill="none"
            stroke={color.stroke}
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={dashOffset}
            transform="rotate(-90 90 90)"
            style={{ transition: animate ? 'stroke-dashoffset 0.1s linear' : 'none' }}
          />
        </svg>

        {/* Center text */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <div style={{ fontSize: 48, fontWeight: 700, color: color.stroke, lineHeight: 1 }}>
            {displayScore}
          </div>
          <div style={{ fontSize: 14, fontWeight: 600, color: '#6B7280', marginTop: 4 }}>
            {band_label}
          </div>
          {band_label_bn && (
            <div
              style={{
                fontSize: 12,
                fontWeight: 400,
                color: '#9CA3AF',
                marginTop: 2,
                fontFamily: "'Noto Sans Bengali', sans-serif",
              }}
            >
              {band_label_bn}
            </div>
          )}
        </div>
      </div>

      {/* Band badge pill */}
      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          padding: '8px 16px',
          borderRadius: 20,
          background: color.bg,
          border: `1px solid ${color.border}`,
          color: color.text,
          fontSize: 13,
          fontWeight: 600,
        }}
      >
        <span>{band === 'RED' ? '🔴' : band === 'AMBER' ? '🟡' : '🟢'}</span>
        <span>{band_label}</span>
        {band_label_bn && (
          <>
            <span style={{ color: color.border }}>•</span>
            <span style={{ fontFamily: "'Noto Sans Bengali', sans-serif" }}>{band_label_bn}</span>
          </>
        )}
      </div>
    </div>
  )
}
