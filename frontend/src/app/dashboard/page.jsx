'use client'

import { Suspense } from 'react'
import DashboardContent from './DashboardContent'

export default function DashboardPage() {
    return (
        <Suspense
            fallback={
                <div className="min-h-screen bg-slate-950 flex items-center justify-center">
                    <div className="flex flex-col items-center gap-4">
                        <div className="w-16 h-16 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
                        <p className="text-slate-400 text-sm">Loading results...</p>
                    </div>
                </div>
            }
        >
            <DashboardContent />
        </Suspense>
    )
}
