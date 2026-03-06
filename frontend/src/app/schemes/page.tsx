import { getSchemes } from '@/lib/server/api'
import { cookies } from 'next/headers'
import SchemeCard from '@/components/SchemeCard'
import type { Scheme } from '@/types'
import { Search } from 'lucide-react'

export const metadata = {
    title: 'All Schemes — WB Digital Sahayak',
    description: 'Browse all West Bengal government welfare schemes — scholarships, pensions, health cover, and more.',
}

const TAG_OPTIONS = [
    { label: 'All', value: '' },
    { label: 'Women', value: 'WOMEN' },
    { label: 'Health', value: 'HEALTH' },
    { label: 'Scholarship', value: 'SCHOLARSHIP' },
    { label: 'Pension', value: 'PENSION' },
    { label: 'Youth', value: 'YOUTH' },
    { label: 'Girl Child', value: 'GIRL_CHILD' },
    { label: 'Agriculture', value: 'AGRICULTURE' },
    { label: 'Marriage', value: 'MARRIAGE' },
]

interface SchemesPageProps {
    searchParams: Promise<{ tag?: string; q?: string; page?: string }>
}

export default async function SchemesPage({ searchParams }: SchemesPageProps) {
    const params = await searchParams
    const activeTag = params.tag || ''
    const q = params.q || ''
    const page = parseInt(params.page || '1', 10)

    // Read language for potential multi-lang display
    const cookieStore = await cookies()
    void cookieStore // used indirectly

    // Fetch from real API
    const data = await getSchemes({ tag: activeTag || undefined, page }).catch(() => null)
    let schemes: Scheme[] = data?.schemes || []
    const total = data?.total ?? schemes.length
    const pages = data?.pages ?? 1

    // Client-side name filter (when backend doesn't support name search on /schemes)
    if (q) {
        const lq = q.toLowerCase()
        schemes = schemes.filter(s =>
            s.scheme_name.toLowerCase().includes(lq) ||
            (s.description ?? '').toLowerCase().includes(lq) ||
            (s.benefit_display ?? '').toLowerCase().includes(lq)
        )
    }

    return (
        <div className="min-h-screen bg-gray-50">

            {/* ── Page header ── */}
            <div className="bg-white border-b border-gray-200">
                <div className="max-w-6xl mx-auto px-5 py-8">
                    <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-1">
                        All Welfare Schemes
                    </h1>
                    <p className="text-sm text-gray-500">
                        {total} schemes available · West Bengal Government
                    </p>

                    {/* Search bar */}
                    <form method="get" action="/schemes" className="mt-4 flex items-center gap-2 max-w-md">
                        <div className="relative flex-1">
                            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                            <input
                                name="q"
                                defaultValue={q}
                                placeholder="Search schemes…"
                                className="w-full pl-9 pr-4 py-2.5 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-50"
                            />
                        </div>
                        <button
                            type="submit"
                            className="px-4 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition-colors"
                        >
                            Search
                        </button>
                    </form>
                </div>
            </div>

            <div className="max-w-6xl mx-auto px-5 py-8">
                {/* ── Tag filter pills ── */}
                <div className="flex flex-wrap gap-2 mb-7">
                    {TAG_OPTIONS.map(({ label, value }) => {
                        const isActive = activeTag === value
                        const href = value
                            ? `/schemes?tag=${value}${q ? `&q=${encodeURIComponent(q)}` : ''}`
                            : `/schemes${q ? `?q=${encodeURIComponent(q)}` : ''}`
                        return (
                            <a
                                key={value}
                                href={href}
                                className={`px-4 py-1.5 rounded-full text-sm font-medium border transition-all ${isActive
                                        ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                                        : 'bg-white text-gray-600 border-gray-200 hover:border-blue-400 hover:text-blue-600'
                                    }`}
                            >
                                {label}
                            </a>
                        )
                    })}
                </div>

                {/* ── Results ── */}
                {schemes.length === 0 ? (
                    <div className="text-center py-20">
                        <div className="text-5xl mb-4">🔍</div>
                        <h2 className="text-xl font-semibold text-gray-800 mb-2">No schemes found</h2>
                        <p className="text-sm text-gray-500 mb-4">Try a different filter or search term.</p>
                        <a href="/schemes" className="text-blue-600 text-sm font-medium hover:underline">
                            Clear filters →
                        </a>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                        {schemes.map((scheme) => (
                            <SchemeCard key={scheme.scheme_id} scheme={scheme} />
                        ))}
                    </div>
                )}

                {/* ── Pagination ── */}
                {pages > 1 && (
                    <div className="flex justify-center gap-1.5 mt-10">
                        {Array.from({ length: pages }, (_, i) => i + 1).map((p) => {
                            const isActive = p === page
                            const href = `/schemes?${new URLSearchParams({
                                ...(activeTag ? { tag: activeTag } : {}),
                                ...(q ? { q } : {}),
                                page: String(p),
                            })}`
                            return (
                                <a
                                    key={p}
                                    href={href}
                                    className={`w-9 h-9 flex items-center justify-center rounded-lg text-sm font-medium transition-colors ${isActive
                                            ? 'bg-blue-600 text-white'
                                            : 'border border-gray-200 text-gray-700 hover:border-blue-400 hover:text-blue-600'
                                        }`}
                                >
                                    {p}
                                </a>
                            )
                        })}
                    </div>
                )}
            </div>
        </div>
    )
}
