import { cookies } from 'next/headers'
import {
    Bike, GraduationCap, Award, Heart, Star, HeartPulse, Wheat, BookOpen,
    SlidersHorizontal, Users, CreditCard, FileText, CalendarClock, IndianRupee,
    ShieldCheck, ArrowRight, Lightbulb, ClipboardList, FolderOpen, ExternalLink, Bot,
    LucideIcon
} from 'lucide-react'

interface DirScheme {
    slug: string
    name: string
    tag: string
    icon: string
    dept: string
    accentColor: string
    desc: string
    benefitLine: string
    benefitIcon: string
}

const ALL_DIR_SCHEMES: DirScheme[] = [
    {
        slug: 'sabuj-sathi', name: 'Sabuj Sathi', tag: 'SCHEME', icon: 'Bike',
        dept: 'Dept. of Backward Classes', accentColor: '#3B82F6',
        desc: 'Bicycle distribution scheme for students in classes IX to XII to encourage higher education and reduce dropouts.',
        benefitLine: '5M+ Beneficiaries', benefitIcon: 'Users'
    },
    {
        slug: 'medhashree', name: 'Medhashree', tag: 'SCHOLARSHIP', icon: 'GraduationCap',
        dept: 'Backward Classes Welfare', accentColor: '#10B981',
        desc: 'Pre-matric scholarship for OBC students in West Bengal to support their educational journey.',
        benefitLine: 'DBT Transfer', benefitIcon: 'CreditCard'
    },
    {
        slug: 'svmcm', name: 'SVMCM', tag: 'MERIT-CUM-MEANS', icon: 'Award',
        dept: 'Higher Education Dept.', accentColor: '#7C3AED',
        desc: 'Swami Vivekananda Merit-cum-Means Scholarship for meritorious students from economically weaker sections.',
        benefitLine: 'Online Application', benefitIcon: 'FileText'
    },
    {
        slug: 'lakshmir-bhandar', name: 'Lakshmir Bhandar', tag: 'FINANCIAL AID', icon: 'Heart',
        dept: 'Women & Child Development', accentColor: '#EC4899',
        desc: 'Basic income support to female heads of households ensuring financial security and empowerment.',
        benefitLine: 'Monthly Payout', benefitIcon: 'CalendarClock'
    },
    {
        slug: 'kanyashree', name: 'Kanyashree', tag: 'GIRL CHILD', icon: 'Star',
        dept: 'Women & Child Development', accentColor: '#F59E0B',
        desc: 'Conditional cash transfer scheme to improve the status and wellbeing of girls in West Bengal.',
        benefitLine: 'Annual Payout', benefitIcon: 'IndianRupee'
    },
    {
        slug: 'swasthya-sathi', name: 'Swasthya Sathi', tag: 'HEALTH', icon: 'HeartPulse',
        dept: 'Health & Family Welfare', accentColor: '#EF4444',
        desc: 'Health insurance scheme providing cashless treatment up to ₹5 lakh per family per year.',
        benefitLine: '₹5L Coverage', benefitIcon: 'ShieldCheck'
    },
    {
        slug: 'krishak-bondhu', name: 'Krishak Bondhu', tag: 'AGRICULTURE', icon: 'Wheat',
        dept: 'Agriculture Dept.', accentColor: '#84CC16',
        desc: 'Financial assistance to farmers for crop cultivation and support during distress.',
        benefitLine: '₹10,000/year', benefitIcon: 'IndianRupee'
    },
    {
        slug: 'aikyashree', name: 'Aikyashree', tag: 'SCHOLARSHIP', icon: 'BookOpen',
        dept: 'Minority Affairs', accentColor: '#6366F1',
        desc: 'Scholarship for Minority Students providing financial assistance for various levels of education.',
        benefitLine: 'Annual Scholarship', benefitIcon: 'GraduationCap'
    },
]

const ICON_MAP: Record<string, LucideIcon> = {
    Bike, GraduationCap, Award, Heart, Star, HeartPulse, Wheat, BookOpen,
    Users, CreditCard, FileText, CalendarClock, IndianRupee, ShieldCheck, ArrowRight, ExternalLink
}

const CATEGORY_TABS = [
    { label: 'All Schemes', value: '' },
    { label: 'Education', value: 'education' },
    { label: 'Health & Welfare', value: 'health' },
    { label: 'Social Security', value: 'social' },
    { label: 'Agriculture', value: 'agriculture' },
    { label: 'Women', value: 'women' },
    { label: 'Farmers', value: 'farmers' },
]

const PAGE_SIZE = 4

