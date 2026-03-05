'use client'

import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import Link from 'next/link'
import { useTranslation } from 'react-i18next'
import '../../i18n/config'
import TopBar from '../../components/TopBar'
import ScoreMeter from '../../components/ScoreMeter'
import IssueCard from '../../components/IssueCard'
import SchemeCard from '../../components/SchemeCard'
import RoadmapStep from '../../components/RoadmapStep'
import I18nProvider from '../../i18n/I18nProvider'

// ─── Mock data for Sulata's case ────────────────────────────────────────────
const MOCK_DATA = {
    score: 42,
    band: 'RED',
    scheme: 'lakshmir_bhandar',
    schemeName: 'Lakshmir Bhandar',
    schemeNameBn: 'লক্ষ্মীর ভান্ডার',
    issues: [
        {
            type: 'fatal',
            code: 'DOC_MISMATCH_001',
            message: 'Name mismatch between Aadhaar and Bank Account',
            messageBn: 'আধার কার্ড ও ব্যাঙ্ক অ্যাকাউন্টের নামে অমিল',
            action: 'Visit bank to update name matching Aadhaar exactly',
            actionBn: 'ব্যাঙ্কে গিয়ে আধার অনুযায়ী নাম সংশোধন করুন',
            scriptBn: 'আমার আধার কার্ডের নাম "সুলতা বেগম" কিন্তু ব্যাঙ্ক অ্যাকাউন্টে "সুলতা বেগুম" আছে। আমাকে নাম সংশোধন করতে হবে। দয়া করে সংশোধনী ফর্ম দিন।',
            scriptEn: 'My Aadhaar name is "Sulata Begum" but my bank account shows "Sulata Begum". I need to fix this name mismatch. Please give me the correction form.',
        },
        {
            type: 'fatal',
            code: 'INCOME_CERT_MISSING',
            message: 'Income certificate not uploaded',
            messageBn: 'আয়ের শংসাপত্র আপলোড করা হয়নি',
            action: 'Get income certificate from your local BDO office',
            actionBn: 'স্থানীয় BDO অফিস থেকে আয়ের শংসাপত্র সংগ্রহ করুন',
            scriptBn: 'আমার লক্ষ্মীর ভান্ডার প্রকল্পের আবেদনের জন্য আয়ের শংসাপত্র দরকার। আমার পরিবারের বার্ষিক আয় ১,৫০,০০০ টাকার কম। দয়া করে শংসাপত্র দিন।',
            scriptEn: 'I need an income certificate for my Lakshmir Bhandar application. My family annual income is less than 1,50,000 rupees. Please provide the certificate.',
        },
        {
            type: 'warning',
            code: 'PHOTO_QUALITY',
            message: 'Profile photo may be too blurry',
            messageBn: 'প্রোফাইল ছবি ঝাপসা হতে পারে',
            action: 'Re-upload a clear, well-lit passport-size photo',
            actionBn: 'স্পষ্ট পাসপোর্ট সাইজের ছবি আবার আপলোড করুন',
            scriptBn: null,
            scriptEn: null,
        },
    ],
    eligibleSchemes: [
        {
            schemeName: 'Lakshmir Bhandar (Partial)',
            schemeNameBn: 'লক্ষ্মীর ভান্ডার (আংশিক)',
            benefit: '₹500/month',
            category: 'Women',
            categoryBn: 'মহিলা',
            applyAt: ['Duare Sarkar Camp', 'BDO Office, Bolpur'],
            applyOnline: 'https://wbcdwdsw.gov.in',
        },
        {
            schemeName: 'Swasthya Sathi',
            schemeNameBn: 'স্বাস্থ্য সাথী',
            benefit: '₹5 lakh health cover',
            category: 'Health',
            categoryBn: 'স্বাস্থ্য',
            applyAt: ['District Hospital', 'Duare Sarkar'],
            applyOnline: null,
        },
    ],
    roadmap: [
        {
            step: 1,
            action: 'Visit your Bank Branch',
            actionBn: 'আপনার ব্যাঙ্ক শাখায় যান',
            location: 'SBI / UCO Bank Branch with Aadhaar',
            done: false,
        },
        {
            step: 2,
            action: 'Get Income Certificate',
            actionBn: 'আয়ের শংসাপত্র নিন',
            location: 'BDO Office, Bolpur Block',
            done: false,
        },
        {
            step: 3,
            action: 'Upload documents on portal',
            actionBn: 'পোর্টালে নথি আপলোড করুন',
            location: 'wbcdwdsw.gov.in or Duare Sarkar',
            done: false,
        },
        {
            step: 4,
            action: 'Visit Duare Sarkar Camp',
            actionBn: 'দুয়ারে সরকার ক্যাম্পে যান',
            location: 'Check local notice board for next date',
            done: false,
        },
    ],
}

