const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface EligibilityItem {
    label: string
    sub: string
}

export interface DocumentItem {
    id: string
    label: string
    sub: string
    icon: string
}

export interface Mismatch {
    exists: boolean
    aadhaar_name: string
    bank_name: string
}

export interface Scheme {
    slug: string
    name: string
    nameTag: string
    icon: string
    dept: string
    desc: string
}

export interface SchemeDetail {
    slug: string
    name: string
    name_bn?: string
    dept: string
    status: string
    benefit_display?: string
    asset?: string
    impact?: string
    description: string
    eligibility: EligibilityItem[]
    documents: DocumentItem[]
    mismatch?: Mismatch
}

const MOCK_SCHEMES: Scheme[] = [
    {
        slug: 'sabuj-sathi',
        name: 'Sabuj Sathi',
        nameTag: 'SCHEME',
        icon: 'Bike',
        dept: 'Dept. of Backward Classes',
        desc: 'Bicycle distribution scheme for students in classes IX to XII to encourage higher education.',
    },
    {
        slug: 'medhashree',
        name: 'Medhashree',
        nameTag: 'SCHOLARSHIP',
        icon: 'GraduationCap',
        dept: 'Backward Classes Welfare',
        desc: 'Pre-matric scholarship for OBC students in West Bengal to support their educational journey.',
    },
    {
        slug: 'svmcm',
        name: 'SVMCM',
        nameTag: 'MERIT-CUM-MEANS',
        icon: 'Award',
        dept: 'Higher Education Dept.',
        desc: 'Swami Vivekananda Merit-cum-Means Scholarship for meritorious students from economically weaker sections.',
    },
]

const MOCK_SCHEME_DETAIL: SchemeDetail = {
    slug: 'sabuj-sathi',
    name: 'Sabuj Sathi',
    name_bn: 'সবুজ সাথী',
    dept: 'Department of Backward Classes Welfare',
    status: 'active',
    benefit_display: 'Free Bicycle',
    asset: 'Free Bicycle',
    impact: 'Reduce Dropouts',
    description:
        'Under this scheme, bicycles are distributed to students of class IX to XII in Government, Government-aided and Government-sponsored schools to increase retention in schools.',
    eligibility: [
        { label: 'Resident of West Bengal', sub: 'Must have permanent address in WB' },
        { label: 'Student of Class IX-XII', sub: 'Currently enrolled' },
        { label: 'Govt/Aided School', sub: 'Private schools not eligible' },
        { label: 'First Time Applicant', sub: 'Not received bicycle earlier' },
    ],
    documents: [
        { id: 'aadhaar', label: 'Aadhaar Card', sub: 'Proof of Identity', icon: 'FileText' },
        { id: 'student_id', label: 'Student ID / Certificate', sub: 'Proof of Enrollment', icon: 'GraduationCap' },
        { id: 'bank_passbook', label: 'Bank Passbook', sub: 'Front page with IFSC', icon: 'CreditCard' },
    ],
    mismatch: {
        exists: true,
        aadhaar_name: 'RAHUL K. ROY',
        bank_name: 'RAHUL KUMAR ROY',
    },
}

export async function getSchemes(): Promise<{ schemes: Scheme[] }> {
    try {
        const res = await fetch(`${BASE}/schemes`, { next: { revalidate: 300 } })
        if (!res.ok) throw new Error('API failed')
        return res.json()
    } catch {
        return { schemes: MOCK_SCHEMES }
    }
}

export async function getScheme(slug: string): Promise<SchemeDetail | null> {
    try {
        const res = await fetch(`${BASE}/scheme/${slug}`, { next: { revalidate: 300 } })
        if (!res.ok) return null
        return res.json()
    } catch {
        return MOCK_SCHEME_DETAIL
    }
}
