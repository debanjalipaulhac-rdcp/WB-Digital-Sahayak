// PARALLEL ROUTE — SSR, no "use client"
import { Suspense } from 'react'
import { getRecommendations } from '@/lib/server/api'
import SchemeCard from '@/components/SchemeCard'

export default async function RecommendationsSlot() {
  return (
    <Suspense fallback={<RecommendationsSkeleton />}>
      <RecommendationsContent />
    </Suspense>
  )
}

async function RecommendationsContent() {
  const data = await getRecommendations({ limit: 6 })
  const schemes = data?.schemes || []

  if (schemes.length === 0) {
    return null
  }

  return (
    <section className="pt-10 pb-5 px-5 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-xl font-bold text-gray-900 border-l-4 border-green-600 pl-3 leading-snug">
          {data.personalised ? 'Recommended for You' : 'Popular Schemes'}
        </h2>
      </div>

      <div className="scheme-cards-scroll">
        {schemes.map((scheme) => (
          <SchemeCard key={scheme.scheme_id} scheme={scheme} />
        ))}
      </div>
    </section>
  )
}

function RecommendationsSkeleton() {
  return (
    <section className="pt-10 pb-5 px-5 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-5">
        <div className="h-6 bg-gray-200 rounded w-48 animate-pulse"></div>
      </div>
      <div className="scheme-cards-scroll">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="bg-white border border-gray-200 rounded-xl p-5 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
            <div className="h-3 bg-gray-200 rounded w-1/2 mb-3"></div>
            <div className="h-3 bg-gray-200 rounded w-full mb-2"></div>
            <div className="h-3 bg-gray-200 rounded w-2/3"></div>
          </div>
        ))}
      </div>
    </section>
  )
}