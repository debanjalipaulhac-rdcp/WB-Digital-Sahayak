import { cookies } from 'next/headers'
import { Sparkles } from 'lucide-react'
import translations from '@/lib/i18n'
import SchemeCard from '@/components/SchemeCard'
import SearchBar, { EligibilityTrigger } from '@/components/SearchBar'
import { getSchemes } from '@/lib/server/api'

export const metadata = {
    title: 'WB Digital Sahayak — Find Your Welfare Benefits',
    description: 'West Bengal government scheme portal for rural citizens. Find scholarships, bicycle schemes, and welfare benefits.',
}

export default async function HomePage() {
    const cookieStore = await cookies()
    const rawLang = cookieStore.get('wb_lang')?.value
    const lang = ['en', 'bn', 'hi'].includes(rawLang ?? '') ? rawLang! : 'en'
    const tx = translations[lang] || translations['en']

    const data = await getSchemes()
    const schemes = data?.schemes || []

    const stats = (tx.stats as string[]) || ['50+', '2M+', '100%', '24/7']
    const statLabels = (tx.stat_labels as string[]) || ['Active Schemes', 'Beneficiaries', 'Digital Process', 'Support Access']

    return (
        <div className="min-h-screen bg-gray-50">

            {/* ── HERO ── */}
            <section className="bg-gradient-to-br from-blue-600 to-blue-800 py-16 px-5 text-center">
                <div className="max-w-2xl mx-auto">

                    {/* Pill badge */}
                    <div className="animate-fade-up inline-block border border-white/50 rounded-full px-4 py-1 mb-5">
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

                    {/* SearchBar */}
                    <SearchBar showEligibilityTrigger />

                    {/* Quick chips */}
                    <div className="flex gap-2.5 justify-center flex-wrap mt-4">
                        {['Taposili Bandhu', 'Lakshmir Bhandar', 'Kanyashree'].map((chip, i) => (
                            <a
                                key={chip}
                                href={`/search?q=${encodeURIComponent(chip)}`}
                                className={`hero-chip animate-fade-up delay-${i + 1}`}
                            >
                                {chip}
                            </a>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── RECOMMENDED BANNER ── */}
            <section className="pt-7 px-5 max-w-6xl mx-auto">
                <div className="bg-white border border-gray-200 rounded-2xl p-6 flex items-center justify-between flex-wrap gap-5">
                    <div className="flex-1 min-w-56">
                        <div className="flex items-center gap-1.5 mb-2">
                            <Sparkles size={14} className="text-blue-600" />
                            <span className="text-xs font-semibold tracking-wide uppercase text-blue-600">
                                {tx.recommended_label}
                            </span>
                        </div>
                        <h2 className="text-lg sm:text-xl font-semibold text-gray-900 mb-1.5 leading-snug">
                            {tx.recommended_title}
                        </h2>
                        <p className="text-sm text-gray-500">
                            {tx.recommended_sub}
                        </p>
                    </div>
                    <EligibilityTrigger />
                </div>
            </section>

            {/* ── SCHEME CATEGORIES ── */}
            <section className="pt-10 pb-5 px-5 max-w-6xl mx-auto">
                <div className="flex items-center justify-between mb-5">
                    <h2 className="text-xl font-bold text-gray-900 border-l-4 border-blue-600 pl-3 leading-snug">
                        Education &amp; Student Support
                    </h2>
                    <a href="/schemes" className="text-sm text-blue-600 font-medium whitespace-nowrap hover:underline">
                        {tx.view_all} →
                    </a>
                </div>

                <div className="scheme-cards-scroll">
                    {schemes.map((scheme) => (
                        <SchemeCard key={scheme.scheme_id || scheme.slug} scheme={scheme} />
                    ))}
                </div>
            </section>

            {/* ── STATS BAR ── */}
            <section className="bg-white border-y border-gray-200 py-10 px-5 my-10">
                <div className="max-w-4xl mx-auto grid grid-cols-4">
                    {stats.map((stat, i) => (
                        <div
                            key={i}
                            className={`animate-count text-center px-5 ${i < 3 ? 'border-r border-gray-200' : ''}`}
                            style={{ animationDelay: `${i * 0.1}s` }}
                        >
                            <div className="text-3xl sm:text-4xl font-bold text-blue-600">{stat}</div>
                            <div className="text-xs text-gray-500 mt-1">{statLabels[i]}</div>
                        </div>
                    ))}
                </div>
            </section>

        </div>
    )
}
