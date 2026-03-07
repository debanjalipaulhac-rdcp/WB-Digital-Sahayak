'use client'

import type { EligibilityIssue, Lang } from '@/types'

interface MismatchBannerProps {
  issue: EligibilityIssue
  lang?: Lang
}

export default function MismatchBanner({ issue, lang = 'en' }: MismatchBannerProps) {
  if (!issue.display) return null

  const { label_a, field_a, label_b, field_b, similarity_score } = issue.display
  const value_a = field_a
  const value_b = field_b

  const translations = {
    en: {
      title: 'Name Mismatch Detected',
      subtitle: 'This is the #1 reason applications get rejected',
      matchScore: 'Match score',
      minRequired: 'Minimum required: 90%',
      howToFix: 'How to fix',
      fixInstruction:
        'Visit your bank branch with your Aadhaar card and request a name correction',
      officialRecord: 'OFFICIAL RECORD',
      bankRecord: 'BANK RECORD',
    },
    bn: {
      title: 'নাম মিলছে না',
      subtitle: 'এটাই মূল সমস্যা — আবেদন বাতিল হওয়ার প্রধান কারণ',
      matchScore: 'মিল স্কোর',
      minRequired: 'ন্যূনতম প্রয়োজন: ৯০%',
      howToFix: 'কীভাবে ঠিক করবেন',
      fixInstruction:
        'আপনার আধার কার্ড নিয়ে ব্যাংক শাখায় যান এবং নাম সংশোধনের জন্য অনুরোধ করুন',
      officialRecord: 'সরকারি নথি',
      bankRecord: 'ব্যাংক নথি',
    },
    hi: {
      title: 'नाम मेल नहीं खाता',
      subtitle: 'यह आवेदन अस्वीकृति का #1 कारण है',
      matchScore: 'मैच स्कोर',
      minRequired: 'न्यूनतम आवश्यक: 90%',
      howToFix: 'कैसे ठीक करें',
      fixInstruction:
        'अपने आधार कार्ड के साथ बैंक शाखा में जाएं और नाम सुधार का अनुरोध करें',
      officialRecord: 'आधिकारिक रिकॉर्ड',
      bankRecord: 'बैंक रिकॉर्ड',
    },
  }

  const t = translations[lang]

  return (
    <div
      style={{
        background: '#FFF5F5',
        border: '2px solid #FECACA',
        borderRadius: 12,
        padding: 16,
        marginBottom: 16,
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 12 }}>
        <span style={{ fontSize: 24, flexShrink: 0 }}>⚠️</span>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: '#DC2626', margin: 0 }}>
              {t.title}
            </h3>
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                padding: '4px 10px',
                borderRadius: 12,
                background: '#FEE2E2',
                border: '1px solid #FECACA',
                color: '#DC2626',
                fontSize: 12,
                fontWeight: 600,
              }}
            >
              -{issue.score_deduction} points
            </div>
          </div>
          <p style={{ fontSize: 13, color: '#6B7280', margin: '4px 0 0', lineHeight: 1.4 }}>
            {t.subtitle}
          </p>
        </div>
      </div>

      {/* Comparison block */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr auto 1fr',
          gap: 12,
          alignItems: 'center',
          background: '#FFFFFF',
          border: '1px solid #FEE2E2',
          borderRadius: 10,
          padding: 16,
          marginBottom: 12,
        }}
      >
        {/* Left column */}
        <div>
          <div style={{ fontSize: 11, color: '#9CA3AF', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {label_a}
          </div>
          <div style={{ fontSize: 13, marginBottom: 6 }}>🪪</div>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#111827', wordBreak: 'break-word' }}>
            {value_a}
          </div>
          <div
            style={{
              display: 'inline-block',
              marginTop: 6,
              padding: '2px 8px',
              borderRadius: 4,
              background: '#DCFCE7',
              border: '1px solid #BBF7D0',
              color: '#16A34A',
              fontSize: 10,
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            {t.officialRecord}
          </div>
        </div>

        {/* Center divider */}
        <div style={{ fontSize: 24, fontWeight: 700, color: '#EF4444' }}>≠</div>

        {/* Right column */}
        <div>
          <div style={{ fontSize: 11, color: '#9CA3AF', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {label_b}
          </div>
          <div style={{ fontSize: 13, marginBottom: 6 }}>🏦</div>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#111827', wordBreak: 'break-word' }}>
            {value_b}
          </div>
          <div
            style={{
              display: 'inline-block',
              marginTop: 6,
              padding: '2px 8px',
              borderRadius: 4,
              background: '#FEF3C7',
              border: '1px solid #FDE68A',
              color: '#D97706',
              fontSize: 10,
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            {t.bankRecord}
          </div>
        </div>
      </div>

      {/* Similarity score bar */}
      {similarity_score !== undefined && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 12, color: '#6B7280', marginBottom: 6 }}>
            {t.matchScore}: {similarity_score}% — {t.minRequired}
          </div>
          <div style={{ position: 'relative', height: 8, background: '#E5E7EB', borderRadius: 4, overflow: 'hidden' }}>
            <div
              style={{
                position: 'absolute',
                left: 0,
                top: 0,
                bottom: 0,
                width: `${similarity_score}%`,
                background: '#EF4444',
                borderRadius: 4,
              }}
            />
            <div
              style={{
                position: 'absolute',
                left: '90%',
                top: -2,
                bottom: -2,
                width: 2,
                background: '#DC2626',
                borderLeft: '2px dashed #DC2626',
              }}
            />
          </div>
          <div style={{ fontSize: 10, color: '#DC2626', marginTop: 2, textAlign: 'right', marginRight: '10%' }}>
            90%
          </div>
        </div>
      )}

      {/* Fix instruction */}
      <div
        style={{
          background: '#EFF6FF',
          border: '1px solid #BFDBFE',
          borderRadius: 8,
          padding: 12,
          display: 'flex',
          gap: 10,
          alignItems: 'flex-start',
        }}
      >
        <span style={{ fontSize: 18, flexShrink: 0 }}>💡</span>
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#1E40AF', marginBottom: 4 }}>
            {t.howToFix}:
          </div>
          <div style={{ fontSize: 12, color: '#1E3A8A', lineHeight: 1.5 }}>
            {t.fixInstruction}
          </div>
        </div>
      </div>
    </div>
  )
}
