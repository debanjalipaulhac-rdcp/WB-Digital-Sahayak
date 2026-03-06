'use client'
import { useState } from 'react'
import { toast } from 'sonner'
import { clientEligibilityApi } from '@/lib/client/api'
import type { EligibilityResult, EligibilityCheckBody } from '@/types'
import { useLangStore } from '@/stores/lang.store'

export function useEligibility() {
    const [result, setResult] = useState<EligibilityResult | null>(null)
    const [loading, setLoading] = useState(false)
    const { lang } = useLangStore()

    const check = async (
        body: Omit<EligibilityCheckBody, 'lang'>
    ): Promise<EligibilityResult | null> => {
        setLoading(true)
        try {
            const data = await clientEligibilityApi.check({ ...body, lang })
            setResult(data)

            const toastFn =
                data.band === 'GREEN'
                    ? toast.success
                    : data.band === 'AMBER'
                        ? toast.warning
                        : toast.error

            toastFn(`Score: ${data.score}/100 — ${data.band_label}`, {
                description:
                    data.band === 'GREEN'
                        ? 'You are ready to apply!'
                        : data.band === 'AMBER'
                            ? 'Fix a few issues before applying.'
                            : 'Follow the roadmap before visiting.',
                duration: 6000,
            })

            return data
        } catch (e) {
            toast.error((e as Error).message || 'Eligibility check failed. Try again.')
            return null
        } finally {
            setLoading(false)
        }
    }

    return { check, result, loading }
}
