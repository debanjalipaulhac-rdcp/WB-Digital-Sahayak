import { NextRequest, NextResponse } from 'next/server'

const PROTECTED_ROUTES = ['/profile', '/applications']

export function middleware(req: NextRequest): NextResponse {
    const { pathname } = req.nextUrl
    const token = req.cookies.get('wb_access_token')?.value
    const lang = req.cookies.get('wb_lang')?.value || 'en'

    // Redirect unauthenticated users away from protected routes
    if (PROTECTED_ROUTES.some((r) => pathname.startsWith(r)) && !token) {
        const url = req.nextUrl.clone()
        url.pathname = '/'
        url.searchParams.set('login', '1') // signal home page to open auth modal
        return NextResponse.redirect(url)
    }

    // Pass lang header so server components can read it without async cookies()
    const res = NextResponse.next()
    res.headers.set('x-wb-lang', ['en', 'bn', 'hi'].includes(lang) ? lang : 'en')
    return res
}

export const config = {
    matcher: ['/((?!_next/static|_next/image|favicon.ico|api/).*)'],
}
