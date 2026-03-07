'use client'

import { useState, useTransition } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { profileClient } from '@/lib/client/api'
import type { ProfileData } from '@/types'

// Profile data is ALWAYS fetched server-side and passed as a prop.
// This hook handles only the SAVE mutation.
export function useProfileSave() {
  const [saving, setSaving] = useState(false)
  const [, startTransition] = useTransition()
  const router = useRouter()

  const save = async (data: Partial<ProfileData>): Promise<boolean> => {
    setSaving(true)
    try {
      await profileClient.saveProfile(data)
      toast.success('Profile saved ✓', {
        description: 'Personalised recommendations updated.',
      })
      startTransition(() => router.refresh())
      return true
    } catch (e) {
      toast.error((e as Error).message)
      return false
    } finally {
      setSaving(false)
    }
  }

  return { save, saving }
}
