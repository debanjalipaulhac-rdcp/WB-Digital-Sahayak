'use client'

import { motion } from 'framer-motion'

export default function RoadmapStep({ step, action, actionBn, location, done = false, isLast = false, delay = 0 }) {
    return (
        <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay, duration: 0.4 }}
            className="flex gap-4"
        >
            {/* Left: step number + vertical line */}
            <div className="flex flex-col items-center">
                <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0 border-2 transition-all ${done
                        ? 'bg-green-500/20 border-green-500 text-green-400'
                        : 'bg-blue-500/20 border-blue-500 text-blue-400'
                    }`}>
                    {done ? '✓' : step}
                </div>
                {!isLast && (
                    <div className={`w-0.5 flex-1 min-h-8 mt-1 ${done ? 'bg-green-500/30' : 'bg-slate-700/60'}`} />
                )}
            </div>

            {/* Right: content */}
            <div className={`pb-6 flex-1 ${isLast ? 'pb-0' : ''}`}>
                <div className={`p-3 rounded-xl border transition-all ${done
                        ? 'bg-green-500/5 border-green-500/20'
                        : 'bg-slate-800/60 border-slate-700/40'
                    }`}>
                    <p className="text-white font-semibold text-sm leading-tight">{action}</p>
                    {actionBn && (
                        <p
                            className="text-slate-400 text-sm mt-0.5"
                            style={{ fontFamily: "'Noto Sans Bengali', sans-serif" }}
                        >
                            {actionBn}
                        </p>
                    )}
                    {location && (
                        <div className="mt-2 flex items-center gap-1.5 text-slate-400 text-xs">
                            <span>📍</span>
                            <span>{location}</span>
                        </div>
                    )}
                </div>
            </div>
        </motion.div>
    )
}
