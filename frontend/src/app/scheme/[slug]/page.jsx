'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import Link from 'next/link'
import { useTranslation } from 'react-i18next'
import '../../../i18n/config'
import TopBar from '../../../components/TopBar'
import ScriptCard from '../../../components/ScriptCard'
import I18nProvider from '../../../i18n/I18nProvider'
import { getScheme } from '../../../api/client'

// ─── Mock data per scheme ────────────────────────────────────────────────────
const SCHEME_MOCKS = {
    lakshmir_bhandar: {
        id: 'lakshmir_bhandar',
        name: 'Lakshmir Bhandar',
        nameBn: 'লক্ষ্মীর ভান্ডার',
        tag: 'Women | মহিলা',
        tagColor: 'pink',
        department: 'Dept. of Women & Child Dev. & Social Welfare',
        benefit: '₹500/month',
        benefitDetail: 'Monthly transfer to bank account for general category women',
        eligibility: [
            { text: 'Female head of household aged 25-60', textBn: '২৫-৬০ বছর বয়সী মহিলা গৃহকর্ত্রী', met: true },
            { text: 'Permanent resident of West Bengal', textBn: 'পশ্চিমবঙ্গের স্থায়ী বাসিন্দা', met: true },
            { text: 'Annual family income < ₹1.5 lakh', textBn: 'পারিবারিক বার্ষিক আয় ₹১.৫ লক্ষের কম', met: false },
            { text: 'Should not be a government employee', textBn: 'সরকারি চাকরিজীবী নন', met: true },
        ],
        documents: [
            { name: 'Aadhaar Card', nameBn: 'আধার কার্ড', status: 'present' },
            { name: 'Voter ID / Residence Proof', nameBn: 'ভোটার আইডি / বাসস্থান প্রমাণ', status: 'present' },
            { name: 'Bank Passbook (front page)', nameBn: 'ব্যাঙ্ক পাসবুক (প্রথম পৃষ্ঠা)', status: 'warning' },
            { name: 'Income Certificate', nameBn: 'আয়ের শংসাপত্র', status: 'missing' },
            { name: 'Passport-size photo', nameBn: 'পাসপোর্ট সাইজ ছবি', status: 'present' },
        ],
        officeLocations: [
            {
                name: 'BDO Office, Bolpur',
                address: 'Bolpur Block Office, Near Shantiniketan Road, Bolpur, Birbhum 731204',
                timings: 'Mon-Fri, 10am-5pm',
            },
            {
                name: 'Duare Sarkar Camp',
                address: 'Check local gram panchayat notice board for next camp date',
                timings: 'As per schedule',
            },
        ],
        applyOnline: 'https://wbcdwdsw.gov.in',
        script: {
            bengali: 'আমি লক্ষ্মীর ভান্ডার প্রকল্পের জন্য আবেদন করতে এসেছি। আমার নাম সুলতা বেগম। আমি এই ব্লকের স্থায়ী বাসিন্দা এবং আমার পরিবারের আয় ১.৫ লক্ষ টাকার কম। আমার সব নথি এখানে আছে। আমাকে আবেদন ফর্ম পূরণ করতে সাহায্য করুন।',
            english: 'I have come to apply for Lakshmir Bhandar scheme. My name is Sulata Begum. I am a permanent resident of this block and my family income is less than 1.5 lakh. All my documents are here. Please help me fill the application form.',
        },
    },
    sabuj_sathi: {
        id: 'sabuj_sathi',
        name: 'Sabuj Sathi',
        nameBn: 'সবুজ সাথী',
        tag: 'Education | শিক্ষা',
        tagColor: 'green',
        department: 'Dept. of Backward Classes Welfare',
        benefit: 'Free Bicycle',
        benefitDetail: 'Free bicycle for students of Class IX–XII in Government/Govt-aided schools',
        eligibility: [
            { text: 'Student of Class IX–XII', textBn: 'নবম থেকে দ্বাদশ শ্রেণীর ছাত্র/ছাত্রী', met: true },
            { text: 'Enrolled in Govt/Aided school in WB', textBn: 'পশ্চিমবঙ্গের সরকারি/সরকার-পোষিত বিদ্যালয়ে ভর্তি', met: true },
            { text: 'Permanent resident of West Bengal', textBn: 'পশ্চিমবঙ্গের স্থায়ী বাসিন্দা', met: true },
            { text: 'First time applicant (no previous bicycle)', textBn: 'প্রথমবার আবেদনকারী', met: true },
        ],
        documents: [
            { name: 'Aadhaar Card', nameBn: 'আধার কার্ড', status: 'present' },
            { name: 'Student ID / Certificate', nameBn: 'ছাত্র পরিচয়পত্র / শংসাপত্র', status: 'present' },
            { name: 'Bank Passbook with IFSC', nameBn: 'IFSC সহ ব্যাঙ্ক পাসবুক', status: 'warning' },
        ],
        officeLocations: [
            {
                name: 'School Principal / Headmaster',
                address: 'Submit application at your own school',
                timings: 'School hours',
            },
        ],
        applyOnline: null,
        script: {
            bengali: 'আমি সবুজ সাথী প্রকল্পের জন্য আবেদন করতে চাই। আমি এই বিদ্যালয়ের নবম শ্রেণীর ছাত্র। আমি আগে কখনো সাইকেল পাইনি। আমার সব প্রয়োজনীয় নথি এখানে আছে।',
            english: 'I want to apply for Sabuj Sathi scheme. I am a Class IX student of this school. I have never received a bicycle before. All required documents are here.',
        },
    },
    kanyashree: {
        id: 'kanyashree',
        name: 'Kanyashree',
        nameBn: 'কন্যাশ্রী',
        tag: 'Women | মহিলা',
        tagColor: 'purple',
        department: 'Dept. of Women & Child Dev. & Social Welfare',
        benefit: '₹25,000 one-time grant',
        benefitDetail: 'Annual stipend of ₹1000 + one-time grant of ₹25,000 for girls continuing education',
        eligibility: [
            { text: 'Girl student aged 13–18 (for K1)', textBn: '১৩-১৮ বছর বয়সী ছাত্রী (K1)', met: true },
            { text: 'Unmarried girl aged 18+ (for K2)', textBn: '১৮+ বছর বয়সী অবিবাহিত ছাত্রী (K2)', met: true },
            { text: 'Annual family income < ₹1.2 lakh', textBn: 'পারিবারিক বার্ষিক আয় ₹১.২ লক্ষের কম', met: false },
            { text: 'Enrolled in school/college', textBn: 'বিদ্যালয়/মহাবিদ্যালয়ে ভর্তি', met: true },
        ],
        documents: [
            { name: 'Aadhaar Card', nameBn: 'আধার কার্ড', status: 'present' },
            { name: 'Birth Certificate', nameBn: 'জন্ম শংসাপত্র', status: 'present' },
            { name: 'Income Certificate', nameBn: 'আয়ের শংসাপত্র', status: 'missing' },
            { name: 'School enrollment certificate', nameBn: 'ভর্তির শংসাপত্র', status: 'present' },
            { name: 'Bank Account (girl\'s own)', nameBn: 'মেয়ের নামে ব্যাঙ্ক অ্যাকাউন্ট', status: 'present' },
        ],
        officeLocations: [
            {
                name: 'School office',
                address: 'Submit via your school to WBIFMS portal',
                timings: 'School hours',
            },
        ],
        applyOnline: 'https://wbkanyashree.gov.in',
        script: {
            bengali: 'আমি কন্যাশ্রী K2 প্রকল্পের জন্য আবেদন করতে এসেছি। আমার বয়স ১৮ বছর এবং আমি অবিবাহিত। আমি উচ্চমাধ্যমিকের ছাত্রী। আমার পারিবারিক আয় ১.২ লক্ষ টাকার কম।',
            english: 'I have come to apply for Kanyashree K2 scheme. I am 18 years old and unmarried. I am a Class XII student. My family income is less than 1.2 lakh.',
        },
    },
}

