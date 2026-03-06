import { AlertTriangle, ArrowRight, Volume2 } from 'lucide-react'

export default function MismatchBanner({ mismatch, t }) {
    if (!mismatch || !mismatch.exists) return null

    return (
        <div
            className="animate-shake"
            style={{
                background: 'var(--color-red-bg)',
                borderLeft: '6px solid var(--color-red)',
                borderRadius: '12px',
                overflow: 'hidden',
                display: 'flex',
                border: '1px solid #FECACA',
                borderLeftWidth: '6px',
                borderLeftColor: 'var(--color-red)',
            }}
        >
            {/* Red left column */}
            <div style={{
                width: 60, flexShrink: 0,
                background: 'var(--color-red)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
                <AlertTriangle size={24} color="white" />
            </div>

            {/* Content */}
            <div style={{ padding: '20px', flex: 1 }}>
                <div style={{
                    display: 'flex', alignItems: 'center',
                    justifyContent: 'space-between', gap: '8px',
                }}>
                    <div style={{ fontWeight: 600, fontSize: '15px', color: 'var(--color-red)' }}>
                        {t('mismatch_title')}
                    </div>
                    <button className="tts-btn" aria-label="Read aloud mismatch notice">
                        <Volume2 size={16} />
                    </button>
                </div>

                <p style={{ fontSize: '13px', color: 'var(--color-muted)', marginTop: '4px', lineHeight: 1.5 }}>
                    {t('mismatch_sub')}
                </p>

                {/* Comparison row */}
                <div style={{
                    background: '#fff', borderRadius: '8px', padding: '12px 16px',
                    marginTop: '12px', display: 'flex', alignItems: 'center',
                    gap: '12px', flexWrap: 'wrap',
                }}>
                    <div>
                        <div style={{ fontSize: '10px', color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            {t('aadhaar_name')}
                        </div>
                        <div style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '13px', marginTop: '2px', color: 'var(--color-text)' }}>
                            {mismatch.aadhaar_name}
                        </div>
                    </div>

                    <ArrowRight size={20} color="#1A56DB" style={{ flexShrink: 0 }} />

                    <div>
                        <div style={{ fontSize: '10px', color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            {t('bank_name')}
                        </div>
                        <div style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '13px', marginTop: '2px', color: 'var(--color-text)' }}>
                            {mismatch.bank_name}
                        </div>
                    </div>

                    <a href="#fix" style={{
                        marginLeft: 'auto',
                        color: '#1A56DB',
                        textDecoration: 'underline',
                        fontSize: '13px',
                        fontWeight: 500,
                        whiteSpace: 'nowrap',
                    }}>
                        {t('fix_this')}
                    </a>
                </div>
            </div>
        </div>
    )
}
