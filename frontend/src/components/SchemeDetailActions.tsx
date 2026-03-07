'use client'

import { Button } from '@/components/ui/button'
import { useUIStore } from '@/stores/ui.store'
import { ClipboardCheck, MessageCircle } from 'lucide-react'

interface Props {
  schemeId: string
  schemeName: string
}

export function SchemeDetailActions({ schemeId, schemeName }: Props) {
  const { openModal } = useUIStore()

  const handleCheckEligibility = () => {
    openModal('eligibility', schemeId)
  }

  return (
    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', margin: '24px 0' }}>
      {/* PRIMARY: Check Eligibility */}
      <Button
        onClick={handleCheckEligibility}
        className="bg-blue-600 hover:bg-blue-700 text-white"
        style={{ flex: 1, minWidth: 200, height: 48, fontSize: 15, fontWeight: 600 }}
      >
        <ClipboardCheck size={18} style={{ marginRight: 8 }} />
        Check My Eligibility
      </Button>

      {/* SECONDARY: WhatsApp (pre-fills scheme name) */}
      <Button
        variant="outline"
        onClick={() =>
          window.open(
            `https://wa.me/14155238886?text=${encodeURIComponent(
              `Hi, I want to check my eligibility for ${schemeName}`
            )}`,
            '_blank'
          )
        }
        style={{
          flex: 1,
          minWidth: 160,
          height: 48,
          fontSize: 14,
          borderColor: '#25D366',
          color: '#25D366',
        }}
      >
        <MessageCircle size={18} style={{ marginRight: 8 }} />
        Ask on WhatsApp
      </Button>
    </div>
  )
}
