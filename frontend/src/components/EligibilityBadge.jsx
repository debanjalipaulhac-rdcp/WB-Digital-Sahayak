import { Check } from 'lucide-react'

export default function EligibilityBadge({ label, sub }) {
    return (
        <div style={{
            background: '#F0FDF4',
            border: '1px solid #BBF7D0',
            borderRadius: '10px',
            padding: '12px 14px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '10px',
        }}>
            <div style={{
                width: 22,
                height: 22,
                background: '#057A55',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                marginTop: '1px',
            }}>
                <Check size={13} color="white" strokeWidth={2.5} />
            </div>
            <div>
                <div style={{ fontSize: '13px', fontWeight: 500, color: 'var(--color-text)' }}>
                    {label}
                </div>
                {sub && (
                    <div style={{ fontSize: '11px', color: 'var(--color-muted)', marginTop: '2px' }}>
                        {sub}
                    </div>
                )}
            </div>
        </div>
    )
}
