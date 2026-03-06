'use client'

import { useReducer, useEffect, useRef } from 'react'
import {
    X, ClipboardCheck, ArrowRight, Loader2, CheckCircle2,
} from 'lucide-react'
import { useEligibility } from '@/hooks/useEligibility'
import { useUIStore } from '@/stores/ui.store'
import type { EligibilityResult } from '@/types'

interface EligibilityState {
    step: number
    age: string
    gender: string
    caste: string
    district: string
    is_govt_employee: boolean | null
    pays_income_tax: boolean | null
    income_bracket: string
    has_daughter: boolean | null
    has_school_child: boolean | null
}

type Action =
    | { type: 'SET'; key: string; value: string | boolean | null }
    | { type: 'NEXT' }
    | { type: 'RESET' }

const INITIAL: EligibilityState = {
    step: 1, age: '', gender: '', caste: '',
    district: '', is_govt_employee: null, pays_income_tax: null,
    income_bracket: '', has_daughter: null, has_school_child: null,
}

function reducer(state: EligibilityState, action: Action): EligibilityState {
    switch (action.type) {
        case 'SET': return { ...state, [action.key]: action.value }
        case 'NEXT': return { ...state, step: state.step + 1 }
        case 'RESET': return INITIAL
        default: return state
    }
}

const WB_DISTRICTS = [
    'Kolkata', 'North 24 Parganas', 'South 24 Parganas', 'Howrah', 'Hooghly',
    'Bardhaman', 'Birbhum', 'Bankura', 'Purulia', 'Midnapore (East)',
    'Midnapore (West)', 'Jhargram', 'Nadia', 'Murshidabad', 'Malda',
    'North Dinajpur', 'South Dinajpur', 'Cooch Behar', 'Jalpaiguri',
    'Darjeeling', 'Alipurduar', 'Kalimpong', 'Dakshin Dinajpur',
]

function ProgressBar({ step }: { step: number }) {
    return (
        <div style={{ marginBottom: 20 }}>
            <p style={{ fontSize: 13, color: 'var(--color-muted)', margin: '0 0 8px' }}>
                Step {step} of 4
            </p>
            <div style={{ display: 'flex', gap: 4 }}>
                {[1, 2, 3, 4].map(s => (
                    <div key={s} className={`step-seg ${s < step ? 'done' : s === step ? 'current' : ''}`} />
                ))}
            </div>
        </div>
    )
}

function Label({ children, required }: { children: React.ReactNode; required?: boolean }) {
    return (
        <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text)', marginBottom: 10 }}>
            {children} {required && <span style={{ color: '#C81E1E' }}>*</span>}
        </div>
    )
}

interface Props {
    isOpen: boolean
    onClose: () => void
    schemeId?: string
    user?: { name: string | null; phone: string } | null
}

