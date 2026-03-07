'use client'

import { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { useUIStore } from '@/stores/ui.store'
import { useEligibility } from '@/hooks/useEligibility'
import  EligibilityResultPanel  from '@/components/EligibilityResultPanel'
import ScriptCard from '@/components/ScriptCard'
import type { ScriptResponse, Lang } from '@/types'

/* ─── Types ─────────────────────────────────────────────────────────────── */

interface Props {
  user?: { name: string | null; phone: string } | null
}

interface FormState {
  // Step 1
  age: string
  gender: string
  caste: string
  // Step 2
  is_govt_employee: boolean | null
  pays_income_tax: boolean | null
  has_daughter: boolean | null
  has_school_child: boolean | null
  district: string
  // Step 3
  aadhaar_name: string
  bank_name: string
  voter_name: string
  aadhaar_bank_linked: boolean
  // Step 4
  bank_active: boolean | null
  bank_last_transaction_months_ago: number
  docs_present: string[]
  docs_missing: string[]
}

const INITIAL_FORM: FormState = {
  age: '',
  gender: '',
  caste: '',
  is_govt_employee: null,
  pays_income_tax: null,
  has_daughter: null,
  has_school_child: null,
  district: '',
  aadhaar_name: '',
  bank_name: '',
  voter_name: '',
  aadhaar_bank_linked: false,
  bank_active: null,
  bank_last_transaction_months_ago: 0,
  docs_present: ['aadhaar'],
  docs_missing: ['voter_id', 'bank_passbook', 'ration_card'],
}

const ALL_DOCS = [
  { id: 'aadhaar', label: 'Aadhaar Card' },
  { id: 'voter_id', label: 'Voter ID Card' },
  { id: 'bank_passbook', label: 'Bank Passbook' },
  { id: 'ration_card', label: 'Ration Card' },
  { id: 'income_certificate', label: 'Income Certificate' },
  { id: 'age_proof', label: 'Age Proof (Birth Cert / Marksheet)' },
]

/* ─── Validation ────────────────────────────────────────────────────────── */

function isStepValid(step: number, form: FormState): boolean {
  switch (step) {
    case 1:
      return (
        form.age !== '' &&
        Number(form.age) > 0 &&
        Number(form.age) < 120 &&
        form.gender !== '' &&
        form.caste !== ''
      )
    case 2:
      return (
        form.is_govt_employee !== null &&
        form.pays_income_tax !== null &&
        form.district.trim().length > 1
      )
    case 3:
      return form.aadhaar_name.trim().length > 1 && form.bank_name.trim().length > 1
    case 4:
      return form.bank_active !== null
    default:
      return true
  }
}

/* ─── PillButton Component ──────────────────────────────────────────────── */

function PillButton({
  label,
  emoji,
  selected,
  onClick,
}: {
  label: string
  emoji?: string
  selected: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 6,
        padding: '12px 16px',
        borderRadius: 12,
        border: selected ? '2px solid #3B82F6' : '2px solid var(--border)',
        background: selected ? '#EFF6FF' : 'var(--card)',
        color: selected ? '#1D4ED8' : 'var(--foreground)',
        cursor: 'pointer',
        fontSize: 14,
        fontWeight: selected ? 600 : 400,
        minWidth: 80,
        transition: 'all 0.15s ease',
      }}
    >
      {emoji && <span style={{ fontSize: 22 }}>{emoji}</span>}
      {label}
    </button>
  )
}

/* ─── Main Component ────────────────────────────────────────────────────── */

