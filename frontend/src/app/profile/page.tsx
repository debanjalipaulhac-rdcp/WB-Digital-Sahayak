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
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-4xl mx-auto px-5 py-8">
                <div className="flex items-start justify-between flex-wrap gap-3 mb-7">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900 mb-2">
                            Personal Details
                        </h1>
                        <p className="text-sm text-gray-600">
                            Ensure your information is up to date to find the best schemes for you.
                        </p>
                    </div>
                    {profile?.completed && (
                        <div className="flex items-center gap-2 bg-green-50 border border-green-200 rounded-full px-4 py-2">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="2">
                                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                            </svg>
                            <span className="text-sm font-medium text-green-700">Profile Complete</span>
                        </div>
                    )}
                </div>

                {/* Pass server-fetched profile as initial values — no client-side fetching */}
                <ProfileFormClient initialProfile={profile} />
            </div>
        </div>
    )
}
