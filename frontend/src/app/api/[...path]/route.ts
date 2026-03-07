// src/app/api/[...path]/route.ts
// Proxy: /api/* → backend/api/v1/*
// Handles: JSON (auth, eligibility, profile) + multipart (audio STT)

import { NextRequest, NextResponse } from 'next/server'
import { cookies } from 'next/headers'

const BACKEND =
  process.env.NODE_ENV === 'development'
    ? 'http://localhost:8000/api/v1'
    : `${process.env.API_URL}/api/v1`

async function proxy(
  req: NextRequest,
  pathParts: string[],
  method: string
): Promise<NextResponse> {
  const path  = pathParts.join('/')
  const cookieStore = await cookies()
  const token = cookieStore.get('wb_access_token')?.value
  const url   = `${BACKEND}/${path}${req.nextUrl.search}`
  const authHeader: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {}

  // ── Detect content type to decide how to forward the body ───────────────
  const contentType = req.headers.get('content-type') ?? ''
  const isMultipart = contentType.includes('multipart/form-data')

  let backendRes: Response
  try {
    if (method === 'GET') {
      // ── GET — no body ──────────────────────────────────────────────────
      backendRes = await fetch(url, {
        method: 'GET',
        headers: authHeader,
      })
    } else if (isMultipart) {
      // ── Multipart/form-data (audio STT upload) ─────────────────────────
      // Pass FormData directly — do NOT set Content-Type header.
      // fetch() sets it automatically with the correct boundary.
      const formData = await req.formData()
      backendRes = await fetch(url, {
        method,
        headers: authHeader,   // no Content-Type — fetch handles boundary
        body: formData,
      })
    } else {
      // ── JSON body (auth, eligibility, profile, etc.) ───────────────────
      const body = await req.text()
      backendRes = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...authHeader,
        },
        body: body || undefined,
      })
    }
  } catch {
    return NextResponse.json(
      { detail: 'Backend unreachable' },
      { status: 503 }
    )
  }

  // ── Parse response ───────────────────────────────────────────────────────
  const data = await backendRes.json().catch(() => ({}))

  // ── Special: set HttpOnly cookies on successful OTP verify ──────────────
  if (path === 'auth/verify-otp' && backendRes.ok) {
    const d = data as { access_token?: string; refresh_token?: string }
    if (d.access_token && d.refresh_token) {
      const res = NextResponse.json(data, { status: 200 })
      res.cookies.set('wb_access_token', d.access_token, {
        httpOnly: true,
        secure:   process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        maxAge:   60 * 60 * 24 * 7,   // 7 days
        path:     '/',
      })
      res.cookies.set('wb_refresh_token', d.refresh_token, {
        httpOnly: true,
        secure:   process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        maxAge:   60 * 60 * 24 * 30,  // 30 days
        path:     '/',
      })
      return res
    }
  }

  // ── Special: clear cookies on logout ────────────────────────────────────
  if (path === 'auth/logout') {
    const res = NextResponse.json({ success: true })
    res.cookies.delete('wb_access_token')
    res.cookies.delete('wb_refresh_token')
    return res
  }

  return NextResponse.json(data, { status: backendRes.status })
}

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params
  return proxy(req, path, 'GET')
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params
  return proxy(req, path, 'POST')
}