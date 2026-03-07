// SERVER COMPONENT — SSR
import { getSchemes } from '@/lib/server/api'
import { cookies } from 'next/headers'
import SchemeCard from '@/components/SchemeCard'
import { Search } from 'lucide-react'
import Link from 'next/link'

export const metadata = {
    title: 'All Schemes — WB Digital Sahayak',
    description: 'Browse all West Bengal government welfare schemes — scholarships, pensions, health cover, and more.',
}

const TAG_OPTIONS = [
    { label: 'All', value: '' },
    { label: 'Women', value: 'women' },
    { label: 'Health', value: 'health' },
    { label: 'Youth', value: 'youth' },
    { label: 'Farmers', value: 'farmers' },
    { label: 'Girl Child', value: 'girl_child' },
]

interface SchemesPageProps {
    searchParams: Promise<{ category?: string; q?: string; page?: string }>
}

export default async function SchemesPage({ searchParams }: SchemesPageProps) {
    const params = await searchParams
    console.log(params)
    const activeCategory = params.category || ''
    const q = params.q || ''
    const page = parseInt(params.page || '1', 10)

    // Fetch schemes using proper API
    const data = await getSchemes({
        q: q || undefined,
        category: activeCategory || undefined,
        page,
        page_size: 12,
        sort: 'relevance',
    })
    
    const schemes = data?.schemes ?? []
    const total = data?.total ?? 0
    const totalPages = data?.pages ?? 1

    return (
        <div className="min-h-screen bg-background">

            {/* ── Page header ── */}
            <div className="bg-card border-b">
                <div className="max-w-6xl mx-auto px-5 py-8">
                    <h1 className="text-2xl sm:text-3xl font-bold mb-1 ">
                        All Welfare Schemes
                    </h1>
                    <p className="text-sm text-gray-500">
                        {total} schemes available · West Bengal Government
                    </p>

                    {/* Search bar */}
                    <form method="get" action="/schemes" className="mt-4 flex items-center gap-2 max-w-md">
                        <div className="relative flex-1">
                            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-accent" />
                            <input
                                name="q"
                                defaultValue={q}
                                placeholder="Search schemes…"
                                className="w-full pl-9 pr-4 py-2.5 rounded-lg border text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-muted text-foreground"
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
                        const isActive = activeCategory === value
                        const href = value
                            ? `/schemes?category=${value}${q ? `&q=${encodeURIComponent(q)}` : ''}`
                            : `/schemes${q ? `?q=${encodeURIComponent(q)}` : ''}`
                        return (
                            <a
                                key={value}
                                href={href}
                                className={`px-4 py-1.5 rounded-full text-sm font-medium border transition-all ${isActive
                                    ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                                    : 'bg-muted text-muted-foreground hover:border-primary-foreground hover:text-primary'
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
                {totalPages > 1 && (
                    <div className="flex justify-center gap-1.5 mt-10">
                        {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                            const p = i + 1
                            const isActive = p === page
                            const href = `/schemes?${new URLSearchParams({
                                ...(activeCategory ? { category: activeCategory } : {}),
                                ...(q ? { q } : {}),
                                page: String(p),
                            })}`
                            return (
                                <Link
                                    key={p}
                                    href={href}
                                    className={`w-9 h-9 flex items-center justify-center rounded-lg text-sm font-medium transition-colors ${isActive
                                        ? 'bg-blue-600 text-white'
                                        : 'border border-gray-200 text-gray-700 hover:border-blue-400 hover:text-blue-600'
                                        }`}
                                >
                                    {p}
                                </Link>
                            )
                        })}
                    </div>
                )}
            </div>
        </div>
    )
}
