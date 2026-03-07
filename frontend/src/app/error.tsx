'use client'
/**
 * app/error.tsx
 * Client error boundary — catches thrown errors in server component trees.
 * Must be a Client Component (Next.js requirement — needs the `reset` callback).
 */
import { useEffect } from 'react'
import { AlertTriangle, RefreshCw, Home } from 'lucide-react'

interface ErrorPageProps {
    error: Error & { digest?: string }
    reset: () => void
}

export default function ErrorPage({ error, reset }: ErrorPageProps) {
    useEffect(() => {
        // Log to your error reporting service here
        console.error('[Page Error]', error)
    }, [error])

    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center px-5">
            <div className="bg-white border border-gray-200 rounded-2xl shadow-sm p-8 max-w-md w-full text-center">

                {/* Icon */}
                <div className="w-16 h-16 bg-red-50 border border-red-100 rounded-2xl flex items-center justify-center mx-auto mb-5">
                    <AlertTriangle size={28} className="text-red-500" />
                </div>

                <h1 className="text-xl font-bold text-gray-900 mb-2">Something went wrong</h1>
                <p className="text-sm text-gray-500 leading-relaxed mb-1">
                    {error.message.includes('fetch') || error.message.includes('API')
                        ? 'Could not reach the server. Please check your connection and try again.'
                        : 'An unexpected error occurred. Our team has been notified.'}
                </p>
                {error.digest && (
                    <p className="text-xs text-gray-400 font-mono mb-5">ref: {error.digest}</p>
                )}

                <div className="flex flex-col sm:flex-row gap-3 justify-center mt-6">
                    <button
                        onClick={reset}
                        className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-xl hover:bg-blue-700 transition-colors"
                    >
                        <RefreshCw size={15} /> Try Again
                    </button>
                    <a
                        href="/"
                        className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-white border border-gray-200 text-gray-700 text-sm font-semibold rounded-xl hover:border-blue-400 hover:text-blue-600 transition-colors no-underline"
                    >
                        <Home size={15} /> Go Home
                    </a>
                </div>
            </div>
        </div>
    )
}
