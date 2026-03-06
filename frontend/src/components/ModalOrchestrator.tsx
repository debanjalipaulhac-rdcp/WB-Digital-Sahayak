'use client'
import dynamic from 'next/dynamic'
import { useUIStore } from '@/stores/ui.store'

// Lazy-load modals — don't bundle them in the initial JS payload
const AuthModal = dynamic(() => import('./AuthModal'))
const EligibilityModal = dynamic(() => import('./CheckEligibilityModal'))
const VoiceModal = dynamic(() => import('./VoiceSearchModal'))

interface Props {
    user: { name: string | null; phone: string } | null
}

export function ModalOrchestrator({ user }: Props) {
    const { activeModal, closeModal } = useUIStore()

    return (
        <>
            {activeModal === 'auth' && (
                <AuthModal isOpen onClose={closeModal} />
            )}
            {activeModal === 'eligibility' && (
                <EligibilityModal isOpen onClose={closeModal} user={user} />
            )}
            {activeModal === 'voice' && (
                <VoiceModal isOpen onClose={closeModal} />
            )}
        </>
    )
}