export default function CheckEligibilityModal({ isOpen, onClose, schemeId, user }: Props) {
    const [state, dispatch] = useReducer(reducer, INITIAL)
    const { check, result, loading: checking } = useEligibility()
    const { eligibilitySchemeId } = useUIStore()
    const firstRef = useRef<HTMLInputElement | null>(null)
    const selectRef = useRef<HTMLSelectElement | null>(null)

    // Effective scheme: prop > store > fallback
    const activeSchemeId = schemeId || eligibilitySchemeId || 'lakshmir_bhandar'

    useEffect(() => {
        if (!isOpen) return
        const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') handleClose() }
        document.addEventListener('keydown', handler)
        setTimeout(() => firstRef.current?.focus(), 100)
        return () => document.removeEventListener('keydown', handler)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isOpen])

    function handleClose() {
        dispatch({ type: 'RESET' }); onClose()
    }

    function set(key: string, value: string | boolean | null) { dispatch({ type: 'SET', key, value }) }

    function canGoNext(): boolean {
        if (state.step === 1) return !!(state.age && state.gender && state.caste)
        if (state.step === 2) return !!(state.district && state.is_govt_employee !== null && state.pays_income_tax !== null)
        if (state.step === 3) return !!(state.income_bracket && state.has_daughter !== null && state.has_school_child !== null)
        return true
    }

    async function handleNext() {
        if (state.step < 4) { dispatch({ type: 'NEXT' }); return }
        const { step, ...profileData } = state
        void step // consumed above
        const data = await check({
            scheme_id: activeSchemeId,
            profile: profileData as Record<string, unknown>,
            save: !!user,  // save to history only if authenticated
        })
        if (data) {
            dispatch({ type: 'NEXT' })  // advance to results step
        }
    }

    if (!isOpen) return null

    const bandColor = result?.band === 'GREEN' ? '#059669' : result?.band === 'AMBER' ? '#D97706' : '#DC2626'

    return (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && handleClose()}>
            <div className="modal-box" style={{ maxWidth: 620 }}>

                {/* Header */}
                <div style={{ padding: '24px 28px 0', borderBottom: '1px solid var(--color-border)', paddingBottom: 16 }}>
                    <button onClick={handleClose} style={{
                        position: 'absolute', top: 16, right: 16,
                        background: 'none', border: 'none', cursor: 'pointer',
                        color: '#9CA3AF', display: 'flex',
                    }}>
                        <X size={22} />
                    </button>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                        <ClipboardCheck size={24} color="#F59E0B" />
                        <h2 style={{ fontWeight: 700, fontSize: 20, margin: 0, color: 'var(--color-text)' }}>
                            Check Eligibility
                        </h2>
                    </div>
                    <p style={{ fontSize: 13, color: 'var(--color-muted)', margin: 0 }}>
                        Let&apos;s find schemes tailored for you.
                    </p>
                </div>

                {/* Body */}
                <div style={{ padding: '20px 28px' }}>
                    <ProgressBar step={state.step} />

                    {/* STEP 1 */}
                    {state.step === 1 && (
                        <div>
                            <Label required>How old are you?</Label>
                            <div style={{ display: 'flex', alignItems: 'center', border: '1.5px solid #E5E7EB', borderRadius: 10, width: 200, overflow: 'hidden', marginBottom: 20 }}>
                                <input
                                    ref={firstRef}
                                    type="number"
                                    min={1} max={120}
                                    placeholder="Enter age in years"
                                    value={state.age}
                                    onChange={e => set('age', e.target.value)}
                                    style={{ flex: 1, border: 'none', outline: 'none', padding: '12px 14px', fontSize: 15, background: 'transparent', color: 'var(--color-text)' }}
                                />
                                <span style={{ padding: '12px 14px', color: '#9CA3AF', borderLeft: '1px solid #E5E7EB', fontSize: 13 }}>Years</span>
                            </div>

                            <Label required>Select Gender</Label>
                            <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
                                {[
                                    { val: 'male', label: 'Male', icon: '👨' },
                                    { val: 'female', label: 'Female', icon: '👩' },
                                    { val: 'other', label: 'Other', icon: '⚧' },
                                ].map(({ val, label, icon }) => (
                                    <button key={val} onClick={() => set('gender', val)}
                                        className={`toggle-btn ${state.gender === val ? 'selected' : ''}`}>
                                        <span style={{ fontSize: 28 }}>{icon}</span>
                                        <span style={{ fontSize: 14, fontWeight: 500 }}>{label}</span>
                                    </button>
                                ))}
                            </div>

                            <Label required>Social Category</Label>
                            <div style={{ display: 'flex', gap: 10 }}>
                                {['General', 'OBC', 'SC', 'ST'].map(cat => (
                                    <button key={cat} onClick={() => set('caste', cat)}
                                        className={`toggle-chip ${state.caste === cat ? 'selected' : ''}`}>
                                        {cat}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* STEP 2 */}
                    {state.step === 2 && (
                        <div>
                            <Label required>Select District</Label>
                            <select
                                ref={selectRef}
                                value={state.district}
                                onChange={e => set('district', e.target.value)}
                                style={{
                                    width: '100%', border: '1.5px solid #E5E7EB', borderRadius: 10,
                                    padding: '12px 14px', fontSize: 14, outline: 'none', marginBottom: 20,
                                    background: 'var(--color-surface, #fff)', color: 'var(--color-text)', cursor: 'pointer',
                                }}
                            >
                                <option value="">Select your district</option>
                                {WB_DISTRICTS.map(d => <option key={d} value={d}>{d}</option>)}
                            </select>

                            <Label required>Are you a Government Employee?</Label>
                            <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
                                {['Yes', 'No'].map(opt => (
                                    <button key={opt} onClick={() => set('is_govt_employee', opt === 'Yes')}
                                        className={`toggle-chip ${state.is_govt_employee === (opt === 'Yes') ? 'selected' : ''}`}>
                                        {opt}
                                    </button>
                                ))}
                            </div>

                            <Label required>Do you pay Income Tax?</Label>
                            <div style={{ display: 'flex', gap: 10 }}>
                                {['Yes', 'No'].map(opt => (
                                    <button key={opt} onClick={() => set('pays_income_tax', opt === 'Yes')}
                                        className={`toggle-chip ${state.pays_income_tax === (opt === 'Yes') ? 'selected' : ''}`}>
                                        {opt}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* STEP 3 */}
                    {state.step === 3 && (
                        <div>
                            <Label required>Annual Family Income</Label>
                            <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
                                {[
                                    { val: 'below_1l', top: 'Below', bottom: '₹ 1 Lakh' },
                                    { val: '1l_2.5l', top: 'Between', bottom: '₹1L - 2.5L' },
                                    { val: '2.5l_5l', top: 'Between', bottom: '₹2.5L - 5L' },
                                    { val: 'above_5l', top: 'Above', bottom: '₹ 5 Lakh' },
                                ].map(({ val, top, bottom }) => (
                                    <div key={val} onClick={() => set('income_bracket', val)}
                                        className={`income-card ${state.income_bracket === val ? 'selected' : ''}`}>
                                        <div style={{ fontSize: 11, color: '#9CA3AF', marginBottom: 4 }}>{top}</div>
                                        <div style={{ fontSize: 14, fontWeight: 600 }}>{bottom}</div>
                                    </div>
                                ))}
                            </div>

                            <Label required>Do you have a daughter?</Label>
                            <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
                                {['Yes', 'No'].map(opt => (
                                    <button key={opt} onClick={() => set('has_daughter', opt === 'Yes')}
                                        className={`toggle-chip ${state.has_daughter === (opt === 'Yes') ? 'selected' : ''}`}>
                                        {opt}
                                    </button>
                                ))}
                            </div>

                            <Label required>Do you have school-going children?</Label>
                            <div style={{ display: 'flex', gap: 10 }}>
                                {['Yes', 'No'].map(opt => (
                                    <button key={opt} onClick={() => set('has_school_child', opt === 'Yes')}
                                        className={`toggle-chip ${state.has_school_child === (opt === 'Yes') ? 'selected' : ''}`}>
                                        {opt}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* STEP 4 */}
                    {state.step === 4 && (
                        <div style={{ textAlign: 'center' }}>
                            {checking ? (
                                <div style={{ padding: '40px 0' }}>
                                    <Loader2 size={40} color="#1A56DB" style={{ animation: 'spin 1s linear infinite', marginBottom: 16 }} />
                                    <p style={{ color: 'var(--color-muted)', fontSize: 15 }}>Checking your eligibility...</p>
                                </div>
                            ) : result ? (
                                <div>
                                    <svg viewBox="0 0 80 80" width={80} height={80} style={{ margin: '0 auto 12px', display: 'block' }}>
                                        <circle cx={40} cy={40} r={34} fill="none" stroke="#F3F4F6" strokeWidth={8} />
                                        <circle cx={40} cy={40} r={34} fill="none" stroke={bandColor} strokeWidth={8}
                                            strokeDasharray={`${result.score * 2.14} 214`}
                                            strokeLinecap="round" transform="rotate(-90 40 40)"
                                        />
                                        <text x={40} y={45} textAnchor="middle" fill={bandColor} fontSize={16} fontWeight={700}>
                                            {result.score}%
                                        </text>
                                    </svg>

                                    <div style={{ fontSize: 18, fontWeight: 700, color: bandColor, marginBottom: 8 }}>
                                        {result.band_label}
                                    </div>

                                    {result.eligible_basic && (
                                        <div style={{ color: '#057A55', fontSize: 14, marginBottom: 16, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                                            <CheckCircle2 size={18} />
                                            You appear eligible for the schemes below!
                                        </div>
                                    )}

                                    <div style={{ textAlign: 'left', marginBottom: 20 }}>
                                        {(result.recommendations || []).map((s: import('@/types').Scheme) => (
                                            <div key={s.scheme_id} style={{
                                                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                                padding: '10px 0', borderBottom: '1px solid var(--color-border)',
                                            }}>
                                                <span style={{ fontWeight: 500, fontSize: 14 }}>{s.scheme_name}</span>
                                                <a href={`/scheme/${s.scheme_id}`} onClick={handleClose} style={{ color: '#1A56DB', fontSize: 13, textDecoration: 'none', fontWeight: 500 }}>
                                                    View →
                                                </a>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ) : (
                                <div style={{ padding: '24px 0' }}>
                                    <p style={{ color: 'var(--color-muted)', fontSize: 14 }}>
                                        Click &quot;Check Now&quot; to verify your eligibility based on your details.
                                    </p>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="sticky-bottom">
                    <button onClick={handleClose} style={{
                        background: 'none', border: 'none', cursor: 'pointer',
                        color: '#6B7280', fontSize: 14, fontWeight: 500, padding: '8px 16px',
                    }}>
                        Cancel
                    </button>
                    {!result && (
                        <button
                            onClick={handleNext}
                            disabled={!canGoNext() || checking}
                            style={{
                                background: canGoNext() && !checking ? '#1A56DB' : '#93C5FD',
                                color: '#fff', border: 'none', borderRadius: 10,
                                padding: '10px 24px', fontWeight: 600, fontSize: 14, cursor: canGoNext() && !checking ? 'pointer' : 'not-allowed',
                                display: 'flex', alignItems: 'center', gap: 6,
                            }}
                        >
                            {state.step < 4 ? <>Next <ArrowRight size={16} /></> : checking ? <><Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> Checking...</> : 'Check Now'}
                        </button>
                    )}
                </div>
            </div>
            <style>{`@keyframes spin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }`}</style>
        </div>
    )
}