function DirectorySchemeCard({ scheme }: { scheme: DirScheme }) {
    const IconComp = ICON_MAP[scheme.icon] || Award
    const BenefitIcon = ICON_MAP[scheme.benefitIcon] || Users
    return (
        <a href={`/scheme/${scheme.slug}`} className="dir-card"
            style={{ borderLeftColor: scheme.accentColor }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 8 }}>
                <div style={{
                    width: 40, height: 40,
                    background: scheme.accentColor + '20',
                    borderRadius: 10,
                    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}>
                    <IconComp size={22} color={scheme.accentColor} />
                </div>
                <span style={{
                    fontSize: 10, fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase',
                    background: scheme.accentColor + '20', color: scheme.accentColor,
                    padding: '2px 8px', borderRadius: 4,
                }}>{scheme.tag}</span>
            </div>
            <div style={{ fontSize: 11, fontWeight: 600, color: scheme.accentColor, marginBottom: 3 }}>
                {scheme.dept}
            </div>
            <div style={{ fontWeight: 700, fontSize: 17, color: 'var(--color-text)', marginBottom: 6 }}>
                {scheme.name}
            </div>
            <p className="line-clamp-3" style={{ fontSize: 13, color: 'var(--color-muted)', margin: '0 0 auto', lineHeight: 1.5, flexGrow: 1 }}>
                {scheme.desc}
            </p>
            <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                marginTop: 16, paddingTop: 12, borderTop: '1px solid var(--color-border)',
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--color-muted)' }}>
                    <BenefitIcon size={14} />
                    {scheme.benefitLine}
                </div>
                <div style={{
                    width: 36, height: 36, borderRadius: '50%',
                    background: '#111928', display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                    <ArrowRight size={16} color="white" />
                </div>
            </div>
        </a>
    )
}

interface SearchParams {
    category?: string
    page?: string
}

export default async function SchemesPage({ searchParams }: { searchParams: Promise<SearchParams> }) {
    const params = await searchParams
    const category = params?.category || ''
    const page = parseInt(params?.page || '1', 10)

    let schemes = ALL_DIR_SCHEMES
    const catMap: Record<string, string[]> = {
        education: ['SCHOLARSHIP', 'MERIT-CUM-MEANS', 'SCHEME'],
        health: ['HEALTH'],
        social: ['FINANCIAL AID', 'GIRL CHILD'],
        agriculture: ['AGRICULTURE'],
        women: ['FINANCIAL AID', 'GIRL CHILD'],
        farmers: ['AGRICULTURE'],
    }
    if (category && catMap[category]) {
        schemes = schemes.filter(s => catMap[category].includes(s.tag))
    }

    const total = schemes.length
    const totalPages = Math.ceil(total / PAGE_SIZE)
    const paged = schemes.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

    // lang for potential future use
    const cookieStore = await cookies()
    const rawLang = cookieStore.get('wb_lang')?.value
    const _lang = ['en', 'bn', 'hi'].includes(rawLang ?? '') ? rawLang! : 'en'
    void _lang

    return (
        <div style={{ background: 'var(--color-bg)', minHeight: '100vh', padding: '32px 20px 48px' }}>
            <div style={{ maxWidth: 1100, margin: '0 auto' }}>

                {/* Header */}
                <div style={{ marginBottom: 28 }}>
                    <h1 style={{ fontWeight: 700, fontSize: 32, color: 'var(--color-text)', margin: '0 0 6px' }}>
                        Schemes Directory
                    </h1>
                    <p style={{ color: 'var(--color-muted)', fontSize: 14, margin: 0 }}>
                        Discover and apply for welfare programs tailored to your needs across all departments.
                    </p>
                </div>

                {/* Search bar */}
                <form action="/search" method="get" style={{
                    display: 'flex', alignItems: 'center', gap: 12,
                    border: '1.5px solid var(--color-border)', borderRadius: 14,
                    padding: '12px 16px', background: 'var(--color-surface, #fff)', marginBottom: 20,
                }}>
                    <SlidersHorizontal size={18} color="var(--color-muted)" style={{ flexShrink: 0 }} />
                    <input name="q" type="text" placeholder="Search schemes, departments, or keywords..."
                        style={{ flex: 1, border: 'none', outline: 'none', fontSize: 15, background: 'transparent', color: 'var(--color-text)' }} />
                    <button type="submit" style={{
                        display: 'flex', alignItems: 'center', gap: 6,
                        border: '1.5px solid var(--color-border)', borderRadius: 8,
                        padding: '7px 14px', background: 'transparent', cursor: 'pointer',
                        fontSize: 13, color: 'var(--color-muted)', whiteSpace: 'nowrap',
                    }}>
                        <SlidersHorizontal size={14} /> Filters
                    </button>
                </form>

                {/* Category tabs */}
                <div style={{ display: 'flex', gap: 8, overflowX: 'auto', marginBottom: 28, paddingBottom: 4 }}>
                    {CATEGORY_TABS.map(tab => (
                        <a key={tab.value} href={`/schemes${tab.value ? '?category=' + tab.value : ''}`}
                            style={{
                                padding: '8px 18px', borderRadius: 999, whiteSpace: 'nowrap',
                                fontSize: 14, fontWeight: 500, textDecoration: 'none',
                                flexShrink: 0,
                                ...(category === tab.value
                                    ? { background: '#111928', color: '#fff' }
                                    : { border: '1.5px solid var(--color-border)', color: '#6B7280', background: 'transparent' }
                                ),
                            }}>
                            {tab.label}
                        </a>
                    ))}
                </div>

                {/* Two column layout */}
                <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 65fr) minmax(0, 32fr)', gap: 24, alignItems: 'start' }}
                    className="detail-grid">

                    {/* Main: cards grid */}
                    <div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 32 }}>
                            {paged.map(s => <DirectorySchemeCard key={s.slug} scheme={s} />)}
                        </div>

                        {/* Pagination */}
                        {totalPages > 1 && (
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                                {page > 1 && (
                                    <a href={`/schemes?page=${page - 1}${category ? '&category=' + category : ''}`}
                                        style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '6px 12px', color: 'var(--color-muted)', textDecoration: 'none', fontSize: 14 }}>
                                        ← Prev
                                    </a>
                                )}
                                {Array.from({ length: totalPages }, (_, i) => i + 1).map(p => (
                                    <a key={p} href={`/schemes?page=${p}${category ? '&category=' + category : ''}`}
                                        style={{
                                            width: 36, height: 36, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center',
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
                                    <a href={`/schemes?page=${page + 1}${category ? '&category=' + category : ''}`}
                                        style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '6px 12px', color: 'var(--color-muted)', textDecoration: 'none', fontSize: 14 }}>
                                        Next →
                                    </a>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Sidebar */}
                    <div>
                        {/* AI Sahayak Card */}
                        <div style={{ border: '1.5px solid #BFDBFE', borderRadius: 14, padding: 20 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                                <div className="pulse-dot" />
                                <div style={{
                                    width: 48, height: 48, background: '#EFF6FF', borderRadius: '50%',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                }}>
                                    <Bot size={24} color="#1A56DB" />
                                </div>
                            </div>
                            <div style={{ fontWeight: 600, fontSize: 17, color: 'var(--color-text)', marginBottom: 6 }}>AI Sahayak</div>
                            <p style={{ fontSize: 13, color: 'var(--color-muted)', margin: '0 0 16px', lineHeight: 1.5 }}>
                                Your intelligent assistant is online and ready to guide you to the perfect scheme.
                            </p>
                            <a href="/eligibility" style={{
                                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                                background: '#1A56DB', color: '#fff', borderRadius: 10, padding: '12px',
                                textDecoration: 'none', fontWeight: 500, fontSize: 14, width: '100%',
                                boxSizing: 'border-box',
                            }}>
                                💬 Start Chat
                            </a>
                        </div>

                        {/* Quick Help */}
                        <div style={{ border: '1.5px solid var(--color-border)', borderRadius: 14, padding: 20, marginTop: 16, background: 'var(--color-surface, #fff)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                                <Lightbulb size={18} color="#F59E0B" />
                                <span style={{ fontWeight: 600, fontSize: 15, color: 'var(--color-text)' }}>Quick Help</span>
                            </div>
                            {[
                                { Icon: FileText, title: 'Application Process', sub: 'Step-by-step guide to apply' },
                                { Icon: ClipboardList, title: 'Track Application', sub: 'Check your current status' },
                                { Icon: FolderOpen, title: 'Document Library', sub: 'Required paperwork checklist' },
                            ].map(({ Icon, title, sub }, i) => (
                                <div key={title} style={{
                                    display: 'flex', alignItems: 'center', gap: 12, padding: '12px 0',
                                    borderBottom: i < 2 ? '1px solid var(--color-border)' : 'none',
                                    cursor: 'pointer',
                                }}>
                                    <div style={{ width: 36, height: 36, background: '#F3F4F6', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                                        <Icon size={18} color="#6B7280" />
                                    </div>
                                    <div>
                                        <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--color-text)' }}>{title}</div>
                                        <div style={{ fontSize: 11, color: 'var(--color-muted)' }}>{sub}</div>
                                    </div>
                                </div>
                            ))}
                            <a href="/support" style={{ display: 'block', marginTop: 12, color: '#1A56DB', fontSize: 13, fontWeight: 500, textDecoration: 'none' }}>
                                Browse Support Center →
                            </a>
                        </div>

                        {/* Govt Portals */}
                        <div style={{ border: '1.5px solid var(--color-border)', borderRadius: 14, padding: 20, marginTop: 16, background: 'var(--color-surface, #fff)' }}>
                            <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-muted)', marginBottom: 12 }}>
                                GOVT. PORTALS
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                                {[
                                    { label: 'Egiye Bangla', href: 'https://egieyebangla.gov.in' },
                                    { label: 'Duare Sarkar', href: 'https://wbduaresarkar.gov.in' },
                                ].map(({ label, href }) => (
                                    <a key={label} href={href} target="_blank" rel="noopener noreferrer" style={{
                                        border: '1.5px solid var(--color-border)', borderRadius: 10, padding: '12px 8px',
                                        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
                                        fontSize: 12, textDecoration: 'none', color: 'var(--color-text)', textAlign: 'center',
                                        transition: 'background 0.15s',
                                    }}>
                                        <ExternalLink size={16} color="#1A56DB" />
                                        {label}
                                    </a>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
