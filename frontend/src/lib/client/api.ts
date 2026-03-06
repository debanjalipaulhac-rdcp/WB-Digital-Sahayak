/**
 * Client-side fetch wrapper.
 * ONLY used inside "use client" components for mutations and interactive calls.
 * Token lives in HttpOnly cookie — browser sends it automatically.
 * All requests go through /api/* proxy (Next.js Route Handler) to avoid CORS.
 */

import type { EligibilityResult, ProfileData, EligibilityCheckBody } from '@/types'

const API_PROXY = '/api'

async function clientFetch<T>(
    path: string,
    options: RequestInit = {}
): Promise<T> {
    const res = await fetch(`${API_PROXY}${path}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...((options.headers as Record<string, string>) || {}),
        },
        credentials: 'include', // sends cookies automatically (including HttpOnly)
    })

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(
            (err as { detail?: string }).detail || `Error ${res.status}`
        )
    }

    return res.json() as Promise<T>
}

// ── Auth mutations ─────────────────────────────────────────────────────────

export const clientAuthApi = {
    sendOtp: (phone: string) =>
        clientFetch<{ success: boolean; message: string; expires_in: number }>(
            '/auth/send-otp',
            { method: 'POST', body: JSON.stringify({ phone }) }
        ),

    verifyOtp: (phone: string, otp: string) =>
        clientFetch<{
            success: boolean
            is_new_user: boolean
            user: { phone: string; name: string | null }
        }>('/auth/verify-otp', {
            method: 'POST',
            body: JSON.stringify({ phone, otp }),
        }),

    updateName: (name: string) =>
        clientFetch<{ success: boolean }>('/auth/update-name', {
            method: 'POST',
            body: JSON.stringify({ name }),
        }),

    logout: () =>
        clientFetch<void>('/auth/logout', { method: 'POST' }),
}

// ── Eligibility (mutation — triggered by user action) ──────────────────────

export const clientEligibilityApi = {
    check: (body: EligibilityCheckBody) =>
        clientFetch<EligibilityResult>('/eligibility', {
            method: 'POST',
            body: JSON.stringify(body),
        }),
}

// ── Profile (mutation) ─────────────────────────────────────────────────────

export const clientProfileApi = {
    save: (data: Record<string, unknown>) =>
        clientFetch<{ success: boolean; profile: ProfileData }>('/profile', {
            method: 'POST',
            body: JSON.stringify(data),
        }),
}
