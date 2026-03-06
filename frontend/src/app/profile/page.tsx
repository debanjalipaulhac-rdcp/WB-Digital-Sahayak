// SERVER COMPONENT — middleware already guards this route
// Fetches profile data with the HttpOnly auth cookie, passes to form as props
import { getProfile } from '@/lib/server/api'
import { ProfileFormClient } from '@/components/ProfileFormClient'
import type { Metadata } from 'next'

export const metadata: Metadata = {
    title: 'My Profile | WB Digital Sahayak',
    description: 'Update your personal details to get personalised scheme recommendations.',
}

export default async function ProfilePage() {
    // Profile fetched server-side — no useEffect, no loading state in the form
    const profile = await getProfile()

    return (
        <div style={{ background: 'var(--color-bg)', minHeight: '100vh', paddingBottom: 80 }}>
            <div style={{ maxWidth: 860, margin: '0 auto', padding: '32px 20px' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12, marginBottom: 28 }}>
                    <div>
                        <h1 style={{ fontWeight: 700, fontSize: 32, color: 'var(--color-text)', margin: '0 0 6px' }}>
                            Personal Details
                        </h1>
                        <p style={{ fontSize: 14, color: 'var(--color-muted)', margin: 0 }}>
                            Ensure your information is up to date to find the best schemes for you.
                        </p>
                    </div>
                    {profile?.verified && (
                        <div style={{
                            display: 'flex', alignItems: 'center', gap: 6,
                            background: '#F0FDF4', border: '1.5px solid #D1FAE5',
                            borderRadius: 999, padding: '8px 16px',
                        }}>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#057A55" strokeWidth="2">
                                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                            </svg>
                            <span style={{ fontSize: 13, fontWeight: 500, color: '#057A55' }}>KYC Verified</span>
                        </div>
                    )}
                </div>

                {/* Pass server-fetched profile as initial values — no client-side fetching */}
                <ProfileFormClient initialProfile={profile} />
            </div>
        </div>
    )
}