// ─── Document status icon ────────────────────────────────────────────────────
function DocStatusIcon({ status }) {
    if (status === 'present') return <span className="text-green-400 text-base">✅</span>
    if (status === 'missing') return <span className="text-red-400 text-base">❌</span>
    return <span className="text-amber-400 text-base">⚠️</span>
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────
function SchemeSkeleton() {
    return (
        <div className="min-h-screen bg-slate-950 pt-20 px-4 pb-10 max-w-xl mx-auto animate-pulse">
            <div className="h-5 bg-slate-800 rounded-full w-24 mb-6" />
            <div className="h-8 bg-slate-800 rounded-full w-3/4 mb-3" />
            <div className="h-5 bg-slate-800 rounded-full w-1/2 mb-6" />
            <div className="h-24 bg-slate-800 rounded-xl mb-4" />
            <div className="grid grid-cols-2 gap-3">
                {[...Array(6)].map((_, i) => (
                    <div key={i} className="h-16 bg-slate-800 rounded-xl" />
                ))}
            </div>
        </div>
    )
}

// ─── Tag color map ────────────────────────────────────────────────────────────
const TAG_COLORS = {
    pink: 'bg-pink-500/15 text-pink-400 border-pink-500/30',
    green: 'bg-green-500/15 text-green-400 border-green-500/30',
    purple: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
    blue: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
}

// ─── Inner component ──────────────────────────────────────────────────────────
function SchemeDetailInner() {
    const params = useParams()
    const slug = params?.slug
    const { t: tCommon } = useTranslation('common')

    const [scheme, setScheme] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        if (!slug) return

        const fetchScheme = async () => {
            setLoading(true)
            setError(null)

            // Try mock first (or if no API URL)
            if (SCHEME_MOCKS[slug]) {
                // Simulate a brief loading state for realism
                await new Promise((res) => setTimeout(res, 400))
                setScheme(SCHEME_MOCKS[slug])
                setLoading(false)
                return
            }

            // Try real API
            try {
                const res = await getScheme(slug)
                setScheme(res.data)
            } catch (err) {
                if (err.isNotFound) {
                    setError('not_found')
                } else {
                    // Fall back to mock if API not available
                    setScheme({ ...SCHEME_MOCKS.lakshmir_bhandar, name: slug.replace(/_/g, ' '), id: slug })
                }
            } finally {
                setLoading(false)
            }
        }

        fetchScheme()
    }, [slug])

    if (loading) return <SchemeSkeleton />

    if (error === 'not_found') {
        return (
            <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center pt-14 px-4 text-center">
                <span className="text-6xl mb-4">🔍</span>
                <h1 className="text-white text-xl font-bold mb-2">Scheme Not Found</h1>
                <p className="text-slate-400 text-sm mb-6">We couldn&apos;t find the scheme &quot;{slug}&quot;</p>
                <Link href="/dashboard" className="px-5 py-2.5 bg-blue-600 text-white rounded-xl font-semibold text-sm hover:bg-blue-500 transition-colors">
                    ← Back to Dashboard
                </Link>
            </div>
        )
    }

    if (!scheme) return <SchemeSkeleton />

    const tagColorClass = TAG_COLORS[scheme.tagColor] || TAG_COLORS.blue

    return (
        <div className="min-h-screen bg-slate-950 text-white pb-28">
            <TopBar />

            <div className="max-w-xl mx-auto px-4 pt-20">

                {/* ── Back arrow ── */}
                <motion.div
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3 }}
                >
                    <Link href="/dashboard" className="inline-flex items-center gap-2 text-slate-400 hover:text-white transition-colors text-sm font-medium mb-5">
                        <span className="w-7 h-7 rounded-lg bg-slate-800 flex items-center justify-center">←</span>
                        Back to Results
                    </Link>
                </motion.div>

                {/* ── Hero ── */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: 0.1 }}
                >
                    {/* Tag badge */}
                    <span className={`text-xs font-bold px-3 py-1 rounded-full border ${tagColorClass} mb-3 inline-block`}>
                        {scheme.tag}
                    </span>

                    <h1 className="text-2xl font-black text-white leading-tight">{scheme.name}</h1>
                    <p
                        className="text-slate-400 text-lg mt-1"
                        style={{ fontFamily: "'Noto Sans Bengali', sans-serif" }}
                    >
                        {scheme.nameBn}
                    </p>
                    {scheme.department && (
                        <p className="text-slate-500 text-xs mt-2">{scheme.department}</p>
                    )}
                </motion.div>

                {/* ── Benefit Callout ── */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.4, delay: 0.2 }}
                    className="mt-5 bg-gradient-to-br from-green-500/15 to-emerald-500/5 border border-green-500/25 rounded-2xl p-5 flex items-center gap-4"
                >
                    <div className="w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center text-2xl flex-shrink-0">
                        💰
                    </div>
                    <div>
                        <p className="text-slate-400 text-xs font-semibold uppercase tracking-wider">Benefit</p>
                        <p className="text-green-300 text-3xl font-black mt-0.5">{scheme.benefit}</p>
                        {scheme.benefitDetail && (
                            <p className="text-slate-400 text-xs mt-1 leading-relaxed">{scheme.benefitDetail}</p>
                        )}
                    </div>
                </motion.div>

                {/* ── Eligibility & Documents Grid ── */}
                <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">

                    {/* Eligibility Criteria */}
                    <motion.div
                        initial={{ opacity: 0, y: 15 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.3 }}
                        className="bg-slate-800/60 border border-slate-700/40 rounded-2xl p-4"
                    >
                        <div className="flex items-center gap-2 mb-3">
                            <span className="text-base">📋</span>
                            <h2 className="text-white font-bold text-sm">{tCommon('eligibilityCriteria')}</h2>
                        </div>
                        <div className="space-y-2">
                            {scheme.eligibility?.map((crit, i) => (
                                <div
                                    key={i}
                                    className={`flex items-start gap-2.5 p-2.5 rounded-lg border ${crit.met
                                        ? 'bg-green-500/5 border-green-500/20'
                                        : 'bg-red-500/5 border-red-500/20'
                                        }`}
                                >
                                    <span className="text-sm flex-shrink-0 mt-0.5">{crit.met ? '✅' : '❌'}</span>
                                    <div>
                                        <p className="text-white text-xs font-semibold leading-tight">{crit.text}</p>
                                        {crit.textBn && (
                                            <p
                                                className="text-slate-400 text-xs mt-0.5"
                                                style={{ fontFamily: "'Noto Sans Bengali', sans-serif" }}
                                            >
                                                {crit.textBn}
                                            </p>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </motion.div>

                    {/* Required Documents */}
                    <motion.div
                        initial={{ opacity: 0, y: 15 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4 }}
                        className="bg-slate-800/60 border border-slate-700/40 rounded-2xl p-4"
                    >
                        <div className="flex items-center gap-2 mb-3">
                            <span className="text-base">📁</span>
                            <h2 className="text-white font-bold text-sm">{tCommon('requiredDocuments')}</h2>
                        </div>
                        <div className="space-y-2">
                            {scheme.documents?.map((doc, i) => (
                                <div
                                    key={i}
                                    className="flex items-center justify-between gap-2 px-3 py-2.5 rounded-lg bg-slate-700/30 border border-slate-700/40"
                                >
                                    <div>
                                        <p className="text-white text-xs font-semibold">{doc.name}</p>
                                        {doc.nameBn && (
                                            <p
                                                className="text-slate-400 text-xs"
                                                style={{ fontFamily: "'Noto Sans Bengali', sans-serif" }}
                                            >
                                                {doc.nameBn}
                                            </p>
                                        )}
                                    </div>
                                    <DocStatusIcon status={doc.status} />
                                </div>
                            ))}
                        </div>
                        {/* Legend */}
                        <div className="mt-3 pt-3 border-t border-slate-700/30 flex gap-3 text-xs text-slate-500">
                            <span>✅ Present</span>
                            <span>❌ Missing</span>
                            <span>⚠️ Warning</span>
                        </div>
                    </motion.div>
                </div>

                {/* ── Where to Apply ── */}
                {scheme.officeLocations && scheme.officeLocations.length > 0 && (
                    <motion.section
                        initial={{ opacity: 0, y: 15 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5 }}
                        className="mt-6"
                    >
                        <div className="flex items-center gap-2 mb-3">
                            <div className="w-1 h-5 bg-blue-500 rounded-full" />
                            <h2 className="text-white font-bold text-base">{tCommon('whereToApply')}</h2>
                        </div>
                        <div className="space-y-3">
                            {scheme.officeLocations.map((loc, i) => (
                                <div
                                    key={i}
                                    className="bg-slate-800/60 border border-slate-700/40 rounded-xl p-4 flex gap-3"
                                >
                                    <div className="w-9 h-9 rounded-xl bg-blue-500/15 flex items-center justify-center text-lg flex-shrink-0">
                                        🏢
                                    </div>
                                    <div>
                                        <p className="text-white font-semibold text-sm">{loc.name}</p>
                                        <p className="text-slate-400 text-xs mt-0.5 leading-relaxed">{loc.address}</p>
                                        {loc.timings && (
                                            <p className="text-slate-500 text-xs mt-1">🕐 {loc.timings}</p>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </motion.section>
                )}

                {/* ── Online Apply ── */}
                {scheme.applyOnline && (
                    <motion.section
                        initial={{ opacity: 0, y: 15 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.55 }}
                        className="mt-5"
                    >
                        <div className="flex items-center gap-2 mb-3">
                            <div className="w-1 h-5 bg-cyan-500 rounded-full" />
                            <h2 className="text-white font-bold text-base">Apply Online</h2>
                        </div>
                        <a
                            href={scheme.applyOnline}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-3 bg-cyan-500/10 border border-cyan-500/25 rounded-xl px-4 py-3.5 hover:bg-cyan-500/15 transition-all group"
                        >
                            <span className="text-cyan-400 text-xl">🌐</span>
                            <span className="text-cyan-300 font-semibold text-sm">{scheme.applyOnline}</span>
                            <span className="ml-auto text-cyan-400 group-hover:translate-x-1 transition-transform">→</span>
                        </a>
                    </motion.section>
                )}

                {/* ── What to Say at Office ── */}
                {scheme.script && (
                    <motion.section
                        initial={{ opacity: 0, y: 15 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.6 }}
                        className="mt-6"
                    >
                        <div className="flex items-center gap-2 mb-3">
                            <div className="w-1 h-5 bg-purple-500 rounded-full" />
                            <h2 className="text-white font-bold text-base">{tCommon('whatToSay')}</h2>
                            <span
                                className="text-slate-400 text-sm"
                                style={{ fontFamily: "'Noto Sans Bengali', sans-serif" }}
                            >
                                / অফিসে কী বলবেন
                            </span>
                        </div>
                        <ScriptCard
                            bengaliText={scheme.script.bengali}
                            englishText={scheme.script.english}
                            audioUrl={scheme.script.audioUrl}
                        />
                    </motion.section>
                )}
            </div>

            {/* ── Sticky CTA ── */}
            <div className="fixed bottom-0 left-0 right-0 z-40 bg-slate-950/95 backdrop-blur-md border-t border-slate-800/60 p-4">
                <div className="max-w-xl mx-auto">
                    <Link href={`/check?scheme=${slug}`}>
                        <motion.button
                            whileTap={{ scale: 0.97 }}
                            className="w-full py-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-sm transition-all duration-200 shadow-lg shadow-blue-500/20 flex items-center justify-center gap-2"
                        >
                            <span>⚡</span>
                            {tCommon('checkEligibility')} for {scheme.name}
                        </motion.button>
                    </Link>
                </div>
            </div>
        </div>
    )
}

// ─── Export wrapped in I18nProvider ──────────────────────────────────────────
export default function SchemeDetailPage() {
    return (
        <I18nProvider>
            <SchemeDetailInner />
        </I18nProvider>
    )
}
