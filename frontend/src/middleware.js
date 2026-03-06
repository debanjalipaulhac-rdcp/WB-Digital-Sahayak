import { NextResponse } from 'next/server'

const SUPPORTED_LANGS = ['en', 'bn', 'hi']
const DEFAULT_LANG = 'en'

export function middleware(request) {
    const lang = request.cookies.get('wb_lang')?.value
    const validLang = SUPPORTED_LANGS.includes(lang) ? lang : DEFAULT_LANG

    const response = NextResponse.next()

    // Set lang header for server components to read
    response.headers.set('x-wb-lang', validLang)
https://13t2hxzp-8000.inc1.devtunnels.ms/
    return response
}

export const config = {
    matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
}
