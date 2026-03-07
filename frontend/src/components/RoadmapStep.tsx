'use client'

import type { Lang } from '@/types'

interface RoadmapStepProps {
  step: number
  action: string
  action_bn?: string
  location?: string
  done: boolean
  isLast: boolean
  lang?: Lang
}

export default function RoadmapStep({
  step,
  action,
  action_bn,
  location,
  done,
  isLast,
  lang = 'en',
}: RoadmapStepProps) {
  const locationColors: Record<string, { bg: string; text: string }> = {
    'Bank Branch': { bg: '#DBEAFE', text: '#1D4ED8' },
    'BDO Office': { bg: '#EDE9FE', text: '#6D28D9' },
    'Post Office': { bg: '#DCFCE7', text: '#15803D' },
  }

  const locationColor = location ? locationColors[location] || { bg: '#F3F4F6', text: '#374151' } : null

  return (
    <div style={{ display: 'flex', gap: 12 }}>
      {/* Left side: circle + line */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        {/* Circle */}
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 14,
            fontWeight: 600,
            flexShrink: 0,
            background: done ? '#22C55E' : '#FFFFFF',
            border: done ? 'none' : '2px solid #3B82F6',
            color: done ? '#FFFFFF' : '#3B82F6',
          }}
        >
          {done ? '✓' : isLast ? '🏁' : step}
        </div>

        {/* Vertical line */}
        {!isLast && (
          <div
            style={{
              width: 2,
              flex: 1,
              minHeight: 40,
              background: '#E5E7EB',
              marginTop: 4,
            }}
          />
        )}
      </div>

      {/* Right side: content */}
      <div style={{ flex: 1, paddingBottom: isLast ? 0 : 16 }}>
        {/* Location badge */}
        {location && locationColor && (
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              padding: '4px 10px',
              borderRadius: 12,
              background: locationColor.bg,
              color: locationColor.text,
              fontSize: 11,
              fontWeight: 600,
              marginBottom: 8,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            {location}
          </div>
        )}

        {/* Action text */}
        <div
          style={{
            fontSize: 14,
            color: done ? '#9CA3AF' : '#111827',
            textDecoration: done ? 'line-through' : 'none',
            lineHeight: 1.5,
            marginBottom: action_bn ? 4 : 0,
          }}
        >
          {action}
        </div>

        {/* Bengali action */}
        {action_bn && (
          <div
            style={{
              fontSize: 13,
              color: '#6B7280',
              lineHeight: 1.5,
              fontFamily: "'Noto Sans Bengali', sans-serif",
              marginLeft: 8,
            }}
          >
            {action_bn}
          </div>
        )}

        {/* Done badge */}
        {done && (
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
              marginTop: 6,
              padding: '2px 8px',
              borderRadius: 10,
              background: '#DCFCE7',
              border: '1px solid #BBF7D0',
              color: '#16A34A',
              fontSize: 11,
              fontWeight: 600,
            }}
          >
            ✓ Done
          </div>
        )}
      </div>
    </div>
  )
}
