'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import ScriptCard from './ScriptCard'

interface Props {
    type?: 'warning' | 'fatal'
    code?: string
    message: string
    messageBn?: string
    action?: string
    actionBn?: string
    scriptBn?: string
    scriptEn?: string
    audioUrl?: string
}

export default function IssueCard({ type = 'warning', code, message, messageBn, action, actionBn, scriptBn, scriptEn, audioUrl }: Props) {
    const [expanded, setExpanded] = useState(false)

    const isFatal = type === 'fatal'

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className={`relative rounded-xl overflow-hidden bg-slate-800/60 border border-slate-700/50 backdrop-blur-sm ${isFatal ? 'border-l-4 border-l-red-500' : 'border-l-4 border-l-amber-500'
                }`}
        >
            <div className="p-4">
                <div className="flex items-start gap-3">
                    <div className={`flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center text-lg ${isFatal ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'
                        }`}>
                        {isFatal ? '⚠️' : '⚡'}
                    </div>

                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${isFatal ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'
                                }`}>
                                {isFatal ? 'CRITICAL' : 'WARNING'}
                            </span>
                            {code && <span className="text-xs text-slate-500 font-mono">{code}</span>}
                        </div>

                        <p className="text-white font-semibold mt-1 text-sm leading-tight">{message}</p>
                        {messageBn && (
                            <p className="text-slate-400 text-sm mt-0.5 font-normal" style={{ fontFamily: "'Noto Sans Bengali', sans-serif" }}>
                                {messageBn}
                            </p>
                        )}

                        {action && (
                            <div className="mt-2 text-xs text-slate-300 bg-slate-700/40 rounded-lg px-3 py-2">
                                <span className="text-slate-500 font-medium">Action: </span>{action}
                                {actionBn && (
                                    <div className="text-slate-400 mt-0.5" style={{ fontFamily: "'Noto Sans Bengali', sans-serif" }}>
                                        {actionBn}
                                    </div>
                                )}
                            </div>
                        )}

                        {scriptBn && (
                            <button
                                onClick={() => setExpanded(!expanded)}
                                className={`mt-3 text-xs px-3 py-1.5 rounded-lg font-semibold transition-all duration-200 flex items-center gap-1.5 ${isFatal
                                    ? 'bg-red-500/20 text-red-300 hover:bg-red-500/30'
                                    : 'bg-amber-500/20 text-amber-300 hover:bg-amber-500/30'
                                    }`}
                            >
                                <span>💬</span>
                                {expanded ? 'Hide Script' : 'What to Say at Office'}
                            </button>
                        )}
                    </div>
                </div>

                <AnimatePresence>
                    {expanded && scriptBn && (
                        <motion.div
                            key="script"
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.25 }}
                            className="overflow-hidden"
                        >
                            <div className="mt-3 pt-3 border-t border-slate-700/50">
                                <ScriptCard bengaliText={scriptBn} englishText={scriptEn} audioUrl={audioUrl} />
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </motion.div>
    )
}
