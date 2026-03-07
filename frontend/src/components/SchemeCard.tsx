import { Bike, GraduationCap, Award, ExternalLink, LucideIcon } from 'lucide-react'
import type { Scheme } from '@/types'
import Link from 'next/link'

const ICON_MAP: Record<string, LucideIcon> = { Bike, GraduationCap, Award }

const TAG_STYLES: Record<string, string> = {
    SCHEME: 'bg-blue-50 text-blue-700',
    SCHOLARSHIP: 'bg-indigo-50 text-indigo-700',
    'MERIT-CUM-MEANS': 'bg-green-50 text-green-700',
    MARRIAGE: 'bg-rose-50 text-rose-700',
    PENSION: 'bg-purple-50 text-purple-700',
    HEALTH: 'bg-teal-50 text-teal-700',
    YOUTH: 'bg-amber-50 text-amber-700',
    WOMEN: 'bg-pink-50 text-pink-700',
    GIRL_CHILD: 'bg-fuchsia-50 text-fuchsia-700',
    AGRICULTURE: 'bg-lime-50 text-lime-700',
}

interface SchemeCardProps {
    scheme: Scheme
}

export default function SchemeCard({ scheme }: SchemeCardProps) {
    const id = scheme.scheme_id || ''
    const label = scheme.name || scheme.scheme_name || ''
    const tag = scheme.tag || ''
    const icon = scheme.icon || ''
    const dept = scheme.dept || scheme.department || ''
    const desc = scheme.description || ''

    const IconComponent = ICON_MAP[icon] || Award
    const tagCls = TAG_STYLES[tag] || TAG_STYLES['SCHEME']

    return (
        <Link href={`/schemes/${id}`} className="bg-accent rounded-xl p-4 hover:-translate-0.5 transform-3d translate-0 transition-all">
            {/* Top row: icon + tag */}
            <div className="flex items-start justify-between">
                <div className="w-12 h-12 bg-muted rounded-md flex items-center justify-center shrink-0">
                    <IconComponent size={24} className="text-blue-600" />
                </div>
                {tag && (
                    <span className={`text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded ${tagCls}`}>
                        {tag.replace('_', ' ')}
                    </span>
                )}
            </div>

            {/* Scheme name */}
            <div className="font-semibold text-[17px]  mt-3 leading-snug">
                {label}
            </div>

            {/* Benefit pill */}
            {scheme.benefit_display && (
                <div className="mt-1.5 text-xs font-semibold text-blue-700 bg-muted rounded px-2 py-0.5 w-fit">
                    {scheme.benefit_display}
                </div>
            )}

            {/* Description */}
            <p className=" text-sm text-muted-foreground mt-2 leading-relaxed grow line-clamp-3">
                {desc}
            </p>

            {/* Footer */}
            <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-100">
                <span className="text-[11px] text-primary-foreground leading-tight">{dept}</span>
                <ExternalLink size={14} className="text-primary/60 group-hover:text-blue-700 transition-colors" />
            </div>
        </Link>
    )
}
