/**
 * Transparent proxy: /api/* → $API_URL/*
 *
 * - Reads wb_access_token cookie and forwards as Authorization header
 * - Avoids CORS completely — client never talks to :8000 directly
 *
 * Special handling:
 *   POST /api/auth/verify-otp → sets HttpOnly cookies on success
 *   POST /api/auth/logout     → clears HttpOnly cookies
 */
import { NextRequest, NextResponse } from 'next/server'
import { cookies } from 'next/headers'

const BACKEND = process.env.API_URL || 'http://localhost:8000/api/v1'

async function proxy(
    req: NextRequest,
    pathParts: string[],
    method: string
): Promise<NextResponse> {
    const path = pathParts.join('/')
    const cookieStore = await cookies()
    const token = cookieStore.get('wb_access_token')?.value
    const url = `${BACKEND}/${path}${req.nextUrl.search}`

    let body: string | undefined
    if (method !== 'GET' && method !== 'HEAD') {
        body = await req.text()
    }

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
        return NextResponse.json(
            { detail: 'Backend unreachable. Please try again.' },
            { status: 503 }
        )
    }

    const data = await backendRes.json().catch(() => ({}))

    // ── Special: set HttpOnly cookies on successful OTP verification ──
    if (
        path === 'auth/verify-otp' &&
        backendRes.ok &&
        (data as { success?: boolean }).success
    ) {
        const typedData = data as {
            success: boolean
            access_token: string
            refresh_token: string
            is_new_user: boolean
            user: { phone: string; name: string | null }
        }
        const res = NextResponse.json(
            {
                success: typedData.success,
                is_new_user: typedData.is_new_user,
                user: typedData.user,
            },
            { status: 200 }
        )
        const isProd = process.env.NODE_ENV === 'production'
        res.cookies.set('wb_access_token', typedData.access_token, {
            httpOnly: true,
            secure: isProd,
            sameSite: 'lax',
            maxAge: 60 * 60 * 24 * 7, // 7 days
            path: '/',
        })
        res.cookies.set('wb_refresh_token', typedData.refresh_token, {
            httpOnly: true,
            secure: isProd,
            sameSite: 'lax',
            maxAge: 60 * 60 * 24 * 30, // 30 days
            path: '/',
        })
        return res
    }

    // ── Special: clear cookies on logout ──
    if (path === 'auth/logout') {
        const res = NextResponse.json({ success: true })
        res.cookies.delete('wb_access_token')
        res.cookies.delete('wb_refresh_token')
        return res
    }

    return NextResponse.json(data, { status: backendRes.status })
}

// ── Route exports ─────────────────────────────────────────────────────────

export async function GET(
    req: NextRequest,
    { params }: { params: Promise<{ path: string[] }> }
): Promise<NextResponse> {
    const { path } = await params
    return proxy(req, path, 'GET')
}

export async function POST(
    req: NextRequest,
    { params }: { params: Promise<{ path: string[] }> }
): Promise<NextResponse> {
    const { path } = await params
    return proxy(req, path, 'POST')
}

export async function PUT(
    req: NextRequest,
    { params }: { params: Promise<{ path: string[] }> }
): Promise<NextResponse> {
    const { path } = await params
    return proxy(req, path, 'PUT')
}

export async function DELETE(
    req: NextRequest,
    { params }: { params: Promise<{ path: string[] }> }
): Promise<NextResponse> {
    const { path } = await params
    return proxy(req, path, 'DELETE')
}
