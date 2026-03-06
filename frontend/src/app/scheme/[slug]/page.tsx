import { cookies } from 'next/headers'
import { notFound } from 'next/navigation'
import {
    Volume2, CheckCircle2, DollarSign, FolderOpen,
    ArrowRight, Bike, GraduationCap, Info
} from 'lucide-react'
import { getScheme } from '@/lib/api'
import translations from '@/lib/i18n'
import type { Translations } from '@/lib/i18n'
import EligibilityBadge from '@/components/EligibilityBadge'
import MismatchBanner from '@/components/MismatchBanner'
import DocumentItem from '@/components/DocumentItem'

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
    const { slug } = await params
    const scheme = await getScheme(slug)
    if (!scheme) return { title: 'Scheme Not Found' }
    return {
        title: `${scheme.name} — WB Digital Sahayak`,
        description: scheme.description,
    }
}

export default async function SchemeDetailPage({ params }: { params: Promise<{ slug: string }> }) {
    const { slug } = await params
    const cookieStore = await cookies()
    const rawLang = cookieStore.get('wb_lang')?.value
    const lang = ['en', 'bn', 'hi'].includes(rawLang ?? '') ? rawLang! : 'en'
    const tx = translations[lang] || translations['en']

    const scheme = await getScheme(slug)
    if (!scheme) notFound()

    function t(key: string): string { return (tx[key as keyof typeof tx] as string) || key }

    return (
        <div style={{ background: 'var(--color-bg)', minHeight: '100vh', paddingBottom: '48px' }}>
            <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '24px 20px' }}>

                {/* ── SCHEME HEADER ── */}
                <div style={{
                    background: '#fff',
                    border: '1px solid var(--color-border)',
                    borderRadius: '16px',
                    padding: '28px',
                    display: 'flex',
                    alignItems: 'flex-start',
                    justifyContent: 'space-between',
                    gap: '16px',
                    flexWrap: 'wrap',
                    marginBottom: '24px',
                }}>
                    <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <h1 style={{
                                fontSize: 'clamp(24px, 5vw, 32px)',
                                fontWeight: 700,
                                color: 'var(--color-text)',
                                margin: 0,
                                lineHeight: 1.2,
                            }}>
                                {scheme.name}
                            </h1>
                            <button
                                className="tts-btn"
                                aria-label="Read aloud scheme name"
                                style={{ borderRadius: '50%', width: 36, height: 36, background: '#EBF5FB' }}
                            >
                                <Volume2 size={18} color="#1A56DB" />
                            </button>
                        </div>
                        <p style={{ fontSize: '13px', color: 'var(--color-muted)', margin: '6px 0 0' }}>
                            {scheme.dept}
                        </p>
                    </div>

                    {scheme.status === 'active' && (
                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            border: '1.5px solid var(--color-green)',
                            borderRadius: '999px',
                            padding: '7px 16px',
                            background: '#fff',
                            flexShrink: 0,
                        }}>
                            <CheckCircle2 size={16} color="var(--color-green)" />
                            <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--color-green)' }}>
                                {t('active_scheme')}
                            </span>
                        </div>
                    )}
                </div>

                {/* ── TWO-COLUMN LAYOUT ── */}
                <div className="detail-grid">

                    {/* LEFT COLUMN */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

                        {/* SCHEME BENEFITS */}
                        <div className="animate-slide-left" style={{
                            background: '#F0FDF4',
                            border: '1px solid #D1FAE5',
                            borderRadius: '16px',
                            padding: '24px',
                        }}>
                            <div style={{
                                display: 'flex', alignItems: 'center',
                                justifyContent: 'space-between', marginBottom: '12px',
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                    <DollarSign size={20} color="var(--color-green)" />
                                    <h2 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-green)', margin: 0 }}>
                                        {t('scheme_benefits')}
                                    </h2>
                                </div>
                                <button className="tts-btn" aria-label="Read aloud benefits">
                                    <Volume2 size={18} />
                                </button>
                            </div>

                            <p style={{ fontSize: '14px', color: '#374151', margin: '0 0 20px', lineHeight: 1.6 }}>
                                {scheme.description}
                            </p>

                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                                <div style={{
                                    background: '#fff', border: '1px solid #D1FAE5',
                                    borderRadius: '10px', padding: '12px 16px',
                                    display: 'flex', alignItems: 'center', gap: '12px',
                                }}>
                                    <div style={{
                                        width: 40, height: 40, background: '#FFF7ED',
                                        borderRadius: '10px', display: 'flex', alignItems: 'center',
                                        justifyContent: 'center', flexShrink: 0,
                                    }}>
                                        <Bike size={20} color="#F97316" />
                                    </div>
                                    <div>
                                        <div style={{ fontSize: '10px', color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>ASSET</div>
                                        <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text)', marginTop: '2px' }}>
                                            {scheme.asset || 'Free Bicycle'}
                                        </div>
                                    </div>
                                </div>

                                <div style={{
                                    background: '#fff', border: '1px solid #D1FAE5',
                                    borderRadius: '10px', padding: '12px 16px',
                                    display: 'flex', alignItems: 'center', gap: '12px',
                                }}>
                                    <div style={{
                                        width: 40, height: 40, background: '#F5F3FF',
                                        borderRadius: '10px', display: 'flex', alignItems: 'center',
                                        justifyContent: 'center', flexShrink: 0,
                                    }}>
                                        <GraduationCap size={20} color="#7C3AED" />
                                    </div>
                                    <div>
                                        <div style={{ fontSize: '10px', color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>IMPACT</div>
                                        <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text)', marginTop: '2px' }}>
                                            {scheme.impact || 'Reduce Dropouts'}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* ELIGIBILITY CRITERIA */}
                        <div style={{
                            background: '#fff', border: '1px solid var(--color-border)',
                            borderRadius: '16px', padding: '24px',
                        }}>
                            <div style={{
                                display: 'flex', alignItems: 'center',
                                justifyContent: 'space-between', marginBottom: '16px',
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                    <CheckCircle2 size={20} color="var(--color-primary)" />
                                    <h2 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-text)', margin: 0 }}>
                                        {t('eligibility_criteria')}
                                    </h2>
                                </div>
                                <button className="tts-btn" aria-label="Read aloud eligibility">
                                    <Volume2 size={18} />
                                </button>
                            </div>

                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                                {(scheme.eligibility || []).map((item, i) => (
                                    <EligibilityBadge key={i} label={item.label} sub={item.sub} />
                                ))}
                            </div>
                        </div>

                        {/* MISMATCH BANNER */}
                        {scheme.mismatch?.exists && (
                            <MismatchBanner mismatch={scheme.mismatch} t={t} />
                        )}
                    </div>

                    {/* RIGHT SIDEBAR */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

                        {/* REQUIRED DOCUMENTS */}
                        <div style={{
                            background: '#fff', border: '1px solid var(--color-border)',
                            borderRadius: '16px', padding: '20px',
                        }}>
                            <div style={{
                                display: 'flex', alignItems: 'center',
                                justifyContent: 'space-between', marginBottom: '4px',
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                    <FolderOpen size={20} color="#D97706" />
                                    <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-text)', margin: 0 }}>
                                        {t('required_docs')}
                                    </h2>
                                </div>
                                <button className="tts-btn" aria-label="Read aloud documents">
                                    <Volume2 size={16} />
                                </button>
                            </div>

                            {(scheme.documents || []).map((doc, i) => (
                                <DocumentItem
                                    key={doc.id}
                                    doc={doc}
                                    isLast={i === (scheme.documents?.length ?? 0) - 1}
                                />
                            ))}

                            <div style={{
                                background: '#EFF6FF', borderRadius: '8px',
                                padding: '10px 12px', marginTop: '12px',
                                display: 'flex', alignItems: 'flex-start', gap: '8px',
                            }}>
                                <Info size={14} color="#1A56DB" style={{ flexShrink: 0, marginTop: '1px' }} />
                                <p style={{ fontSize: '12px', color: '#1D4ED8', margin: 0, lineHeight: 1.5 }}>
                                    {t('doc_tip')}
                                </p>
                            </div>
                        </div>

                        {/* READY TO APPLY */}
                        <div style={{
                            background: '#fff', border: '1px solid var(--color-border)',
                            borderRadius: '16px', padding: '20px',
                        }}>
                            <h2 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--color-text)', margin: '0 0 8px' }}>
                                {t('ready_to_apply')}
                            </h2>
                            <p style={{ fontSize: '13px', color: 'var(--color-muted)', margin: '0 0 16px', lineHeight: 1.5 }}>
                                {t('ready_sub')}
                            </p>
                            <a href={`/check-eligibility/${scheme.slug}`} className="btn-apply">
                                {t('check_now')}
                                <ArrowRight size={18} />
                            </a>
                        </div>

                        {/* SCHEME IMAGE */}
                        <div style={{ borderRadius: '16px', overflow: 'hidden', position: 'relative', height: '180px' }}>
                            <img
                                src="https://picsum.photos/400/250?random=42"
                                alt="West Bengal students with bicycles"
                                style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                            />
                            <div style={{
                                position: 'absolute', inset: 0,
                                background: 'linear-gradient(to top, rgba(0,0,0,0.6) 0%, transparent 60%)',
                            }} />
                            <span style={{
                                position: 'absolute', bottom: '12px', left: '12px',
                                color: '#fff', fontWeight: 500, fontSize: '13px',
                                textShadow: '0 1px 3px rgba(0,0,0,0.5)',
                            }}>
                                West Bengal Students Empowered
                            </span>
                        </div>

                    </div>
                </div>
            </div>
        </div>
    )
}
