'use client'

import { useState } from 'react'
import { toast } from 'sonner'
import { eligibilityClient } from '@/lib/client/api'
import type { EligibilityResult, EligibilityCheckBody } from '@/types'

export function useEligibility() {
  const [result, setResult] = useState<EligibilityResult | null>(null)
  const [loading, setLoading] = useState(false)

  const check = async (
    body: EligibilityCheckBody
  ): Promise<EligibilityResult | null> => {
    setLoading(true)
    try {
      const data = await eligibilityClient.check(body)
      setResult(data)
      const fn =
        data.band === 'GREEN'
          ? toast.success
          : data.band === 'AMBER'
          ? toast.warning
          : toast.error
      fn(`Score: ${data.score}/100 — ${data.band_label}`, { duration: 6000 })
      return data
    } catch (e) {
      toast.error((e as Error).message)
      return null
    } finally {
      setLoading(false)
    }
  }

  const fetchScript = async (
    issueCode: string,
    lang = 'bn',
    aadhaar_name = '',
    bank_name = ''
  ) => {
    try {
      return await eligibilityClient.getScript(
        issueCode,
        lang,
        aadhaar_name,
        bank_name
      )
    } catch {
      toast.error('Could not load script')
      return null
    }
  }

  const reset = () => setResult(null)

  return { check, fetchScript, reset, result, loading }
}
