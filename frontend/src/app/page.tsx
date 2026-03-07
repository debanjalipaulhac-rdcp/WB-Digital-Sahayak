// SERVER COMPONENT — SSR, no "use client"
import { cookies } from 'next/headers'
import { Sparkles } from 'lucide-react'
import translations from '@/lib/i18n'
import SchemeCard from '@/components/SchemeCard'
import SearchBar, { EligibilityTrigger } from '@/components/SearchBar'
import { getSchemes } from '@/lib/server/api'
import Link from 'next/link'
import { QuickEligibilityFilter } from '@/components/QuickEligibilityFilter'

export const metadata = {
    title: 'WB Digital Sahayak — Find Your Welfare Benefits',
    description: 'West Bengal government scheme portal for rural citizens. Find scholarships, bicycle schemes, and welfare benefits.',
}

export default async function HomePage() {
    const cookieStore = await cookies()
    const rawLang = cookieStore.get('wb_lang')?.value
    const lang = ['en', 'bn', 'hi'].includes(rawLang ?? '') ? rawLang! : 'en'
    const tx = translations[lang] || translations['en']

    // Fetch schemes with proper error handling
    const data = await getSchemes({ page_size: 8, sort: 'relevance' })
    const schemes = data?.schemes || []

    const stats = (tx.stats as string[]) || ['50+', '2M+', '100%', '24/7']
    const statLabels = (tx.stat_labels as string[]) || ['Active Schemes', 'Beneficiaries', 'Digital Process', 'Support Access']

    return (
        <div className="min-h-screen bg-background">

            {/* ── HERO ── */}
            <section className="bg-linear-180 from-primary/90 to-primary py-16 px-5 text-center">
                <div className="max-w-2xl mx-auto">

                    {/* Pill badge */}
                    <div className="animate-fade-up inline-block border border-accent-foreground rounded-full px-4 py-1 mb-5">
                        <span className="text-xs font-semibold tracking-widest uppercase text-white">
                            {tx.hero_badge}
                        </span>
                    </div>

                    {/* H1 */}
                    <h1 className="animate-fade-up delay-1 text-3xl sm:text-4xl lg:text-5xl font-bold text-white leading-tight mb-4">
                        {tx.hero_title}
                    </h1>

                    {/* Subtitles */}
                    <p className="bn-text animate-fade-up delay-1 text-base text-white/85 mb-1">
                        {tx.hero_subtitle_bn}
                    </p>
                    <p className="animate-fade-up delay-2 text-sm text-white/75 mb-8">
                        {tx.hero_subtitle}
                    </p>
                    <div className="m-auto inline-block">

                        {/* SearchBar */}
                        <SearchBar showEligibilityTrigger />
                    </div>

                    {/* Quick chips */}
                    <div className="flex gap-2.5 justify-center items-center flex-wrap mt-4 ">
                        {['Taposili Bandhu', 'Lakshmir Bhandar', 'Kanyashree'].map((chip, i) => (
                            <Link
                                key={chip}
                                href={`/search?q=${encodeURIComponent(chip)}`}
                                className={`opactity-0 rounded-full border border-gray-300 animate-fade-up delay-${i + 1} text-white`}
                            >
                                <span className="text-xs tracking-wide uppercase p-4">
                                    {chip}
                                </span>
                            </Link>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── FIND MY SCHEMES WIDGET ── */}
            <section className="pt-7 px-5 max-w-6xl mx-auto">
                <QuickEligibilityFilter />
            </section>

            {/* ── SCHEME CATEGORIES ── */}
            <section className="pt-10 pb-5 px-5 max-w-6xl mx-auto">
                <div className="flex items-center justify-between mb-5">
                    <h2 className="text-xl font-bold border-l-4 border-blue-600 pl-3 leading-snug">
                        Education &amp; Student Support
                    </h2>
                    <a href="/schemes" className="text-sm text-blue-600 font-medium whitespace-nowrap hover:underline">
                        {tx.view_all} →
                    </a>
                </div>

                <div className="scheme-cards-scroll">
                    {schemes.map((scheme) => (
                        <SchemeCard key={scheme.scheme_id} scheme={scheme} />
                    ))}
                </div>
            </section>

            {/* ── STATS BAR ── */}
            <section className="py-10 px-5">
                <div className="max-w-2xl mx-auto grid gap-5 grid-cols-4">
                    {stats.map((stat, i) => (
                        <div
                            key={i}
                            className={`animate-count bg-secondary rounded-lg text-center p-5 ${i < 3 ? 'border-r' : ''}`}
                            style={{ animationDelay: `${i * 0.1}s` }}
                        >
                            <div className="text-3xl sm:text-4xl font-bold text-blue-600 text-center">{stat}</div>
                            <div className="text-xs text-accent-foreground mt-1">{statLabels[i]}</div>
                        </div>
                    ))}
                </div>
            </section>
            <div className="h-8"/>
        </div>
    )
}
