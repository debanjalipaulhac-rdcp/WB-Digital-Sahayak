'use client'

import { useState, useTransition } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { authClient } from '@/lib/client/api'
import { useUIStore } from '@/stores/ui.store'

export function useAuth() {
  const [loading, setLoading] = useState(false)
  const [, startTransition] = useTransition()
  const router = useRouter()
  const { closeModal } = useUIStore()

  const sendOtp = async (phone: string): Promise<boolean> => {
    setLoading(true)
    try {
      const res = await authClient.sendOtp(phone)
      toast.success(res.message ?? 'OTP sent!')
      return true
    } catch (e) {
      toast.error((e as Error).message ?? 'Failed to send OTP')
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
      const res = await authClient.verifyOtp(phone, otp)
      // Cookie is set by proxy route handler — no localStorage needed
      toast.success(res.is_new_user ? 'Welcome! 🎉' : 'Welcome back!')
      startTransition(() => router.refresh())  // re-run server components
      return { success: true, isNewUser: res.is_new_user }
    } catch (e) {
      toast.error((e as Error).message ?? 'Invalid OTP')
      return { success: false, isNewUser: false }
    } finally {
      setLoading(false)
    }
  }

  const updateName = async (name: string): Promise<boolean> => {
    setLoading(true)
    try {
      await authClient.updateName(name)
      toast.success('Name saved!')
      closeModal()
      startTransition(() => router.refresh())
      return true
    } catch (e) {
      toast.error((e as Error).message)
      return false
    } finally {
      setLoading(false)
    }
  }

  const logout = async (): Promise<void> => {
    try { await authClient.logout() } catch { /* always clear */ }
    toast.success('Logged out')
    startTransition(() => {
      router.refresh()
      router.push('/')
    })
  }

  return { sendOtp, verifyOtp, updateName, logout, loading }
}
