'use client'
import { useState, useTransition } from 'react'
import { toast } from 'sonner'
import { useRouter } from 'next/navigation'
import { clientProfileApi } from '@/lib/client/api'
import type { ProfileData } from '@/types'

/**
 * Profile data is fetched server-side and passed as a prop (initialProfile).
 * This hook only handles the SAVE mutation — no data fetching.
 */
export function useProfileSave() {
    const [saving, setSaving] = useState(false)
    const [, startTransition] = useTransition()
    const router = useRouter()

    const save = async (
        data: Partial<ProfileData> & { annual_income_bracket?: string }
    ): Promise<boolean> => {
        setSaving(true)
        try {
            await clientProfileApi.save(data as Record<string, unknown>)
            toast.success('Profile saved ✓', {
                description: 'Personalised recommendations have been updated.',
            })
            startTransition(() => router.refresh())
            return true
        } catch (e) {
            toast.error((e as Error).message || 'Failed to save profile. Try again.')
            return false
        } finally {
            setSaving(false)
        }
    }

    return { save, saving }
}
