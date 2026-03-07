/**
 * app/not-found.tsx
 * Server Component — rendered for any unmatched route (404).
 */
import { Search, Home, FileSearch } from 'lucide-react'

export const metadata = {
    title: '404 — Page Not Found | WB Digital Sahayak',
}

export default function NotFound() {
    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center px-5">
            <div className="bg-white border border-gray-200 rounded-2xl shadow-sm p-8 max-w-md w-full text-center">

                {/* Icon */}
                <div className="w-16 h-16 bg-blue-50 border border-blue-100 rounded-2xl flex items-center justify-center mx-auto mb-5">
                    <FileSearch size={28} className="text-blue-500" />
                </div>

                <span className="text-5xl font-black text-gray-200 block mb-2">404</span>
                <h1 className="text-xl font-bold text-gray-900 mb-2">Page not found</h1>
                <p className="text-sm text-gray-500 leading-relaxed mb-6">
                    The page you are looking for does not exist or may have been moved.
                </p>

                <div className="flex flex-col sm:flex-row gap-3 justify-center">
                    <a
                        href="/"
                        className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-xl hover:bg-blue-700 transition-colors no-underline"
                    >
                        <Home size={15} /> Go Home
                    </a>
                    <a
                        href="/schemes"
                        className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-white border border-gray-200 text-gray-700 text-sm font-semibold rounded-xl hover:border-blue-400 hover:text-blue-600 transition-colors no-underline"
                    >
                        <Search size={15} /> Browse Schemes
                    </a>
                </div>
            </div>
        </div>
    )
}
