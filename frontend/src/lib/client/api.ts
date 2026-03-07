// src/lib/client/api.ts
// CLIENT ONLY — used inside "use client" hooks and components
// Token is in HttpOnly cookie — browser sends it automatically
// All calls go through /api proxy to avoid CORS

import type {
  EligibilityResult,
  EligibilityCheckBody,
  ProfileData,
  ScriptResponse,
  User
} from '@/types'

const PROXY = '/api'

async function call<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${PROXY}${path}`, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...((options.headers as Record<string, string>) ?? {}),
    },
  })
  
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error((err as { detail?: string }).detail ?? `Error ${res.status}`)
  }
  
  return res.json() as Promise<T>
}

// ── Auth (POST mutations) ──────────────────────────────────────────────────

export const authClient = {
  sendOtp: (phone: string) =>
    call<{ success: boolean; message: string; expires_in: number }>(
      '/auth/send-otp',
      { method: 'POST', body: JSON.stringify({ phone }) }
    ),

  verifyOtp: (phone: string, otp: string) =>
    call<{ success: boolean; is_new_user: boolean; user: User }>(
      '/auth/verify-otp',
      { method: 'POST', body: JSON.stringify({ phone, otp }) }
    ),

  updateName: (name: string) =>
    call<{ success: boolean }>(
      '/auth/update-name',
      {
        method: 'POST',
        body: JSON.stringify({ name }),
      }
    ),

  logout: () => call<void>('/auth/logout', { method: 'POST' }),
}

// ── Eligibility (POST mutation — interactive form) ─────────────────────────

export const eligibilityClient = {
  check: (body: EligibilityCheckBody) =>
    call<EligibilityResult>('/eligibility', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  getScript: (
    issueCode: string,
    lang = 'bn',
    aadhaar_name = '',
    bank_name = ''
  ) =>
    call<ScriptResponse>(
      `/script/${issueCode}?${new URLSearchParams({ lang, aadhaar_name, bank_name })}`
    ),
}

// ── Profile (mutation — auth required) ────────────────────────────────────

export const profileClient = {
  getProfile: () => call<ProfileData>('/profile'),
  
  saveProfile: (data: Partial<ProfileData>) =>
    call<{ success: boolean; profile: ProfileData }>(
      '/profile',
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    ),
}

// ── Schemes (for application history) ─────────────────────────────────────

export const schemesClient = {
  getApplications: (limit = 10) =>
    call<{ applications: import('@/types').ApplicationRecord[] }>(
      `/applications?limit=${limit}`
    ),
}

// ── Named exports for convenience ──────────────────────────────────────────

export const auth = authClient
export const eligibility = eligibilityClient
export const profile = profileClient
export const schemes = schemesClient
