import {
    Bike, GraduationCap, Award, Heart, Star, HeartPulse, Wheat, BookOpen,
    ArrowRight, SlidersHorizontal, ChevronLeft, ChevronRight
} from 'lucide-react'
import SearchInputClient from './SearchInputClient'

const ALL_SCHEMES = [
    {
        slug: 'svmcm', name: 'SVMCM', tag: 'MERIT-CUM-MEANS', icon: 'Award',
        dept: 'Higher Education Dept.', color: '#7C3AED',
        desc: 'Swami Vivekananda Merit-cum-Means Scholarship for meritorious students from economically weaker sections pursuing higher studies.'
    },
    {
        slug: 'medhashree', name: 'Medhashree', tag: 'SCHOLARSHIP', icon: 'GraduationCap',
        dept: 'Backward Classes Welfare', color: '#059669',
        desc: 'Pre-matric scholarship for OBC students in West Bengal to support their educational journey from class V to VIII.'
    },
    {
        slug: 'aikyashree', name: 'Aikyashree', tag: 'SCHOLARSHIP', icon: 'BookOpen',
        dept: 'Minority Affairs & Madrasah Ed.', color: '#DC2626',
        desc: 'West Bengal State Scholarship Scheme for Minority Students providing financial assistance for various levels of education.'
    },
    {
        slug: 'sabuj-sathi', name: 'Sabuj Sathi', tag: 'SCHEME', icon: 'Bike',
        dept: 'Dept. of Backward Classes', color: '#D97706',
        desc: 'Bicycle distribution scheme for students in classes IX to XII to encourage higher education and reduce dropouts.'
    },
    {
        slug: 'lakshmir-bhandar', name: 'Lakshmir Bhandar', tag: 'FINANCIAL AID', icon: 'Heart',
        dept: 'Women & Child Development', color: '#DB2777',
        desc: 'Basic income support to female heads of households ensuring financial security and empowerment.'
    },
    {
        slug: 'kanyashree', name: 'Kanyashree', tag: 'GIRL CHILD', icon: 'Star',
        dept: 'Women & Child Development', color: '#7C3AED',
        desc: 'Conditional cash transfer scheme to improve the status and wellbeing of girls in West Bengal.'
    },
]

const ICON_MAP = { Bike, GraduationCap, Award, Heart, Star, HeartPulse, Wheat, BookOpen }
const PAGE_SIZE = 4

function SearchSchemeCard({ scheme }) {
    const IconComp = ICON_MAP[scheme.icon] || Award
    return (
        <a href={`/scheme/${scheme.slug}`} className="search-card">
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 12 }}>
                <div style={{
                    width: 48, height: 48, borderRadius: 12,
                    background: scheme.color + '20',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                    <IconComp size={24} color={scheme.color} />
                </div>
                <span style={{
                    fontSize: 10, fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase',
                    background: scheme.color + '15', color: scheme.color,
                    padding: '2px 8px', borderRadius: 4,
                }}>{scheme.tag}</span>
            </div>
            <div style={{ fontWeight: 700, fontSize: 20, color: 'var(--color-text)', marginBottom: 8 }}>{scheme.name}</div>
            <p className="line-clamp-3" style={{ fontSize: 13, color: 'var(--color-muted)', margin: '0 0 auto', lineHeight: 1.6, flexGrow: 1 }}>
                {scheme.desc}
            </p>
            <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                marginTop: 16, paddingTop: 12, borderTop: '1px solid var(--color-border)',
            }}>
                <span style={{ fontSize: 12, color: '#9CA3AF' }}>{scheme.dept}</span>
                <ArrowRight size={16} color="#1A56DB" />
            </div>
        </a>
    )
}

