'use client'
import { create } from 'zustand'
import type { ModalName } from '@/types'

interface UIStore {
    activeModal: ModalName
    eligibilitySchemeId: string | null
    openModal: (modal: ModalName, schemeId?: string) => void
    closeModal: () => void
}

export const useUIStore = create<UIStore>((set) => ({
    activeModal: null,
    eligibilitySchemeId: null,

    openModal: (modal, schemeId) =>
        set({ activeModal: modal, eligibilitySchemeId: schemeId ?? null }),

    closeModal: () =>
        set({ activeModal: null, eligibilitySchemeId: null }),
}))
