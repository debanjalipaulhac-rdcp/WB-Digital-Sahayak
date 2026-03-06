import { Bike, GraduationCap, Award, ExternalLink } from 'lucide-react'

const ICON_MAP = {
    Bike: Bike,
    GraduationCap: GraduationCap,
    Award: Award,
}

const TAG_COLORS = {
    'SCHEME': { bg: '#EBF5FB', text: '#1A56DB' },
    'SCHOLARSHIP': { bg: '#EFF6FF', text: '#2563EB' },
    'MERIT-CUM-MEANS': { bg: '#F0FDF4', text: '#057A55' },
}

export default function SchemeCard({ scheme }) {
    const { slug, name, nameTag, icon, dept, desc } = scheme
    const IconComponent = ICON_MAP[icon] || Award
    const tagColor = TAG_COLORS[nameTag] || TAG_COLORS['SCHEME']

    return (
        <a href={`/scheme/${slug}`} className="scheme-card-link">
            {/* Top row: icon + tag */}
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                <div style={{
                    width: 48, height: 48,
                    background: '#EBF5FB',
                    borderRadius: '12px',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                    <IconComponent size={24} color="#1A56DB" />
                </div>
                <span style={{
                    fontSize: '10px',
                    fontWeight: 600,
                    letterSpacing: '0.05em',
                    textTransform: 'uppercase',
                    background: tagColor.bg,
                    color: tagColor.text,
                    padding: '2px 8px',
                    borderRadius: '4px',
                }}>
                    {nameTag}
                </span>
            </div>

            {/* Name */}
            <div style={{
                fontWeight: 600,
                fontSize: '17px',
                color: 'var(--color-text)',
                marginTop: '12px',
            }}>
                {name}
            </div>

            {/* Description */}
            <p className="line-clamp-3" style={{
                fontSize: '13px',
                color: 'var(--color-muted)',
                marginTop: '6px',
                lineHeight: 1.55,
                flexGrow: 1,
            }}>
                {desc}
            </p>

            {/* Bottom row: dept + external link */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginTop: '16px',
                paddingTop: '12px',
                borderTop: '1px solid var(--color-border)',
            }}>
                <span style={{ fontSize: '11px', color: '#9CA3AF' }}>{dept}</span>
                <ExternalLink size={14} color="#1A56DB" />
            </div>
        </a>
    )
}
