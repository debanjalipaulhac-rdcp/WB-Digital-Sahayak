import { FileText, GraduationCap, CreditCard, LucideIcon } from 'lucide-react'

const ICON_MAP: Record<string, LucideIcon> = {
    FileText,
    GraduationCap,
    CreditCard,
}

interface Doc {
    id: string
    label: string
    sub: string
    icon: string
}

interface Props {
    doc: Doc
    isLast?: boolean
}

export default function DocumentItem({ doc, isLast }: Props) {
    const IconComponent = ICON_MAP[doc.icon] || FileText

    return (
        <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            padding: '12px 0',
            borderBottom: isLast ? 'none' : '1px solid var(--color-border)',
        }}>
            {/* Checkbox */}
            <div style={{
                width: 20,
                height: 20,
                border: '1.5px solid #D1D5DB',
                borderRadius: '4px',
                flexShrink: 0,
                background: '#fff',
            }} aria-hidden="true" />

            {/* Text */}
            <div style={{ flex: 1 }}>
                <div style={{ fontSize: '13px', fontWeight: 500, color: 'var(--color-text)' }}>
                    {doc.label}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--color-muted)', marginTop: '2px' }}>
                    {doc.sub}
                </div>
            </div>

            {/* Icon */}
            <IconComponent size={18} color="#9CA3AF" />
        </div>
    )
}
