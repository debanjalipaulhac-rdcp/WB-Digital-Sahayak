'use client'
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Lang } from '@/types'

interface LangStore {
    lang: Lang
    setLang: (lang: Lang) => void
}

export const useLangStore = create<LangStore>()(
    persist(
        (set) => ({
            lang: 'en',
            setLang: (lang) => {
                set({ lang })
                // Also write cookie so SSR server components and middleware can read it
                if (typeof document !== 'undefined') {
                    document.cookie = `wb_lang=${lang};path=/;max-age=31536000;samesite=lax`
                }
            },
        }),
        { name: 'wb_lang' }
    )
)
