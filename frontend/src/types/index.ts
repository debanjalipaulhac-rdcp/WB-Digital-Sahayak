// Pure types — no imports, no "use client", safe in every context

export type Lang = 'en' | 'bn' | 'hi'
export type Band = 'RED' | 'AMBER' | 'GREEN'
export type ModalName = 'auth' | 'eligibility' | 'voice' | null

// ─── Auth ───────────────────────────────────────────────────────────────────

export interface User {
    phone: string
    name: string | null
    verified: boolean
    has_profile: boolean
}

// ─── Schemes API (/schemes) ──────────────────────────────────────────────────

/** Eligibility block attached to each scheme */
export interface SchemeEligibility {
    age_min?: number | null
    age_max?: number | null
    gender?: 'male' | 'female' | 'all' | null
    state_resident?: boolean
    family_income_max?: number | null
    low_income?: boolean
    family_card_holder?: boolean
    must_be_unemployed?: boolean
    must_be_registered_at_employment_exchange?: boolean
    must_be_enrolled_in_school?: boolean
    must_be_unmarried?: boolean
    not_govt_employee?: boolean
    not_income_tax_payer?: boolean
    not_enrolled_in_other_cash_scheme?: boolean
    caste_note?: string | null
    note_en?: string | null
    note_bn?: string | null
    note_hi?: string | null
}

/** Benefits block */
export interface SchemeBenefits {
    mode?: string
    one_time_grant?: number | null
    monthly_pension?: number | null
    cashless_limit?: number | null
    k1_annual?: number | null
    k2_one_time?: number | null
    general_monthly?: number | null
    sc_st_monthly?: number | null
    graduate_monthly?: number | null
    non_graduate_monthly?: number | null
    duration_max_months?: number | null
    note_en?: string | null
    note_bn?: string | null
    note_hi?: string | null
}

/** Bank / DBT conditions per scheme */
export interface BankConditions {
    account_required: boolean
    aadhaar_linked_required: boolean
    dormant_check: boolean
    dormant_threshold_months?: number | null
    score_deduction_unlinked?: number | null
    score_deduction_dormant?: number | null
    script_code_unlinked?: string | null
    script_code_dormant?: string | null
}

/** Document required for a scheme */
export interface SchemeDocument {
    doc_id: string
    label: string
    label_bn?: string | null
    label_hi?: string | null
    required: boolean
    score_deduction_if_missing?: number | null
    note_en?: string | null
    note_bn?: string | null
    note_hi?: string | null
    where_to_get_en?: string | null
    where_to_get_bn?: string | null
    where_to_get_hi?: string | null
    // legacy alias
    id?: string
    sub?: string
    icon?: string
}

/** Mismatch check between two documents */
export interface MismatchCheck {
    check_id: string
    field: string
    severity: 'FATAL' | 'WARNING'
    score_deduction: number
    script_code?: string | null
    doc_a?: string | null
    doc_b?: string | null
    label_a?: string | null
    label_b?: string | null
    message_en: string
    message_bn?: string | null
    message_hi?: string | null
}

/** Cross-scheme recommendation trigger */
export interface CrossSchemeTrigger {
    condition: string
    suggest_scheme_id: string
    reason_en: string
    reason_bn?: string | null
    reason_hi?: string | null
}

/** Apply location step */
export interface ApplyAt {
    step: number
    office: string
    office_bn?: string | null
}

/** Full scheme object as returned by GET /schemes */
export interface Scheme {
    scheme_id: string
    scheme_name: string
    scheme_name_bn?: string | null
    scheme_name_hi?: string | null
    tag: string
    department?: string | null
    benefit_display: string
    seeded_at?: string | null

    eligibility?: SchemeEligibility | null
    benefits?: SchemeBenefits | null
    bank_conditions?: BankConditions | null
    documents?: SchemeDocument[]
    mismatch_checks?: MismatchCheck[]
    cross_scheme_triggers?: CrossSchemeTrigger[]
    apply_at?: ApplyAt[]

    // UI helpers (may be absent from API, set locally for display)
    icon?: string
    accent_color?: string
    description?: string

    // Legacy fields from older mock data (keep for backward compat)
    dept?: string
    dept_name?: string
    slug?: string
    name?: string
}

// ─── API List Responses ──────────────────────────────────────────────────────

export interface SchemesListResponse {
    schemes: Scheme[]
    total: number
    page: number
    pages: number
}

export interface RecommendationsResponse {
    schemes: Scheme[]
    mode: 'profile' | 'context' | 'query' | 'featured'
    personalised: boolean
}

// ─── Eligibility ─────────────────────────────────────────────────────────────

export interface EligibilityIssue {
    type: 'fatal' | 'warning' | 'ineligible'
    code: string
    message: string
    score_deduction: number
    script_code?: string
    script_available?: boolean
    display?: {
        field_a: string
        label_a: string
        field_b: string
        label_b: string
        similarity_score?: number
    }
}

export interface EligibilityResult {
    scheme_id: string
    scheme_name: string
    scheme_name_bn: string
    score: number
    band: Band
    band_label: string
    band_label_bn: string
    eligible_basic: boolean
    benefit_amount?: number | null
    issues: EligibilityIssue[]
    warnings: EligibilityIssue[]
    roadmap: Array<{
        step: number
        action: string
        action_bn?: string
        location?: string
        done: boolean
    }>
    recommendations: Scheme[]
    score_breakdown: Record<string, number>
}

export interface EligibilityCheckBody {
    scheme_id: string
    profile: Record<string, unknown>
    checks?: Record<string, unknown>
    lang?: Lang
    save?: boolean
}

// ─── Profile ─────────────────────────────────────────────────────────────────

export interface ProfileData {
    phone: string
    name?: string | null
    age?: number
    gender?: string
    caste?: string
    district?: string
    is_govt_employee?: boolean
    pays_income_tax?: boolean
    has_daughter?: boolean
    has_school_child?: boolean
    annual_income_bracket?: string
    verified: boolean
    completed: boolean
    updated_at?: number
}

export interface ApplicationRecord {
    scheme_id: string
    scheme_name: string
    score: number
    band: Band
    eligible: boolean
    checked_at: number
}

// ─── Script ──────────────────────────────────────────────────────────────────

export interface ScriptResponse {
    issue_code: string
    where: string
    form: string
    script: string
    audio_url?: string | null
}
