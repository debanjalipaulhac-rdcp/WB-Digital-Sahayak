import { cookies } from 'next/headers'
import SearchInputClient from './SearchInputClient'
import SchemeCard from '@/components/SchemeCard'
import { getSchemes } from '@/lib/server/api'
import type { Scheme } from '@/types'

export const metadata = {
    title: 'Search Schemes — WB Digital Sahayak',
}

const CATEGORIES = ['Education', 'Health', 'Women', 'Agriculture', 'Financial Aid', 'Scholarship']
const DEPARTMENTS = ['Higher Education', 'Women & Child Dev.', 'Backward Classes', 'Health & Family Welfare']

const PAGE_SIZE = 6

interface SearchPageProps {
    searchParams: Promise<{ q?: string; cat?: string; dept?: string; page?: string }>
}

export default async function SearchPage({ searchParams }: SearchPageProps) {
    const params = await searchParams
    const q = params?.q || ''
    const selectedCat = params?.cat || ''
    const selectedDept = params?.dept || ''
    const page = parseInt(params?.page || '1', 10)

    const cookieStore = await cookies()
    void cookieStore

    // Fetch from real backend — fall back to empty on error
    const data = await getSchemes({ q: q || undefined }).catch(() => null)
    let schemes: Scheme[] = data?.schemes || []

    // Local dept filter (backend doesn't expose it as a param)
    if (selectedDept) {
        const ld = selectedDept.toLowerCase()
        schemes = schemes.filter(s =>
            (s.dept ?? '').toLowerCase().includes(ld) ||
            (s.department ?? '').toLowerCase().includes(ld)
        )
    }

    const total = schemes.length
    const totalPages = Math.ceil(total / PAGE_SIZE)
    const paged = schemes.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

    return (
        <div className="min-h-screen bg-gray-50 px-5 py-6 pb-12">
            <div className="max-w-6xl mx-auto">

                {/* Search input */}
                <SearchInputClient defaultQuery={q} />

                {/* Meta row */}
                <div className="flex items-center justify-between mt-4 mb-6 flex-wrap gap-2.5">
                    <span className="text-sm text-gray-500">
                        {total > 0
                            ? `Showing ${(page - 1) * PAGE_SIZE + 1}–${Math.min(page * PAGE_SIZE, total)} of ${total} results${q ? ` for "${q}"` : ''}`
                            : 'No schemes found'}
                    </span>
                </div>

                {/* Two column: sidebar + results */}
                <div className="detail-grid">

                    {/* Sidebar */}
                    <aside>
                        <div className="bg-white border border-gray-200 rounded-2xl p-5 mb-4">
                            <div className="font-semibold text-sm text-gray-900 mb-3">Category</div>
                            {CATEGORIES.map(cat => (
                                <a
                                    key={cat}
                                    href={`/search?${q ? `q=${encodeURIComponent(q)}&` : ''}cat=${encodeURIComponent(cat)}`}
                                    className={`block px-2.5 py-1.5 rounded-lg text-sm mb-0.5 no-underline transition-colors ${selectedCat === cat
                                            ? 'bg-blue-50 text-blue-600 font-semibold'
                                            : 'text-gray-500 hover:bg-gray-50 hover:text-gray-800'
                                        }`}
                                >
                                    {cat}
                                </a>
                            ))}
                        </div>

                        <div className="bg-white border border-gray-200 rounded-2xl p-5">
                            <div className="font-semibold text-sm text-gray-900 mb-3">Department</div>
                            {DEPARTMENTS.map(dept => (
                                <a
                                    key={dept}
                                    href={`/search?${q ? `q=${encodeURIComponent(q)}&` : ''}dept=${encodeURIComponent(dept)}`}
                                    className={`block px-2.5 py-1.5 rounded-lg text-sm mb-0.5 no-underline transition-colors ${selectedDept === dept
                                            ? 'bg-blue-50 text-blue-600 font-semibold'
                                            : 'text-gray-500 hover:bg-gray-50 hover:text-gray-800'
                                        }`}
                                >
                                    {dept}
                                </a>
                            ))}
                        </div>
                    </aside>

                    {/* Results */}
                    <main>
                        {paged.length === 0 ? (
                            <div className="text-center py-16">
                                <div className="text-5xl mb-4">🔍</div>
                                <h2 className="font-semibold text-xl text-gray-800 mb-2">No results found</h2>
                                <p className="text-sm text-gray-500 mb-4">Try different keywords or browse all schemes.</p>
                                <a href="/schemes" className="text-blue-600 font-medium text-sm hover:underline no-underline">
                                    View all schemes →
                                </a>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                                {paged.map(scheme => (
                                    <SchemeCard key={scheme.scheme_id} scheme={scheme} />
                                ))}
                            </div>
                        )}

                        {/* Pagination */}
                        {totalPages > 1 && (
                            <div className="flex justify-center gap-1.5 mt-8">
                                {Array.from({ length: totalPages }, (_, i) => i + 1).map(p => (
                                    <a
                                        key={p}
                                        href={`/search?q=${encodeURIComponent(q)}&page=${p}`}
                                        className={`w-9 h-9 flex items-center justify-center rounded-lg text-sm font-medium no-underline transition-colors ${p === page
                                                ? 'bg-blue-600 text-white'
                                                : 'border border-gray-200 text-gray-700 hover:border-blue-400 hover:text-blue-600'
                                            }`}
                                    >
                                        {p}
                                    </a>
                                ))}
                            </div>
                        )}
                    </main>
                </div>
            </div>
        </div>
    )
}
