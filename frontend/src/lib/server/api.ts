/**
 * Server-side fetch wrapper.
 * ONLY import this in: Server Components, Route Handlers, Server Actions.
 * NEVER import in "use client" files — it will crash (uses next/headers).
 */
import { cookies } from 'next/headers'
import type {
    SchemesListResponse,
    Scheme,
    RecommendationsResponse,
    ProfileData,
    ApplicationRecord,
    ScriptResponse,
} from '@/types'

const API = process.env.API_URL || 'http://localhost:8000/api/v1'

async function getAuthHeader(): Promise<Record<string, string>> {
    const cookieStore = await cookies()
    const token = cookieStore.get('wb_access_token')?.value
    return token ? { Authorization: `Bearer ${token}` } : {}
}

async function serverFetch<T>(
    path: string,
    options: RequestInit = {},
    revalidate: number | false = 60
): Promise<T> {
    const authHeader = await getAuthHeader()

    const res = await fetch(`${API}${path}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...authHeader,
            ...((options.headers as Record<string, string>) || {}),
        },
        next: revalidate === false ? { revalidate: 0 } : { revalidate },
    })

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(
            (err as { detail?: string }).detail || `API error ${res.status}`
        )
    }

    return res.json() as Promise<T>
}

// ── Schemes ──────────────────────────────────────────────────────────────

export async function getSchemes(
    params: {
        q?: string
        tag?: string
        category?: string
        page?: number
        page_size?: number
        sort?: string
    } = {}
): Promise<SchemesListResponse> {
    const qs = new URLSearchParams(
        Object.fromEntries(
            Object.entries(params)
                .filter(([, v]) => v !== undefined && v !== '')
                .map(([k, v]) => [k, String(v)])
        )
    ).toString()
    return serverFetch<SchemesListResponse>(
        `/schemes${qs ? `?${qs}` : ''}`,
        {},
        300 // 5-minute cache
    )
}


export async function getSchemeById(schemeId: string): Promise<Scheme> {
    return serverFetch<Scheme>(`/schemes/${schemeId}`, {}, 300)
}

export async function getRecommendations(
    params: {
        scheme_id?: string
        query?: string
        limit?: number
    } = {}
): Promise<RecommendationsResponse> {
    const qs = new URLSearchParams(
        Object.fromEntries(
            Object.entries(params)
                .filter(([, v]) => v !== undefined)
                .map(([k, v]) => [k, String(v)])
        )
    ).toString()
    // No cache — personalised per user
    return serverFetch<RecommendationsResponse>(
        `/recommendations${qs ? `?${qs}` : ''}`,
        {},
        false
    )
}

export async function getScript(
    issueCode: string,
    lang = 'bn',
    aadhaar_name = '',
    bank_name = ''
): Promise<ScriptResponse> {
    const qs = new URLSearchParams({ lang, aadhaar_name, bank_name }).toString()
    return serverFetch<ScriptResponse>(`/script/${issueCode}?${qs}`, {}, false)
}

// ── Profile (auth required) ───────────────────────────────────────────────

export async function getProfile(): Promise<ProfileData | null> {
    try {
        return await serverFetch<ProfileData>('/profile', {}, false)
    } catch {
        return null
    }
}

export async function getApplications(limit = 10): Promise<ApplicationRecord[]> {
    try {
        const data = await serverFetch<{ applications: ApplicationRecord[] }>(
            `/applications?limit=${limit}`,
            {},
            false
        )
        return data.applications
    } catch {
        return []
    }
}

// ── Current user ──────────────────────────────────────────────────────────

export async function getCurrentUser(): Promise<{
    phone: string
    name: string | null
    has_profile: boolean
} | null> {
    try {
        return await serverFetch<{
            phone: string
            name: string | null
            has_profile: boolean
        }>('/auth/me', {}, false)
    } catch {
        return null
    }
}
