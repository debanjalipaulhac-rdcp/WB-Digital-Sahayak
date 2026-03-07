// src/lib/server/api.ts
// SERVER ONLY — import this ONLY in Server Components, Route Handlers, middleware
// NEVER import in "use client" files

import { cookies } from 'next/headers'
import type {
  Scheme,
  SchemesListResponse,
  RecommendationsResponse,
  ProfileData,
  ApplicationRecord,
  ScriptResponse,
  User
} from '@/types'

const API = process.env.NODE_ENV === 'development' ? 'http://localhost:8000/api/v1' : `${process.env.API_URL}/api/v1`

// ── Internal helper ────────────────────────────────────────────────────────

async function authHeaders(): Promise<Record<string, string>> {
  const cookieStore = await cookies()
  const token = cookieStore.get('wb_access_token')?.value
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function get<T>(
  path: string,
  revalidate: number | false = 60
): Promise<T | null> {
  try {

    const headers = await authHeaders()
    const res = await fetch(`${API}${path}`, {
      headers: { ...headers },
      next: revalidate === false ? { revalidate: 0 } : { revalidate },
    })
    if (!res.ok) return null
    return res.json() as Promise<T>
  } catch {
    return null
  }
}

// ── Public routes (no auth needed — rural users) ─────────────────────────

export async function getSchemes(params: {
  q?: string
  category?: string
  page?: number
  page_size?: number
  sort?: string
} = {}): Promise<SchemesListResponse> {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== '' && v !== 0)
        .map(([k, v]) => [k, String(v)])
    )
  ).toString()

  const data = await get<SchemesListResponse>(
    `/schemes${qs ? `?${qs}` : ''}`,
    300
  )
  return data ?? { schemes: [], total: 0, page: 1, pages: 1 }
}

export async function getSchemeById(schemeId: string): Promise<Scheme | null> {
  return get<Scheme>(`/schemes/${schemeId}`, 300)
}

export async function getRecommendations(params: {
  scheme_id?: string
  query?: string
  limit?: number
} = {}): Promise<RecommendationsResponse> {
  const qs = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined)
        .map(([k, v]) => [k, String(v)])
    )
  ).toString()

  // No cache — depends on auth cookie for personalisation
  const data = await get<RecommendationsResponse>(
    `/recommendations${qs ? `?${qs}` : ''}`,
    false
  )
  return data ?? { schemes: [], mode: 'featured', personalised: false }
}

export async function getScript(
  issueCode: string,
  lang = 'bn',
  aadhaar_name = '',
  bank_name = ''
): Promise<ScriptResponse | null> {
  const qs = new URLSearchParams({ lang, aadhaar_name, bank_name }).toString()
  return get<ScriptResponse>(`/script/${issueCode}?${qs}`, false)
}

// ── Auth-required routes ───────────────────────────────────────────────────

export async function getCurrentUser(): Promise<User | null> {
  return get<User>('/auth/me', false)
}

export async function getProfile(): Promise<ProfileData | null> {
  return get<ProfileData>('/profile', false)
}

export async function getApplications(limit = 10): Promise<ApplicationRecord[]> {
  const data = await get<{ applications: ApplicationRecord[]; count: number }>(
    `/applications?limit=${limit}`,
    false
  )
  return data?.applications ?? []
}
