import { cookies } from 'next/headers'
import { Sparkles, ArrowRight } from 'lucide-react'
import { getSchemes } from '@/lib/api'
import translations from '@/lib/i18n'
import SchemeCard from '@/components/SchemeCard'
import SearchBar, { EligibilityTrigger } from '@/components/SearchBar'

export const metadata = {
    title: 'WB Digital Sahayak — Find Your Welfare Benefits',
    description: 'West Bengal government scheme portal for rural citizens. Find scholarships, bicycle schemes, and welfare benefits.',
}

export default async function HomePage() {
    const cookieStore = await cookies()
    const rawLang = cookieStore.get('wb_lang')?.value
    const lang = ['en', 'bn', 'hi'].includes(rawLang) ? rawLang : 'en'
    const tx = translations[lang] || translations['en']

    const data = await getSchemes()
    const schemes = data?.schemes || []

    return (
        <div style={{ background: 'var(--color-bg)', minHeight: '100vh' }}>

            {/* ── HERO SECTION ── */}
            <section style={{
                background: 'linear-gradient(135deg, #1A56DB 0%, #1E429F 100%)',
                padding: 'clamp(60px, 8vw, 80px) 20px 60px',
                textAlign: 'center',
            }}>
                <div style={{ maxWidth: 700, margin: '0 auto' }}>

                    {/* Pill badge */}
                    <div className="animate-fade-up" style={{
                        display: 'inline-block',
                        border: '1px solid rgba(255,255,255,0.5)',
                        borderRadius: 999, padding: '5px 16px', marginBottom: 20,
                    }}>
                        <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#fff' }}>
                            {tx.hero_badge}
                        </span>
                    </div>

                    {/* H1 */}
                    <h1 className="animate-fade-up delay-1" style={{
                        fontSize: 'clamp(2rem, 5vw, 3rem)', fontWeight: 700, color: '#fff',
                        lineHeight: 1.2, margin: '0 0 16px',
                    }}>
                        {tx.hero_title}
                    </h1>

                    {/* Bengali subtitle */}
                    <p className="bn-text animate-fade-up delay-1" style={{ fontSize: 16, color: 'rgba(255,255,255,0.85)', margin: '0 0 6px' }}>
                        {tx.hero_subtitle_bn}
                    </p>
                    <p className="animate-fade-up delay-2" style={{ fontSize: 14, color: 'rgba(255,255,255,0.75)', margin: '0 0 32px' }}>
                        {tx.hero_subtitle}
                    </p>

                    {/* CLIENT: SearchBar with VoiceModal + CheckEligibilityModal wired */}
                    <SearchBar showEligibilityTrigger />

                    {/* Quick chips */}
                    <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
                        {['Taposili Bandhu', 'Lakshmir Bhandar', 'Kanyashree'].map((chip, i) => (
                            <a key={chip} href={`/search?q=${encodeURIComponent(chip)}`}
                                className={`hero-chip animate-fade-up delay-${i + 1}`}>
                                {chip}
                            </a>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── RECOMMENDED BANNER ── */}
            <section style={{ padding: '28px 20px 0', maxWidth: 1100, margin: '0 auto' }}>
                <div style={{
                    background: 'var(--color-surface, #fff)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 16, padding: '24px 28px',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    gap: 20, flexWrap: 'wrap',
                }}>
                    <div style={{ flex: 1, minWidth: 220 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                            <Sparkles size={14} color="#1A56DB" />
                            <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#1A56DB' }}>
                                {tx.recommended_label}
                            </span>
                        </div>
                        <h2 style={{ fontSize: 'clamp(16px, 3vw, 20px)', fontWeight: 600, color: 'var(--color-text)', margin: '0 0 6px', lineHeight: 1.3 }}>
                            {tx.recommended_title}
                        </h2>
                        <p style={{ fontSize: 13, color: 'var(--color-muted)', margin: 0 }}>
                            {tx.recommended_sub}
                        </p>
                    </div>
                    {/* CLIENT: opens eligibility modal */}
                    <EligibilityTrigger />
                </div>
            </section>

            {/* ── SCHEME CATEGORIES ── */}
            <section style={{ padding: '40px 20px 20px', maxWidth: 1100, margin: '0 auto' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
                    <h2 style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-text)', margin: 0, borderLeft: '4px solid var(--color-primary)', paddingLeft: 12, lineHeight: 1.3 }}>
                        Education &amp; Student Support
                    </h2>
                    <a href="/schemes" style={{ fontSize: 13, color: '#1A56DB', textDecoration: 'none', fontWeight: 500, whiteSpace: 'nowrap' }}>
                        {tx.view_all} →
                    </a>
                </div>

                <div className="scheme-cards-scroll">
                    {schemes.map((scheme) => (
                        <SchemeCard key={scheme.slug} scheme={scheme} />
                    ))}
                </div>
            </section>

            {/* ── STATS BAR ── */}
            <section style={{
                background: 'var(--color-surface, #fff)',
                borderTop: '1px solid var(--color-border)',
                borderBottom: '1px solid var(--color-border)',
                padding: '40px 20px', margin: '40px 0',
            }}>
                <div style={{ maxWidth: 900, margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)' }}>
                    {(tx.stats || ['50+', '2M+', '100%', '24/7']).map((stat, i) => (
                        <div key={i} className="animate-count" style={{
                            textAlign: 'center', padding: '0 20px',
                            borderRight: i < 3 ? '1px solid var(--color-border)' : 'none',
                            animationDelay: `${i * 0.1}s`,
                        }}>
                            <div style={{ fontSize: 'clamp(24px, 4vw, 32px)', fontWeight: 700, color: 'var(--color-primary)' }}>
                                {stat}
                            </div>
                            <div style={{ fontSize: 12, color: 'var(--color-muted)', marginTop: 4 }}>
                                {(tx.stat_labels || ['Active Schemes', 'Beneficiaries', 'Digital Process', 'Support Access'])[i]}
                            </div>
                        </div>
                    ))}
                </div>
            </section>

        </div>
    )
}