// ─── Band config ─────────────────────────────────────────────────────────────
function getBandConfig(band) {
    if (band === 'GREEN') return {
        bg: 'bg-green-500/10',
        border: 'border-green-500/30',
        text: 'text-green-400',
        dot: 'bg-green-400',
        verdictKey: 'bandGreen',
        subKey: 'bandGreenSub',
    }
    if (band === 'AMBER') return {
        bg: 'bg-amber-500/10',
        border: 'border-amber-500/30',
        text: 'text-amber-400',
        dot: 'bg-amber-400',
        verdictKey: 'bandAmber',
        subKey: 'bandAmberSub',
    }
    return {
        bg: 'bg-red-500/10',
        border: 'border-red-500/30',
        text: 'text-red-400',
        dot: 'bg-red-400',
        verdictKey: 'bandRed',
        subKey: 'bandRedSub',
    }
}

// ─── Inner component that uses hooks ─────────────────────────────────────────
function DashboardInner() {
    const searchParams = useSearchParams()
    const { t: tDash } = useTranslation('dashboard')
    const { t: tCommon } = useTranslation('common')

    const [data, setData] = useState(null)
    const [scoreAnimDone, setScoreAnimDone] = useState(false)

    useEffect(() => {
        // 1. Try query params
        const qScore = searchParams.get('score')
        const qBand = searchParams.get('band')
        const qScheme = searchParams.get('scheme')

        if (qScore && qBand) {
            setData({ ...MOCK_DATA, score: parseInt(qScore, 10), band: qBand })
            return
        }

        // 2. Try localStorage
        try {
            const stored = localStorage.getItem('wb_sahayak_result')
            if (stored) {
                setData(JSON.parse(stored))
                return
            }
        } catch { }

        // 3. Fall back to mock
        setData(MOCK_DATA)
    }, [searchParams])

    if (!data) {
        return (
            <div className="min-h-screen bg-slate-950 flex items-center justify-center pt-14">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-14 h-14 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
                    <p className="text-slate-400 text-sm">Loading results...</p>
                </div>
            </div>
        )
    }

    const bandConfig = getBandConfig(data.band)
    const showRoadmap = data.band === 'RED' || data.band === 'AMBER'

    return (
        <div className="min-h-screen bg-slate-950 text-white pb-28">
            <TopBar />

            <div className="max-w-xl mx-auto px-4 pt-20">

                {/* ── Hero Score Section ── */}
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                    className="flex flex-col items-center py-8"
                >
                    <p className="text-slate-400 text-xs font-semibold uppercase tracking-widest mb-4">
                        {tDash('eligibilityScore')}
                    </p>

                    <ScoreMeter score={data.score} shouldAnimate={true} />

                    {/* Band verdict */}
                    <motion.div
                        initial={{ scale: 0.8, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        transition={{ delay: 1.6, type: 'spring', stiffness: 300 }}
                        className={`mt-5 px-5 py-3 rounded-2xl border text-center max-w-xs ${bandConfig.bg} ${bandConfig.border}`}
                    >
                        <p className={`font-bold text-base ${bandConfig.text}`}>
                            {tDash(bandConfig.verdictKey)}
                        </p>
                        <p
                            className="text-slate-400 text-sm mt-1"
                            style={{ fontFamily: "'Noto Sans Bengali', sans-serif" }}
                        >
                            {tDash(bandConfig.subKey)}
                        </p>
                    </motion.div>

                    {/* Scheme context */}
                    {data.schemeName && (
                        <motion.p
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: 2 }}
                            className="mt-3 text-slate-500 text-sm text-center"
                        >
                            For:{' '}
                            <span className="text-slate-300 font-semibold">{data.schemeName}</span>
                            {data.schemeNameBn && (
                                <span
                                    className="text-slate-400 ml-1"
                                    style={{ fontFamily: "'Noto Sans Bengali', sans-serif" }}
                                >
                                    ({data.schemeNameBn})
                                </span>
                            )}
                        </motion.p>
                    )}
                </motion.div>

                {/* ── Issues Section ── */}
                {data.issues && data.issues.length > 0 && (
                    <section className="mt-4">
                        <div className="flex items-center gap-2 mb-3">
                            <div className="w-1 h-5 bg-red-500 rounded-full" />
                            <h2 className="text-white font-bold text-base">
                                {tDash('issuesFound')}
                            </h2>
                            <span
                                className="text-slate-400 text-sm ml-1"
                                style={{ fontFamily: "'Noto Sans Bengali', sans-serif" }}
                            >
                                / সমস্যা পাওয়া গেছে
                            </span>
                        </div>
                        <div className="space-y-3">
                            {data.issues.map((issue, i) => (
                                <motion.div
                                    key={i}
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: 0.1 * i + 0.3, duration: 0.4 }}
                                >
                                    <IssueCard {...issue} />
                                </motion.div>
                            ))}
                        </div>
                    </section>
                )}

                {/* ── Eligible Schemes ── */}
                {data.eligibleSchemes && data.eligibleSchemes.length > 0 && (
                    <section className="mt-8">
                        <div className="flex items-center gap-2 mb-3">
                            <div className="w-1 h-5 bg-blue-500 rounded-full" />
                            <h2 className="text-white font-bold text-base">
                                {tDash('schemesQualified')}
                            </h2>
                        </div>
                        <div className="space-y-3">
                            {data.eligibleSchemes.map((scheme, i) => (
                                <SchemeCard key={i} {...scheme} delay={0.1 * i + 0.5} />
                            ))}
                        </div>
                    </section>
                )}

                {/* ── Roadmap ── */}
                {showRoadmap && data.roadmap && data.roadmap.length > 0 && (
                    <section className="mt-8">
                        <div className="flex items-center gap-2 mb-4">
                            <div className="w-1 h-5 bg-amber-500 rounded-full" />
                            <h2 className="text-white font-bold text-base">
                                {tDash('roadmap')}
                            </h2>
                        </div>
                        <div className="pl-1">
                            {data.roadmap.map((roadmapItem, i) => (
                                <RoadmapStep
                                    key={i}
                                    {...roadmapItem}
                                    isLast={i === data.roadmap.length - 1}
                                    delay={0.1 * i + 0.4}
                                />
                            ))}
                        </div>
                    </section>
                )}
            </div>

            {/* ── Sticky CTA ── */}
            <div className="fixed bottom-0 left-0 right-0 z-40 bg-slate-950/95 backdrop-blur-md border-t border-slate-800/60 p-4">
                <div className="max-w-xl mx-auto flex gap-3">
                    <Link href="/" className="flex-1">
                        <motion.button
                            whileTap={{ scale: 0.97 }}
                            className="w-full py-3.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-sm transition-all duration-200 shadow-lg shadow-blue-500/20 flex items-center justify-center gap-2"
                        >
                            <span>🔄</span>
                            {tCommon('checkAnother')}
                        </motion.button>
                    </Link>
                    <Link href={`/scheme/${data.scheme || 'lakshmir_bhandar'}`}>
                        <motion.button
                            whileTap={{ scale: 0.97 }}
                            className="py-3.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-sm transition-all duration-200 border border-slate-700/60 flex items-center gap-2"
                        >
                            <span>📋</span>
                            Details
                        </motion.button>
                    </Link>
                </div>
            </div>
        </div>
    )
}

// ─── Export wrapped in I18nProvider ──────────────────────────────────────────
export default function DashboardContent() {
    return (
        <I18nProvider>
            <DashboardInner />
        </I18nProvider>
    )
}
