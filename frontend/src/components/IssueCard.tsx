'use client'

import type { EligibilityIssue, Lang } from '@/types'

interface IssueCardProps {
  issue: EligibilityIssue
  lang?: Lang
  onScriptRequest?: (scriptCode: string) => void
}

export default function IssueCard({ issue, lang = 'en', onScriptRequest }: IssueCardProps) {
  const isFatal = issue.type === 'fatal'

  const borderColor = isFatal ? '#EF4444' : '#F59E0B'
  const bgColor = isFatal ? '#FFF5F5' : '#FFFBEB'
  const icon = isFatal ? '⛔' : '⚠️'

  // Format code: replace underscores with spaces and title case
  const formatCode = (code: string) => {
    return code
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ')
  }

  return (
    <div
      style={{
        background: bgColor,
        borderLeft: `4px solid ${borderColor}`,
        borderRadius: 8,
        padding: 14,
        marginBottom: 12,
      }}
    >
      {/* Row 1: Icon + Code + Badge */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 8 }}>
        <span style={{ fontSize: 20, flexShrink: 0 }}>{icon}</span>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
            <h4 style={{ fontSize: 14, fontWeight: 600, color: '#111827', margin: 0 }}>
              {formatCode(issue.code)}
            </h4>
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                padding: '3px 8px',
                borderRadius: 10,
                background: isFatal ? '#FEE2E2' : '#FEF3C7',
                border: `1px solid ${isFatal ? '#FECACA' : '#FDE68A'}`,
                color: isFatal ? '#DC2626' : '#D97706',
                fontSize: 11,
                fontWeight: 600,
              }}
            >
              -{issue.score_deduction} pts
            </div>
          </div>
        </div>
      </div>

      {/* Row 2: Message */}
      <div style={{ fontSize: 13, color: '#374151', lineHeight: 1.5, marginBottom: 8, marginLeft: 30 }}>
        {issue.message}
      </div>

      {/* Row 3: Script button */}
      {issue.script_available && issue.script_code && onScriptRequest && (
        <button
          onClick={() => onScriptRequest(issue.script_code!)}
          style={{
            marginLeft: 30,
            padding: '6px 12px',
            borderRadius: 6,
            background: 'transparent',
            border: 'none',
            color: '#2563EB',
            fontSize: 12,
            fontWeight: 600,
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
          }}
          onMouseOver={(e) => {
            e.currentTarget.style.textDecoration = 'underline'
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.textDecoration = 'none'
          }}
        >
          Get help script →
        </button>
      )}
    </div>
  )
}
