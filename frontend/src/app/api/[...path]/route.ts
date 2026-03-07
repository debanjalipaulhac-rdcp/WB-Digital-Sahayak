// src/app/api/[...path]/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { cookies } from 'next/headers'

const BACKEND = process.env.NODE_ENV === 'development' ? 'http://localhost:8000/api/v1' : `${process.env.API_URL}/api/v1`

async function proxy(req: NextRequest, pathParts: string[], method: string) {
  const path = pathParts.join('/')
  const cookieStore = await cookies()
  const token = cookieStore.get('wb_access_token')?.value
  const url   = `${BACKEND}/${path}${req.nextUrl.search}`
  const body = method !== 'GET' ? await req.text() : undefined

  let backendRes: Response
  try {
    backendRes = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body,
    })
  } catch {
    return NextResponse.json({ detail: 'Backend unreachable' }, { status: 503 })
  }

  const data = await backendRes.json().catch(() => ({}))

  // On successful OTP verify → set HttpOnly cookies
  if (path === 'auth/verify-otp' && backendRes.ok) {
    const d = data as { access_token?: string; refresh_token?: string }
    if (d.access_token && d.refresh_token) {
      const res = NextResponse.json(data, { status: 200 })
      res.cookies.set('wb_access_token', d.access_token, {
        httpOnly: true,
        secure:   process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        maxAge:   60 * 60 * 24 * 7,
        path:     '/',
      })
      res.cookies.set('wb_refresh_token', d.refresh_token, {
        httpOnly: true,
        secure:   process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        maxAge:   60 * 60 * 24 * 30,
        path:     '/',
      })
      return res
    }
  }

  // On logout → clear cookies
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
