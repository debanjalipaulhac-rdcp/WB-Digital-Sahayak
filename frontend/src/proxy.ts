import { NextRequest, NextResponse } from 'next/server'

// Only /profile routes require authentication - everything else is public
const PROTECTED_ROUTES = ['/profile']

export function proxy(req: NextRequest): NextResponse {
    const { pathname } = req.nextUrl

    const accessToken = req.cookies.get('wb_access_token')?.value
    const refreshToken = req.cookies.get('wb_refresh_token')?.value
    const lang = req.cookies.get('wb_lang')?.value ?? 'en'

    // Check if route requires authentication
    const isProtectedRoute = PROTECTED_ROUTES.some(route => pathname.startsWith(route))

    if (isProtectedRoute && !accessToken) {
        // Redirect to home with login modal trigger
        const url = req.nextUrl.clone()
        url.pathname = '/'
        url.searchParams.set('login', '1')
        return NextResponse.redirect(url)
    }

    // Set language header for server components
    const response = NextResponse.next()
    response.headers.set('x-wb-lang', ['en', 'bn', 'hi'].includes(lang) ? lang : 'en')
    
    // Pass auth tokens in headers for server components
    if (accessToken) {
        response.headers.set('x-wb-access-token', accessToken)
    }
    if (refreshToken) {
        response.headers.set('x-wb-refresh-token', refreshToken)
    }

    return response
}

export const config = {
    matcher: [
        /*
         * Match all request paths except for the ones starting with:
         * - api (API routes)
         * - _next/static (static files)
         * - _next/image (image optimization files)
         * - favicon.ico (favicon file)
         */
        '/((?!api|_next/static|_next/image|favicon.ico).*)',
    ],
}
