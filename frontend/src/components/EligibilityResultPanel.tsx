'use client'

import { useState } from 'react'
import type { EligibilityResult, Lang } from '@/types'
import ScoreMeter from './ScoreMeter'
import MismatchBanner from './MismatchBanner'
import RoadmapStep from './RoadmapStep'
import IssueCard from './IssueCard'

interface EligibilityResultPanelProps {
  result: EligibilityResult
  lang?: Lang
  onScriptRequest?: (scriptCode: string) => void
  onClose?: () => void
}

export default function EligibilityResultPanel({
  result,
  lang = 'en',
  onScriptRequest,
  onClose,
}: EligibilityResultPanelProps) {
  const [showWarnings, setShowWarnings] = useState(false)

  // Separate mismatch issues from other issues
  const mismatchIssues = result.issues.filter((i) => i.code.includes('MISMATCH'))
  const otherIssues = result.issues.filter((i) => !i.code.includes('MISMATCH'))

  const translations = {
    en: {
      benefit: 'Benefit',
      actionPlan: 'Your Action Plan',
      warnings: 'warnings',
      checkAnother: '← Check Another Scheme',
    },
    bn: {
      benefit: 'সুবিধা',
      actionPlan: 'আপনার কার্যপরিকল্পনা',
      warnings: 'সতর্কতা',
      checkAnother: '← অন্য স্কিম চেক করুন',
    },
    hi: {
      benefit: 'लाभ',
      actionPlan: 'आपकी कार्य योजना',
      warnings: 'चेतावनी',
      checkAnother: '← दूसरी योजना जांचें',
    },
  }

  const t = translations[lang]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, padding: '0 0 16px' }}>
      {/* 1. Score Meter */}
      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 8 }}>
        <ScoreMeter
          score={result.score}
          band={result.band}
          band_label={result.band_label}
          band_label_bn={result.band_label_bn}
          animate={true}
        />
      </div>

      {/* 2. Scheme name and benefit */}
      <div style={{ textAlign: 'center' }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: '#111827', margin: 0, marginBottom: 4 }}>
          {result.scheme_name}
        </h2>
        {result.scheme_name_bn && (
          <p
            style={{
              fontSize: 15,
              color: '#6B7280',
              margin: 0,
              marginBottom: 8,
              fontFamily: "'Noto Sans Bengali', sans-serif",
            }}
          >
            {result.scheme_name_bn}
          </p>
        )}
        {result.benefit_amount && (
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '6px 14px',
              borderRadius: 16,
              background: '#EFF6FF',
              border: '1px solid #BFDBFE',
              color: '#1E40AF',
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            {t.benefit}: ₹{result.benefit_amount.toLocaleString('en-IN')}
          </div>
        )}
      </div>

      {/* 3. Mismatch banners */}
      {mismatchIssues.length > 0 && (
        <div>
          {mismatchIssues.map((issue, idx) => (
            <MismatchBanner key={idx} issue={issue} lang={lang} />
          ))}
        </div>
      )}

      {/* 4. Other issues */}
      {otherIssues.length > 0 && (
        <div>
          {otherIssues.map((issue, idx) => (
            <IssueCard key={idx} issue={issue} lang={lang} onScriptRequest={onScriptRequest} />
          ))}
        </div>
      )}

      {/* 5. Warnings (collapsible) */}
      {result.warnings && result.warnings.length > 0 && (
        <details
          open={showWarnings}
          onToggle={(e) => setShowWarnings((e.target as HTMLDetailsElement).open)}
          style={{
            background: '#FFFBEB',
            border: '1px solid #FDE68A',
            borderRadius: 8,
            padding: 12,
          }}
        >
          <summary
            style={{
              fontSize: 14,
              fontWeight: 600,
              color: '#D97706',
              cursor: 'pointer',
              listStyle: 'none',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <span>⚠️</span>
            <span>
              {result.warnings.length} {t.warnings}
            </span>
            <span style={{ marginLeft: 'auto', fontSize: 12 }}>
              {showWarnings ? '▼' : '▶'}
            </span>
          </summary>
          <div style={{ marginTop: 12 }}>
            {result.warnings.map((warning, idx) => (
              <IssueCard key={idx} issue={warning} lang={lang} onScriptRequest={onScriptRequest} />
            ))}
          </div>
        </details>
      )}

      {/* 6. Action Roadmap */}
      {result.roadmap && result.roadmap.length > 0 && (
        <div>
          <h3
            style={{
              fontSize: 16,
              fontWeight: 700,
              color: '#111827',
              marginBottom: 16,
            }}
          >
            {t.actionPlan}
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {result.roadmap.map((step, idx) => (
              <RoadmapStep
                key={idx}
                step={step.step}
                action={step.action}
                action_bn={step.action_bn}
                location={step.location}
                done={step.done}
                isLast={idx === result.roadmap.length - 1}
                lang={lang}
              />
            ))}
          </div>
        </div>
      )}

      {/* 7. Close button */}
      {onClose && (
        <button
          onClick={onClose}
          style={{
            width: '100%',
            padding: '12px 20px',
            borderRadius: 10,
            background: '#F3F4F6',
            border: '1px solid #D1D5DB',
            color: '#374151',
            fontSize: 14,
            fontWeight: 600,
            cursor: 'pointer',
            marginTop: 8,
          }}
          onMouseOver={(e) => {
            e.currentTarget.style.background = '#E5E7EB'
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.background = '#F3F4F6'
          }}
        >
          {t.checkAnother}
        </button>
      )}
    </div>
  )
}
