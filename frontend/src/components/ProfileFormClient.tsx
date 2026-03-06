'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import {
    UserRound, Phone, Lock, Minus, Plus, LayoutGrid, Wallet,
    IndianRupee, Briefcase, CheckCircle2, Loader2,
} from 'lucide-react'
import React from 'react'
import { useProfileSave } from '@/hooks/useProfile'
import type { ProfileData } from '@/types'

const CASTE_OPTIONS = ['General (UR)', 'SC', 'ST', 'OBC-A', 'OBC-B']

function SectionCard({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
    return (
        <div style={{
            background: 'var(--color-surface, #fff)',
            border: '1px solid var(--color-border)',
            borderRadius: 16, padding: '24px 28px', marginBottom: 16,
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
                <div style={{
                    width: 40, height: 40, background: '#EEF2FF', borderRadius: 10,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                    {icon}
                </div>
                <span style={{ fontWeight: 600, fontSize: 17, color: 'var(--color-text)' }}>{title}</span>
            </div>
            {children}
        </div>
    )
}

function Label({ children }: { children: React.ReactNode }) {
    return (
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            {children}
        </div>
    )
}

interface InputWithIconProps {
    leftIcon: React.ReactNode
    value: string
    onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void
    disabled?: boolean
    rightIcon?: React.ReactNode
    placeholder?: string
    type?: string
}

function InputWithIcon({ leftIcon, value, onChange, disabled, rightIcon, placeholder, type = 'text' }: InputWithIconProps) {
    return (
        <div style={{
            display: 'flex', alignItems: 'center',
            border: '1.5px solid var(--color-border)', borderRadius: 10,
            overflow: 'hidden', background: disabled ? '#F9FAFB' : 'var(--color-surface, #fff)',
        }}>
            <div style={{ padding: '12px 14px', color: '#9CA3AF', flexShrink: 0, display: 'flex' }}>
                {leftIcon}
            </div>
            <input
                type={type} value={value} onChange={onChange}
                disabled={disabled} placeholder={placeholder}
                style={{
                    flex: 1, border: 'none', outline: 'none', padding: '12px 0',
                    fontSize: 15, background: 'transparent', color: 'var(--color-text)',
                    cursor: disabled ? 'not-allowed' : 'text',
                }}
            />
            {rightIcon && <div style={{ padding: '12px 14px', color: '#9CA3AF', flexShrink: 0, display: 'flex' }}>{rightIcon}</div>}
        </div>
    )
}

interface Props {
    initialProfile: ProfileData | null
}

export function ProfileFormClient({ initialProfile }: Props) {
    const router = useRouter()
    const { save, saving } = useProfileSave()

    const [name, setName] = useState(initialProfile?.name ?? '')
    const [age, setAge] = useState(initialProfile?.age ?? 25)
    const [gender, setGender] = useState(initialProfile?.gender ?? 'male')
    const [caste, setCaste] = useState(initialProfile?.caste ?? 'General (UR)')
    const [income, setIncome] = useState(initialProfile?.annual_income_bracket ?? '')
    const [govtJob, setGovtJob] = useState<boolean | null>(initialProfile?.is_govt_employee ?? null)

    const phone = initialProfile?.phone || ''
    const maskedPhone = phone ? `+91 ${phone.slice(0, 5)} ${phone.slice(5)}` : ''

    async function handleSave() {
        await save({
            name: name || undefined,
            age,
            gender,
            caste,
            annual_income_bracket: income || undefined,
            is_govt_employee: govtJob ?? undefined,
        })
    }

    return (
        <>
            {/* Card 1: Basic Info */}
            <SectionCard icon={<UserRound size={22} color="#1A56DB" />} title="Basic Information">
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
                    <div>
                        <Label>Full Name</Label>
                        <InputWithIcon
                            leftIcon={<UserRound size={16} />}
                            value={name ?? ''}
                            onChange={e => setName(e.target.value)}
                            placeholder="Your full name"
                        />
                    </div>
                    <div>
                        <Label>Phone Number</Label>
                        <InputWithIcon
                            leftIcon={<Phone size={16} />}
                            value={maskedPhone}
                            disabled
                            rightIcon={<Lock size={14} />}
                        />
                        <p style={{ fontSize: 11, color: 'var(--color-muted)', margin: '4px 0 0' }}>
                            Contact support to change phone number.
                        </p>
                    </div>
                </div>
                <div>
                    <Label>Age (Years)</Label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <button
                            onClick={() => setAge(a => Math.max(1, a - 1))}
                            style={{ width: 36, height: 36, border: '1.5px solid var(--color-border)', borderRadius: 8, background: 'var(--color-surface, #fff)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                        >
                            <Minus size={16} color="var(--color-text)" />
                        </button>
                        <span style={{ fontSize: 22, fontWeight: 700, color: 'var(--color-text)', minWidth: 48, textAlign: 'center' }}>{age}</span>
                        <button
                            onClick={() => setAge(a => Math.min(120, a + 1))}
                            style={{ width: 36, height: 36, border: '1.5px solid var(--color-border)', borderRadius: 8, background: 'var(--color-surface, #fff)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                        >
                            <Plus size={16} color="var(--color-text)" />
                        </button>
                    </div>
                </div>
            </SectionCard>

            {/* Card 2: Social & Demographic */}
            <SectionCard icon={<LayoutGrid size={22} color="#1A56DB" />} title="Social & Demographic">
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, alignItems: 'start' }}>
                    <div>
                        <Label>Gender</Label>
                        <div style={{ display: 'flex', gap: 8 }}>
                            {[
                                { val: 'male', label: 'Male', icon: '👨' },
                                { val: 'female', label: 'Female', icon: '👩' },
                                { val: 'other', label: 'Other', icon: '⚧' },
                            ].map(({ val, label, icon }) => (
                                <button key={val} onClick={() => setGender(val)}
                                    className={`toggle-btn ${gender === val ? 'selected' : ''}`}
                                    style={{ minHeight: 72 }}>
                                    <span style={{ fontSize: 20 }}>{icon}</span>
                                    <span style={{ fontSize: 12, fontWeight: 500 }}>{label}</span>
                                </button>
                            ))}
                        </div>
                    </div>
                    <div>
                        <Label>Social Category (Caste)</Label>
                        <select
                            value={caste}
                            onChange={e => setCaste(e.target.value)}
                            style={{
                                width: '100%', border: '1.5px solid var(--color-border)', borderRadius: 10,
                                padding: '12px 14px', fontSize: 14, background: 'var(--color-surface, #fff)',
                                color: 'var(--color-text)', outline: 'none', cursor: 'pointer',
                            }}
                        >
                            {CASTE_OPTIONS.map(o => <option key={o}>{o}</option>)}
                        </select>
                    </div>
                </div>
            </SectionCard>

            {/* Card 3: Economic Details */}
            <SectionCard icon={<Wallet size={22} color="#1A56DB" />} title="Economic Details">
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
                    <IndianRupee size={14} color="#F59E0B" />
                    <Label>Annual Family Income</Label>
                </div>
                <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
                    {[
                        { val: 'below_1l', top: 'Below', bottom: '₹ 1 Lakh' },
                        { val: '1l_2.5l', top: 'Between', bottom: '₹1L - 2.5L' },
                        { val: '2.5l_5l', top: 'Between', bottom: '₹2.5L - 5L' },
                        { val: 'above_5l', top: 'Above', bottom: '₹ 5 Lakh' },
                    ].map(({ val, top, bottom }) => (
                        <div key={val} onClick={() => setIncome(val)}
                            className={`income-card ${income === val ? 'selected' : ''}`}
                            style={{ minWidth: 100 }}>
                            <div style={{ fontSize: 11, color: '#9CA3AF', marginBottom: 4 }}>{top}</div>
                            <div style={{ fontSize: 13, fontWeight: 600 }}>{bottom}</div>
                        </div>
                    ))}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
                    <Briefcase size={14} color="#6B7280" />
                    <Label>Is any family member in a Government Job?</Label>
                </div>
                <div style={{ display: 'flex', gap: 10 }}>
                    {['Yes', 'No'].map(opt => (
                        <button key={opt} onClick={() => setGovtJob(opt === 'Yes')}
                            className={`toggle-chip ${govtJob === (opt === 'Yes') ? 'selected' : ''}`}
                            style={{ flexGrow: 0, minWidth: 80 }}>
                            {opt}
                        </button>
                    ))}
                </div>
            </SectionCard>

            {/* Sticky bottom bar */}
            <div className="sticky-bottom">
                <button onClick={() => router.back()} style={{
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: '#6B7280', fontSize: 14, fontWeight: 500, padding: '8px 16px',
                }}>
                    Cancel
                </button>
                <button
                    onClick={handleSave}
                    disabled={saving}
                    style={{
                        display: 'flex', alignItems: 'center', gap: 8,
                        background: saving ? '#93C5FD' : '#1A56DB', color: '#fff',
                        border: 'none', borderRadius: 10, padding: '12px 28px',
                        fontWeight: 600, fontSize: 14, cursor: saving ? 'not-allowed' : 'pointer',
                    }}
                >
                    {saving
                        ? <><Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> Saving...</>
                        : <><CheckCircle2 size={18} /> Save Details</>
                    }
                </button>
            </div>
            <style>{`@keyframes spin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }`}</style>
        </>
    )
}