export default function CheckEligibilityModal({ user }: Props) {
  const [step, setStep] = useState(1)
  const [form, setForm] = useState<FormState>(INITIAL_FORM)
  const [scriptData, setScriptData] = useState<ScriptResponse | null>(null)

  const { activeModal, closeModal, eligibilitySchemeId } = useUIStore()
  const { check, fetchScript, result, loading } = useEligibility()

  const set = (key: keyof FormState, val: unknown) =>
    setForm((f) => ({ ...f, [key]: val }))

  const toggle = (key: keyof FormState, val: boolean) => set(key, val)

  const toggleDoc = (docId: string, present: boolean) => {
    setForm((f) => ({
      ...f,
      docs_present: present
        ? [...f.docs_present.filter((d) => d !== docId), docId]
        : f.docs_present.filter((d) => d !== docId),
      docs_missing: !present
        ? [...f.docs_missing.filter((d) => d !== docId), docId]
        : f.docs_missing.filter((d) => d !== docId),
    }))
  }

  const handleNext = () => {
    if (step < 4) {
      setStep(step + 1)
    }
  }

  const handleSubmit = async () => {
    setStep(5)

    const body = {
      scheme_id: eligibilitySchemeId ?? 'lakshmir_bhandar',
      profile: {
        name: form.aadhaar_name,
        age: Number(form.age),
        gender: form.gender,
        caste: form.caste,
        district: form.district,
        is_govt_employee: form.is_govt_employee ?? false,
        pays_income_tax: form.pays_income_tax ?? false,
        has_daughter: form.has_daughter ?? false,
        has_school_child: form.has_school_child ?? false,
      },
      checks: {
        aadhaar_name: form.aadhaar_name,
        bank_name: form.bank_name,
        voter_name: form.voter_name || undefined,
        aadhaar_bank_linked: form.aadhaar_bank_linked,
        bank_last_transaction_months_ago: form.bank_active
          ? 0
          : form.bank_last_transaction_months_ago || 7,
        docs_present: form.docs_present,
        docs_missing: form.docs_missing,
      },
      lang: 'bn' as Lang,
      save: !!user,
    }

    await check(body)
  }

  const handleScript = async (scriptCode: string) => {
    const mismatchIssue = result?.issues.find((i) => i.display?.field_a)
    const data = await fetchScript(
      scriptCode,
      'bn',
      mismatchIssue?.display?.field_a ?? '',
      mismatchIssue?.display?.field_b ?? ''
    )
    if (data) setScriptData(data)
  }

  const handleClose = () => {
    closeModal()
    setStep(1)
    setForm(INITIAL_FORM)
    setScriptData(null)
  }

  return (
    <Dialog
      open={activeModal === 'eligibility'}
      onOpenChange={(o) => !o && handleClose()}
    >
      <DialogContent
        className="max-w-lg w-full"
        style={{ maxHeight: '90vh', overflowY: 'auto', padding: '0' }}
      >
        {/* Header */}
        <DialogHeader style={{ padding: '24px 24px 0' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <span style={{ fontSize: 22 }}>📋</span>
            <DialogTitle style={{ fontSize: 20, fontWeight: 700 }}>
              {step < 5 ? 'Check Eligibility' : 'Your Results'}
            </DialogTitle>
          </div>
          {step < 5 && (
            <p style={{ fontSize: 13, color: 'var(--muted-foreground)', margin: 0 }}>
              Let&apos;s find schemes tailored for you.
            </p>
          )}
        </DialogHeader>

        {/* Progress bar */}
        {step <= 4 && (
          <div style={{ padding: '16px 24px 0' }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                marginBottom: 6,
              }}
            >
              <span style={{ fontSize: 12, color: 'var(--muted-foreground)' }}>
                Step {step} of 4
              </span>
              <span style={{ fontSize: 12, color: 'var(--muted-foreground)' }}>
                {Math.round((step / 4) * 100)}%
              </span>
            </div>
            <Progress value={(step / 4) * 100} className="h-1.5" />
          </div>
        )}

        {/* Step content */}
        <div style={{ padding: '24px' }}>
          {step === 1 && <Step1 form={form} set={set} />}
          {step === 2 && <Step2 form={form} set={set} toggle={toggle} />}
          {step === 3 && <Step3 form={form} set={set} toggle={toggle} />}
          {step === 4 && <Step4 form={form} set={set} toggle={toggle} toggleDoc={toggleDoc} />}
          {step === 5 &&
            (loading ? (
              <LoadingResult />
            ) : result ? (
              scriptData ? (
                <ScriptCard
                  script={scriptData}
                  lang="bn"
                  onClose={() => setScriptData(null)}
                />
              ) : (
                <EligibilityResultPanel
                  result={result}
                  lang="bn"
                  onScriptRequest={handleScript}
                  onClose={handleClose}
                />
              )
            ) : (
              <ErrorResult onRetry={() => setStep(4)} />
            ))}
        </div>

        {/* Footer nav */}
        {step <= 4 && (
          <div
            style={{
              padding: '16px 24px 24px',
              display: 'flex',
              justifyContent: 'space-between',
              borderTop: '1px solid var(--border)',
              marginTop: 8,
            }}
          >
            <Button
              variant="ghost"
              onClick={() => (step === 1 ? handleClose() : setStep((s) => s - 1))}
            >
              {step === 1 ? 'Cancel' : '← Back'}
            </Button>
            {step < 4 ? (
              <Button onClick={handleNext} disabled={!isStepValid(step, form)}>
                Next →
              </Button>
            ) : (
              <Button
                onClick={handleSubmit}
                disabled={!isStepValid(4, form) || loading}
                className="bg-blue-600 hover:bg-blue-700"
              >
                {loading ? 'Checking...' : 'Check Eligibility →'}
              </Button>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}


/* ─── Step Components ───────────────────────────────────────────────────── */

function Step1({ form, set }: { form: FormState; set: (key: keyof FormState, val: unknown) => void }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Age */}
      <div>
        <Label htmlFor="age" style={{ fontWeight: 600, marginBottom: 8, display: 'block' }}>
          How old are you? <span style={{ color: '#EF4444' }}>*</span>
        </Label>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Input
            id="age"
            type="number"
            min={1}
            max={120}
            value={form.age}
            onChange={(e) => set('age', e.target.value)}
            placeholder="Age"
            style={{ maxWidth: 120 }}
          />
          <span style={{ color: 'var(--muted-foreground)', fontSize: 14 }}>Years</span>
        </div>
      </div>

      {/* Gender */}
      <div>
        <Label style={{ fontWeight: 600, marginBottom: 12, display: 'block' }}>
          Select Gender <span style={{ color: '#EF4444' }}>*</span>
        </Label>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <PillButton
            label="Male"
            emoji="👨"
            selected={form.gender === 'male'}
            onClick={() => set('gender', 'male')}
          />
          <PillButton
            label="Female"
            emoji="👩"
            selected={form.gender === 'female'}
            onClick={() => set('gender', 'female')}
          />
          <PillButton
            label="Other"
            emoji="⚧"
            selected={form.gender === 'other'}
            onClick={() => set('gender', 'other')}
          />
        </div>
      </div>

      {/* Caste */}
      <div>
        <Label style={{ fontWeight: 600, marginBottom: 12, display: 'block' }}>
          Social Category <span style={{ color: '#EF4444' }}>*</span>
        </Label>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          {['general', 'obc', 'sc', 'st'].map((c) => (
            <PillButton
              key={c}
              label={c.toUpperCase()}
              selected={form.caste === c}
              onClick={() => set('caste', c)}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

function Step2({
  form,
  set,
  toggle,
}: {
  form: FormState
  set: (key: keyof FormState, val: unknown) => void
  toggle: (key: keyof FormState, val: boolean) => void
}) {
  const questions = [
    { key: 'is_govt_employee' as keyof FormState, label: 'Are you a government employee?', required: true },
    { key: 'pays_income_tax' as keyof FormState, label: 'Do you pay income tax?', required: true },
    { key: 'has_daughter' as keyof FormState, label: 'Do you have an unmarried daughter?', required: false },
    { key: 'has_school_child' as keyof FormState, label: 'Do you have a school-going child?', required: false },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {questions.map((q) => (
        <div key={q.key}>
          <Label style={{ fontWeight: 600, marginBottom: 10, display: 'block' }}>
            {q.label}
            {q.required && <span style={{ color: '#EF4444' }}> *</span>}
            {!q.required && (
              <span style={{ color: 'var(--muted-foreground)', fontSize: 12 }}> (optional)</span>
            )}
          </Label>
          <div style={{ display: 'flex', gap: 12 }}>
            <PillButton
              label="Yes"
              emoji="✅"
              selected={form[q.key] === true}
              onClick={() => toggle(q.key, true)}
            />
            <PillButton
              label="No"
              emoji="❌"
              selected={form[q.key] === false}
              onClick={() => toggle(q.key, false)}
            />
          </div>
        </div>
      ))}

      <div>
        <Label htmlFor="district" style={{ fontWeight: 600, marginBottom: 8, display: 'block' }}>
          Your District <span style={{ color: '#EF4444' }}>*</span>
        </Label>
        <Input
          id="district"
          value={form.district}
          onChange={(e) => set('district', e.target.value)}
          placeholder="e.g. Jalpaiguri, Bankura, Howrah"
        />
      </div>
    </div>
  )
}

function Step3({
  form,
  set,
  toggle,
}: {
  form: FormState
  set: (key: keyof FormState, val: unknown) => void
  toggle: (key: keyof FormState, val: boolean) => void
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Warning banner */}
      <div
        style={{
          background: '#FEF3C7',
          border: '1px solid #FDE68A',
          borderRadius: 8,
          padding: '10px 14px',
          display: 'flex',
          gap: 8,
          alignItems: 'flex-start',
        }}
      >
        <span style={{ fontSize: 16, flexShrink: 0 }}>⚠️</span>
        <div>
          <p style={{ fontSize: 13, fontWeight: 600, color: '#92400E', margin: 0 }}>
            Enter names EXACTLY as written on each document
          </p>
          <p style={{ fontSize: 12, color: '#78350F', margin: '4px 0 0' }}>
            One letter difference = application rejected. Check spelling carefully.
          </p>
        </div>
      </div>

      <div>
        <Label
          htmlFor="aadhaar_name"
          style={{ fontWeight: 600, marginBottom: 6, display: 'block' }}
        >
          Name on Aadhaar Card <span style={{ color: '#EF4444' }}>*</span>
        </Label>
        <Input
          id="aadhaar_name"
          value={form.aadhaar_name}
          onChange={(e) => set('aadhaar_name', e.target.value)}
          placeholder="Exactly as printed on Aadhaar"
        />
        <p style={{ fontSize: 11, color: 'var(--muted-foreground)', marginTop: 4 }}>
          🪪 Check your Aadhaar card right now
        </p>
      </div>

      <div>
        <Label htmlFor="bank_name" style={{ fontWeight: 600, marginBottom: 6, display: 'block' }}>
          Name on Bank Passbook / Card <span style={{ color: '#EF4444' }}>*</span>
        </Label>
        <Input
          id="bank_name"
          value={form.bank_name}
          onChange={(e) => set('bank_name', e.target.value)}
          placeholder="Exactly as printed on passbook"
        />
        <p style={{ fontSize: 11, color: 'var(--muted-foreground)', marginTop: 4 }}>
          🏦 Open your bank passbook / check bank card
        </p>
      </div>

      <div>
        <Label htmlFor="voter_name" style={{ fontWeight: 600, marginBottom: 6, display: 'block' }}>
          Name on Voter ID{' '}
          <span style={{ color: 'var(--muted-foreground)', fontWeight: 400, fontSize: 12 }}>
            (optional)
          </span>
        </Label>
        <Input
          id="voter_name"
          value={form.voter_name}
          onChange={(e) => set('voter_name', e.target.value)}
          placeholder="Leave blank if not available"
        />
      </div>

      <div>
        <Label style={{ fontWeight: 600, marginBottom: 10, display: 'block' }}>
          Is your Aadhaar linked to your bank account?
        </Label>
        <div style={{ display: 'flex', gap: 12 }}>
          <PillButton
            label="Yes, linked"
            emoji="🔗"
            selected={form.aadhaar_bank_linked === true}
            onClick={() => set('aadhaar_bank_linked', true)}
          />
          <PillButton
            label="No, not linked"
            emoji="❌"
            selected={form.aadhaar_bank_linked === false}
            onClick={() => set('aadhaar_bank_linked', false)}
          />
        </div>
      </div>
    </div>
  )
}

function Step4({
  form,
  set,
  toggle,
  toggleDoc,
}: {
  form: FormState
  set: (key: keyof FormState, val: unknown) => void
  toggle: (key: keyof FormState, val: boolean) => void
  toggleDoc: (docId: string, present: boolean) => void
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div>
        <Label style={{ fontWeight: 600, marginBottom: 10, display: 'block' }}>
          Any bank transaction in the last 6 months? <span style={{ color: '#EF4444' }}>*</span>
        </Label>
        <div style={{ display: 'flex', gap: 12 }}>
          <PillButton
            label="Yes, active"
            emoji="✅"
            selected={form.bank_active === true}
            onClick={() => toggle('bank_active', true)}
          />
          <PillButton
            label="No, dormant"
            emoji="💤"
            selected={form.bank_active === false}
            onClick={() => toggle('bank_active', false)}
          />
        </div>
      </div>

      {form.bank_active === false && (
        <div>
          <Label style={{ fontWeight: 600, marginBottom: 8, display: 'block' }}>
            Last transaction was approximately:
          </Label>
          <Select
            value={String(form.bank_last_transaction_months_ago || '')}
            onValueChange={(v) => set('bank_last_transaction_months_ago', Number(v))}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select time period" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">7–8 months ago</SelectItem>
              <SelectItem value="10">10–12 months ago</SelectItem>
              <SelectItem value="18">More than 1 year ago</SelectItem>
              <SelectItem value="24">More than 2 years ago</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      <div>
        <Label style={{ fontWeight: 600, marginBottom: 4, display: 'block' }}>
          Which documents do you currently have?
        </Label>
        <p style={{ fontSize: 12, color: 'var(--muted-foreground)', marginBottom: 12 }}>
          Check all that apply — unchecked = missing document
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {ALL_DOCS.map((doc) => {
            const isPresent = form.docs_present.includes(doc.id)
            return (
              <label
                key={doc.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: '10px 14px',
                  borderRadius: 8,
                  border: isPresent ? '1px solid #BBF7D0' : '1px solid var(--border)',
                  background: isPresent ? '#F0FDF4' : 'var(--card)',
                  cursor: 'pointer',
                }}
              >
                <input
                  type="checkbox"
                  checked={isPresent}
                  onChange={(e) => toggleDoc(doc.id, e.target.checked)}
                  style={{ width: 16, height: 16, accentColor: '#22C55E' }}
                />
                <span style={{ fontSize: 14 }}>{doc.label}</span>
                {isPresent ? (
                  <Badge
                    variant="outline"
                    style={{
                      marginLeft: 'auto',
                      color: '#16A34A',
                      borderColor: '#BBF7D0',
                      background: '#F0FDF4',
                      fontSize: 11,
                    }}
                  >
                    ✓ Have it
                  </Badge>
                ) : (
                  <Badge
                    variant="outline"
                    style={{
                      marginLeft: 'auto',
                      color: '#DC2626',
                      borderColor: '#FECACA',
                      background: '#FFF5F5',
                      fontSize: 11,
                    }}
                  >
                    ✗ Missing
                  </Badge>
                )}
              </label>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function LoadingResult() {
  return (
    <div style={{ textAlign: 'center', padding: '40px 0' }}>
      <div style={{ fontSize: 48, marginBottom: 16 }}>🔍</div>
      <p style={{ fontSize: 16, fontWeight: 600 }}>Checking eligibility...</p>
      <p style={{ fontSize: 13, color: 'var(--muted-foreground)', marginTop: 8 }}>
        Comparing your documents with scheme requirements
      </p>
      <div style={{ display: 'flex', justifyContent: 'center', gap: 6, marginTop: 20 }}>
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: '#3B82F6',
              animation: `bounce 1.2s ${i * 0.2}s infinite`,
            }}
          />
        ))}
      </div>
      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
          40% { transform: scale(1.2); opacity: 1; }
        }
      `}</style>
    </div>
  )
}

function ErrorResult({ onRetry }: { onRetry: () => void }) {
  return (
    <div style={{ textAlign: 'center', padding: '40px 0' }}>
      <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
      <p style={{ fontSize: 16, fontWeight: 600 }}>Could not check eligibility</p>
      <p style={{ fontSize: 13, color: 'var(--muted-foreground)', marginTop: 8 }}>
        Please check your internet connection and try again.
      </p>
      <Button onClick={onRetry} style={{ marginTop: 20 }}>
        ← Go back and retry
      </Button>
    </div>
  )
}
