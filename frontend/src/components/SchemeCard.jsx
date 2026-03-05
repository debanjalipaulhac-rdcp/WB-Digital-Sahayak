'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'

export default function SchemeCard({ schemeName, schemeNameBn, benefit, category, categoryBn, applyAt = [], applyOnline, delay = 0 }) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay, duration: 0.4 }}
            className="bg-slate-800/60 border border-slate-700/40 rounded-xl p-4 hover:border-blue-500/40 transition-all duration-300 backdrop-blur-sm group"
        >
            {/* Category tag */}
            {category && (
                <div className="mb-3">
                    <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-blue-500/15 text-blue-400 border border-blue-500/25">
                        {category}
                        {categoryBn && <span className="ml-1 opacity-80" style={{ fontFamily: "'Noto Sans Bengali', sans-serif" }}>| {categoryBn}</span>}
                    </span>
                </div>
            )}

            {/* Scheme name */}
            <h3 className="text-white font-bold text-base leading-tight group-hover:text-blue-300 transition-colors">
                {schemeName}
            </h3>
            {schemeNameBn && (
                <p className="text-slate-400 text-sm mt-0.5" style={{ fontFamily: "'Noto Sans Bengali', sans-serif" }}>
                    {schemeNameBn}
                </p>
            )}

            {/* Benefit callout */}
            {benefit && (
                <div className="mt-3 bg-green-500/10 border border-green-500/20 rounded-lg px-3 py-2 flex items-center gap-2">
                    <span className="text-green-400 text-lg">💰</span>
                    <span className="text-green-300 font-bold text-base">{benefit}</span>
                </div>
            )}

            {/* Where to apply */}
            {applyAt.length > 0 && (
                <div className="mt-3">
                    <p className="text-slate-500 text-xs font-medium uppercase tracking-wider mb-1.5">Apply At</p>
                    <div className="space-y-1">
                        {applyAt.map((loc, i) => (
                            <div key={i} className="flex items-center gap-1.5 text-slate-300 text-xs">
                                <span className="text-slate-500">📍</span>
                                {loc}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Online apply link */}
            {applyOnline && (
                <a
                    href={applyOnline}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-3 flex items-center gap-2 text-blue-400 text-sm font-semibold hover:text-blue-300 transition-colors group/link"
                >
                    <span className="w-5 h-5 rounded-full bg-blue-500/20 flex items-center justify-center text-xs">↗</span>
                    Apply Online
                    <span className="ml-auto opacity-0 group-hover/link:opacity-100 transition-opacity">→</span>
                </a>
            )}
        </motion.div>
    )
}
