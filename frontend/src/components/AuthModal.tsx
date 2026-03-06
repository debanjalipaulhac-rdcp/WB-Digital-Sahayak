'use client'

import { useState, useRef, useEffect } from 'react'
import { X, Landmark, Loader2 } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { useUIStore } from '@/stores/ui.store'

type AuthStep = 'phone' | 'otp' | 'name'

interface Props {
    isOpen: boolean
    onClose: () => void
}

export default function AuthModal({ isOpen, onClose }: Props) {
    const { sendOtp, verifyOtp, updateName, loading } = useAuth()
    const { closeModal } = useUIStore()

    const [step, setStep] = useState<AuthStep>('phone')
    const [phone, setPhone] = useState('')
    const [phoneError, setPhoneError] = useState('')
    const [otp, setOtp] = useState<string[]>(['', '', '', '', '', ''])
    const [otpError, setOtpError] = useState('')
    const [name, setName] = useState('')
    const [resendTimer, setResendTimer] = useState(0)
    const otpRefs = useRef<(HTMLInputElement | null)[]>([])
    const firstInputRef = useRef<HTMLInputElement | null>(null)

    useEffect(() => {
        if (!isOpen) return
        const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') handleClose() }
        document.addEventListener('keydown', handler)
        setTimeout(() => firstInputRef.current?.focus(), 100)
        return () => document.removeEventListener('keydown', handler)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isOpen])

    useEffect(() => {
        if (resendTimer <= 0) return
        const id = setTimeout(() => setResendTimer(t => t - 1), 1000)
        return () => clearTimeout(id)
    }, [resendTimer])

    function reset() {
        setStep('phone'); setPhone(''); setOtp(['', '', '', '', '', ''])
        setPhoneError(''); setOtpError(''); setName('')
    }

    function handleClose() { reset(); onClose() }

    async function handleSendOtp() {
        if (!/^[6-9]\d{9}$/.test(phone)) {
            setPhoneError('Enter a valid 10-digit mobile number')
            return
        }
        setPhoneError('')
        const success = await sendOtp(phone)
        if (success) {
            setStep('otp')
            setResendTimer(30)
        }
    }

    function handleOtpChange(idx: number, val: string) {
        if (!/^\d?$/.test(val)) return
        const newOtp = [...otp]
        newOtp[idx] = val
        setOtp(newOtp)
        if (val && idx < 5) otpRefs.current[idx + 1]?.focus()
    }

    function handleOtpKeyDown(idx: number, e: React.KeyboardEvent<HTMLInputElement>) {
        if (e.key === 'Backspace' && !otp[idx] && idx > 0) {
            otpRefs.current[idx - 1]?.focus()
        }
    }

    function handleOtpPaste(e: React.ClipboardEvent<HTMLInputElement>) {
        e.preventDefault()
        const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
        const newOtp = [...otp]
        for (let i = 0; i < 6; i++) newOtp[i] = pasted[i] || ''
        setOtp(newOtp)
        otpRefs.current[Math.min(pasted.length, 5)]?.focus()
    }

    async function handleVerifyOtp() {
        const code = otp.join('')
        if (code.length < 6) { setOtpError('Enter all 6 digits'); return }
        setOtpError('')
        const { success, isNewUser } = await verifyOtp(phone, code)
        if (success) {
            if (isNewUser) {
                setStep('name')
            } else {
                closeModal()
            }
        }
    }

    async function handleSaveName() {
        if (!name.trim()) return
        await updateName(name.trim()) // auto-closes modal via closeModal() in hook
    }

    if (!isOpen) return null

    const maskedPhone = '+91 ' + phone.slice(0, 2) + 'XXX XX' + phone.slice(-2)

    return (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && handleClose()}>
            <div className="modal-box" style={{ maxWidth: 420 }}>

                {/* STEP: PHONE */}
                {step === 'phone' && (
                    <div style={{ padding: '32px' }}>
                        <button onClick={handleClose} style={{
                            position: 'absolute', top: 16, right: 16,
                            background: 'none', border: 'none', cursor: 'pointer',
                            color: '#9CA3AF', borderRadius: '50%', padding: 4,
                            display: 'flex',
                        }}>
                            <X size={20} />
                        </button>

                        <div style={{ textAlign: 'center', marginBottom: 24 }}>
                            <div style={{
                                width: 56, height: 56, background: '#EEF2FF',
                                borderRadius: '50%', display: 'flex', alignItems: 'center',
                                justifyContent: 'center', margin: '0 auto 16px',
                            }}>
                                <Landmark size={28} color="#1A56DB" />
                            </div>
                            <h2 style={{ fontWeight: 700, fontSize: 20, margin: '0 0 4px', color: 'var(--color-text)' }}>
                                Welcome to WB Digital Sahayak
                            </h2>
                            <p style={{ fontSize: 13, color: 'var(--color-muted)', margin: 0 }}>
                                Sign in or create account
                            </p>
                        </div>

                        <hr style={{ borderColor: 'var(--color-border)', margin: '0 0 24px' }} />

                        <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text)', display: 'block', marginBottom: 8 }}>
                            Mobile Number
                        </label>
                        <div style={{ display: 'flex', marginBottom: 6 }}>
                            <div className="phone-prefix">🇮🇳 +91</div>
                            <input
                                ref={firstInputRef}
                                className="phone-input-field"
                                type="tel"
                                inputMode="numeric"
                                maxLength={10}
                                placeholder="Enter 10-digit number"
                                value={phone}
                                onChange={e => { setPhone(e.target.value.replace(/\D/g, '')); setPhoneError('') }}
                                onKeyDown={e => e.key === 'Enter' && handleSendOtp()}
                                style={{ flex: 1 }}
                            />
                        </div>
                        {phoneError && <p style={{ fontSize: 12, color: '#C81E1E', margin: '0 0 8px' }}>{phoneError}</p>}
                        <p style={{ fontSize: 12, color: 'var(--color-muted)', margin: '0 0 20px' }}>
                            We&apos;ll send a 6-digit OTP to verify
                        </p>

                        <button
                            onClick={handleSendOtp}
                            disabled={loading}
                            style={{
                                width: '100%', background: loading ? '#93C5FD' : '#1A56DB',
                                color: '#fff', border: 'none', borderRadius: 10, padding: '13px',
                                fontWeight: 600, fontSize: 15, cursor: loading ? 'not-allowed' : 'pointer',
                                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                            }}
                        >
                            {loading ? <><Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> Sending...</> : 'Send OTP'}
                        </button>
                    </div>
                )}

                {/* STEP: OTP */}
                {step === 'otp' && (
                    <div style={{ padding: '32px' }}>
                        <button onClick={handleClose} style={{
                            position: 'absolute', top: 16, right: 16,
                            background: 'none', border: 'none', cursor: 'pointer',
                            color: '#9CA3AF', borderRadius: '50%', padding: 4, display: 'flex',
                        }}>
                            <X size={20} />
                        </button>

                        <div style={{ textAlign: 'center', marginBottom: 20 }}>
                            <h2 style={{ fontWeight: 700, fontSize: 20, margin: '0 0 4px', color: 'var(--color-text)' }}>Verify OTP</h2>
                            <p style={{ fontSize: 13, color: 'var(--color-muted)', margin: 0 }}>
                                Sent to {maskedPhone}
                            </p>
                            <button onClick={() => setStep('phone')} style={{
                                fontSize: 12, color: '#1A56DB', background: 'none', border: 'none',
                                cursor: 'pointer', textDecoration: 'underline', marginTop: 4,
                            }}>
                                Change number
                            </button>
                        </div>

                        <div className="otp-boxes" style={{ marginBottom: 12 }}>
                            {otp.map((digit, i) => (
                                <input
                                    key={i}
                                    ref={el => { otpRefs.current[i] = el; if (i === 0) firstInputRef.current = el }}
                                    className="otp-box"
                                    type="text"
                                    inputMode="numeric"
                                    maxLength={1}
                                    value={digit}
                                    onChange={e => handleOtpChange(i, e.target.value)}
                                    onKeyDown={e => handleOtpKeyDown(i, e)}
                                    onPaste={i === 0 ? handleOtpPaste : undefined}
                                />
                            ))}
                        </div>
                        {otpError && <p style={{ fontSize: 12, color: '#C81E1E', textAlign: 'center', margin: '0 0 8px' }}>{otpError}</p>}

                        <button
                            onClick={handleVerifyOtp}
                            disabled={loading}
                            style={{
                                width: '100%', background: loading ? '#93C5FD' : '#1A56DB', color: '#fff', border: 'none',
                                borderRadius: 10, padding: '13px', fontWeight: 600, fontSize: 15,
                                cursor: loading ? 'not-allowed' : 'pointer', marginBottom: 12,
                                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                            }}
                        >
                            {loading ? <><Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> Verifying...</> : 'Verify OTP'}
                        </button>

                        <div style={{ textAlign: 'center', fontSize: 13, color: 'var(--color-muted)' }}>
                            {resendTimer > 0 ? (
                                <span>Resend in {resendTimer}s</span>
                            ) : (
                                <button
                                    onClick={() => { setOtp(['', '', '', '', '', '']); handleSendOtp() }}
                                    style={{ fontSize: 13, color: '#1A56DB', background: 'none', border: 'none', cursor: 'pointer' }}
                                >
                                    Resend OTP
                                </button>
                            )}
                        </div>
                    </div>
                )}

                {/* STEP: NAME */}
                {step === 'name' && (
                    <div style={{ padding: '32px' }}>
                        <div style={{ textAlign: 'center', marginBottom: 20 }}>
                            <div style={{ fontSize: 32, marginBottom: 8 }}>👋</div>
                            <h2 style={{ fontWeight: 700, fontSize: 20, margin: '0 0 4px', color: 'var(--color-text)' }}>
                                Almost there!
                            </h2>
                            <p style={{ fontSize: 13, color: 'var(--color-muted)', margin: 0 }}>
                                What should we call you?
                            </p>
                        </div>

                        <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text)', display: 'block', marginBottom: 8 }}>
                            Your Name
                        </label>
                        <input
                            ref={firstInputRef}
                            type="text"
                            placeholder="Enter your name"
                            value={name}
                            onChange={e => setName(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && handleSaveName()}
                            style={{
                                width: '100%', border: '1.5px solid #E5E7EB', borderRadius: 10,
                                padding: '12px 16px', fontSize: 15, outline: 'none', marginBottom: 20,
                                boxSizing: 'border-box',
                            }}
                        />
                        <button
                            onClick={handleSaveName}
                            disabled={!name.trim() || loading}
                            style={{
                                width: '100%', background: (name.trim() && !loading) ? '#1A56DB' : '#93C5FD',
                                color: '#fff', border: 'none', borderRadius: 10, padding: '13px',
                                fontWeight: 600, fontSize: 15, cursor: (name.trim() && !loading) ? 'pointer' : 'not-allowed',
                                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                            }}
                        >
                            {loading ? <><Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> Saving...</> : 'Save & Continue'}
                        </button>
                    </div>
                )}
            </div>
            <style>{`@keyframes spin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }`}</style>
        </div>
    )
}
