import { getRecommendations } from '@/lib/server/api'
import SchemeCard from '@/components/SchemeCard'
import { Sparkles } from 'lucide-react'

export default async function RecommendationsSlot() {
  const data = await getRecommendations().catch(() => null)
  const schemes = data?.schemes || []

  if (schemes.length === 0) return null

  return (
    <section className="pt-7 px-5 max-w-6xl mx-auto">
      <div className="flex items-center gap-2 mb-4">
        <Sparkles size={16} className="text-blue-600" />
        <h2 className="text-base font-semibold text-blue-600 uppercase tracking-wide">
          Recommended for You
        </h2>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {schemes.map((scheme) => (
          <SchemeCard key={scheme.scheme_id} scheme={scheme} />
        ))}
      </div>
    </section>
  )
}