export default async function SearchPage({ searchParams }) {
    const params = await searchParams
    const query = params?.q || ''
    const category = params?.category || ''
    const page = parseInt(params?.page || '1', 10)

    // Filter
    const q = query.toLowerCase()
    let filtered = ALL_SCHEMES.filter(s =>
        !q || s.name.toLowerCase().includes(q) || s.desc.toLowerCase().includes(q) || s.tag.toLowerCase().includes(q)
    )
    if (category) {
        const tagMap = { woman: ['FINANCIAL AID', 'GIRL CHILD'], student: ['SCHOLARSHIP', 'MERIT-CUM-MEANS', 'SCHEME'], health: ['HEALTH'], farmers: ['AGRICULTURE'] }
        if (tagMap[category]) filtered = filtered.filter(s => tagMap[category].includes(s.tag))
    }

    const total = filtered.length
    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
    const paged = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

    const CATEGORIES = [
        { val: '', label: 'All' },
        { val: 'woman', label: 'Woman' },
        { val: 'student', label: 'Student' },
        { val: 'health', label: 'Health' },
        { val: 'farmers', label: 'Farmers' },
        { val: 'girl-child', label: 'Girl-child' },
    ]

    const DEPARTMENTS = ['All Departments', 'Higher Education', 'Backward Classes Welfare', 'Women & Child Development', 'Minority Affairs', 'Agriculture']

    function buildUrl(overrides = {}) {
        const p = { q: query, category, page, ...overrides }
        const qs = Object.entries(p).filter(([, v]) => v).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&')
        return `/search${qs ? '?' + qs : ''}`
    }

    return (
        <div style={{ background: 'var(--color-bg)', minHeight: '100vh' }}>

            {/* Hero bar */}
            <div style={{ background: '#1A56DB', padding: '40px 20px', textAlign: 'center' }}>
                <h1 style={{ color: '#fff', fontWeight: 700, fontSize: 32, margin: '0 0 20px' }}>Search Results</h1>
                <SearchInputClient defaultQuery={query} />
            </div>

            {/* Main content */}
            <div style={{ maxWidth: 1100, margin: '0 auto', padding: '28px 20px 48px', display: 'flex', gap: 24, alignItems: 'flex-start', flexWrap: 'wrap' }}>

                {/* Left sidebar */}
                <div style={{
                    width: 240, flexShrink: 0,
                    background: 'var(--color-surface, #fff)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 14, padding: 20,
                    position: 'sticky', top: 80,
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                        <SlidersHorizontal size={16} color="var(--color-muted)" />
                        <span style={{ fontWeight: 600, fontSize: 15, color: 'var(--color-text)' }}>Filters</span>
                    </div>

                    <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-muted)', marginBottom: 10 }}>
                        CATEGORIES
                    </div>
                    {CATEGORIES.map(cat => (
                        <a key={cat.val} href={buildUrl({ category: cat.val, page: 1 })} style={{
                            display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0',
                            textDecoration: 'none', color: category === cat.val ? '#1A56DB' : 'var(--color-text)',
                            fontWeight: category === cat.val ? 600 : 400, fontSize: 14,
                        }}>
                            <div style={{
                                width: 16, height: 16, borderRadius: '50%',
                                border: `2px solid ${category === cat.val ? '#1A56DB' : '#D1D5DB'}`,
                                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                            }}>
                                {category === cat.val && <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#1A56DB' }} />}
                            </div>
                            {cat.label}
                        </a>
                    ))}

                    <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-muted)', margin: '16px 0 10px' }}>
                        DEPARTMENT
                    </div>
                    <select style={{
                        width: '100%', border: '1.5px solid var(--color-border)', borderRadius: 8,
                        padding: '8px 10px', fontSize: 13, background: 'var(--color-surface, #fff)', color: 'var(--color-text)', outline: 'none',
                    }}>
                        {DEPARTMENTS.map(d => <option key={d}>{d}</option>)}
                    </select>
                </div>

                {/* Right content */}
                <div style={{ flex: 1, minWidth: 0 }}>
                    {/* Meta row */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20, flexWrap: 'wrap', gap: 8 }}>
                        <p style={{ fontSize: 14, color: 'var(--color-muted)', margin: 0 }}>
                            Showing <strong>{total}</strong> schemes{query ? <> for &ldquo;<em>{query}</em>&rdquo;</> : ''}
                        </p>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span style={{ fontSize: 13, color: 'var(--color-muted)' }}>Sort by:</span>
                            <select style={{
                                border: '1.5px solid var(--color-border)', borderRadius: 8,
                                padding: '6px 10px', fontSize: 13, background: 'var(--color-surface, #fff)', color: 'var(--color-text)', outline: 'none',
                            }}>
                                <option>Relevance</option>
                                <option>Name A-Z</option>
                                <option>Newest</option>
                            </select>
                        </div>
                    </div>

                    {/* Cards grid */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16, marginBottom: 28 }}>
                        {paged.map(s => <SearchSchemeCard key={s.slug} scheme={s} />)}
                        {paged.length === 0 && (
                            <div style={{ gridColumn: '1/-1', padding: '48px 0', textAlign: 'center', color: 'var(--color-muted)' }}>
                                No schemes found for your search. Try different keywords.
                            </div>
                        )}
                    </div>

                    {/* Pagination */}
                    {totalPages > 1 && (
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                            {page > 1 && (
                                <a href={buildUrl({ page: page - 1 })} style={{
                                    display: 'flex', alignItems: 'center', gap: 4, padding: '6px 12px',
                                    color: 'var(--color-muted)', textDecoration: 'none', fontSize: 14, border: '1.5px solid var(--color-border)', borderRadius: 8,
                                }}>
                                    <ChevronLeft size={16} /> Prev
                                </a>
                            )}
                            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1).map(p => (
                                <a key={p} href={buildUrl({ page: p })} style={{
                                    width: 36, height: 36, borderRadius: 8,
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    fontWeight: 500, fontSize: 14, textDecoration: 'none',
                                    ...(p === page
                                        ? { background: '#1A56DB', color: '#fff' }
                                        : { border: '1.5px solid var(--color-border)', color: 'var(--color-text)' }
                                    ),
                                }}>
                                    {p}
                                </a>
                            ))}
                            {page < totalPages && (
                                <a href={buildUrl({ page: page + 1 })} style={{
                                    display: 'flex', alignItems: 'center', gap: 4, padding: '6px 12px',
                                    color: 'var(--color-muted)', textDecoration: 'none', fontSize: 14, border: '1.5px solid var(--color-border)', borderRadius: 8,
                                }}>
                                    Next <ChevronRight size={16} />
                                </a>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
