'use client'
import { useState, useTransition } from 'react'
import { toast } from 'sonner'
import { useRouter } from 'next/navigation'
import { clientAuthApi } from '@/lib/client/api'
import { useUIStore } from '@/stores/ui.store'

export function useAuth() {
    const [loading, setLoading] = useState(false)
    const [, startTransition] = useTransition()
    const router = useRouter()
    const { closeModal } = useUIStore()

    const sendOtp = async (phone: string): Promise<boolean> => {
        setLoading(true)
        try {
            const result = await clientAuthApi.sendOtp(phone)
            toast.success(result.message || 'OTP sent!')
            return true
        } catch (e) {
            toast.error((e as Error).message || 'Failed to send OTP')
            return false
        } finally {
            setLoading(false)
        }
    }

    const verifyOtp = async (
        phone: string,
        otp: string
    ): Promise<{ success: boolean; isNewUser: boolean }> => {
        setLoading(true)
        try {
            // Cookie (HttpOnly wb_access_token) is set by the Route Handler
            const result = await clientAuthApi.verifyOtp(phone, otp)
            toast.success(result.is_new_user ? 'Welcome to WB Sahayak! 🎉' : 'Welcome back!')
            // router.refresh() re-runs server components with the new cookie
            startTransition(() => router.refresh())
            return { success: true, isNewUser: result.is_new_user }
        } catch (e) {
            toast.error((e as Error).message || 'Incorrect OTP. Try again.')
            return { success: false, isNewUser: false }
        } finally {
            setLoading(false)
        }
    }

    const updateName = async (name: string): Promise<boolean> => {
        setLoading(true)
        try {
            await clientAuthApi.updateName(name)
            toast.success('Name saved!')
            closeModal()
            startTransition(() => router.refresh())
            return true
        } catch (e) {
            toast.error((e as Error).message || 'Failed to save name')
            return false
        } finally {
            setLoading(false)
        }
    }

    const logout = async (): Promise<void> => {
        try {
            await clientAuthApi.logout()
        } catch {
            // Always clear locally even if backend call fails
        }
        toast.success('Logged out successfully')
        startTransition(() => {
            router.refresh()
            router.push('/')
        })
    }

    return { sendOtp, verifyOtp, updateName, logout, loading }
}
