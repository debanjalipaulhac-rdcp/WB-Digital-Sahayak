import { cookies } from 'next/headers'
import SearchInputClient from './SearchInputClient'
import SchemeCard from '@/components/SchemeCard'
import { getSchemes } from '@/lib/server/api'
import type { Scheme } from '@/types'
import Link from 'next/link'
import DepartMent from './DepartMent'

export const metadata = {
    title: 'Search Schemes — WB Digital Sahayak',
}

const CATEGORIES = ['Education', 'Health', 'Women', 'Agriculture', 'Financial Aid', 'Scholarship']


const PAGE_SIZE = 6

interface SearchPageProps {
    searchParams: Promise<{ q?: string; category?: string; dept?: string; page?: string }>
}

export default async function SearchPage({ searchParams }: SearchPageProps) {
    const params = await searchParams
    const q = params?.q || ''
    const selectedCat = params?.category || ''
    const selectedDept = params?.dept || ''
    const page = parseInt(params?.page || '1', 10)

    const cookieStore = await cookies()
    void cookieStore


    const data = await getSchemes({
        q: q || undefined,
        category: selectedCat || undefined
    }).catch(() => null)

    let schemes: Scheme[] = data?.schemes || []


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
        <div className="min-h-screen bg-background px-5 py-6 pb-12">
            <div className="max-w-6xl mx-auto">

                {/* Search input */}
                <SearchInputClient defaultQuery={q} />

                {/* Meta row */}
                <div className="flex items-center justify-between mt-4 mb-6 flex-wrap gap-2.5">
                    <span className="text-sm text-muted-foreground">
                        {total > 0
                            ? `Showing ${(page - 1) * PAGE_SIZE + 1}–${Math.min(page * PAGE_SIZE, total)} of ${total} results${q ? ` for "${q}"` : ''}`
                            : 'No schemes found'}
                    </span>
                </div>

                {/* Two column: sidebar + results */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">

                    {/* Sidebar */}
                    <aside>
                        <div className="bg-muted/50 border  rounded-2xl p-5 mb-4">
                            <div className="font-semibold text-sm text-foreground/70 mb-3">Category</div>
                            <Link
                                href={`/search`}
                                className={`block px-2.5 py-1.5 rounded-lg text-sm mb-0.5 no-underline transition-colors ${selectedCat === ''
                                    ? 'bg-primary-foreground text-primary font-semibold'
                                    : 'text-gray-500 hover:bg-background/50 hover:text-accent'
                                    }`}
                            >
                                All
                            </Link>
                            {CATEGORIES.map(cat => (
                                <Link
                                    key={cat}
                                    href={`/search?${q ? `q=${encodeURIComponent(q)}&` : ''}category=${encodeURIComponent(cat)}`}
                                    className={`block px-2.5 py-1.5 rounded-lg text-sm mb-0.5 no-underline transition-colors ${selectedCat === cat
                                        ? 'bg-accent text-blue-600 font-semibold'
                                        : 'text-gray-500 hover:bg-gray-50 hover:text-gray-800'
                                        }`}
                                >
                                    {cat}
                                </Link>
                            ))}
                            <div className="bg-muted border rounded-2xl p-3 mt-4">
                                <div className="font-semibold text-sm text-foreground/70 mb-3">Department</div>
                                <DepartMent q={q} dept={selectedDept} />
                            </div>
                        </div>


                    </aside>

                    {/* Results */}
                    <main className=' col-span-3'>
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
