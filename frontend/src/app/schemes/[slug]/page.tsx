import { Suspense } from 'react'
import { notFound } from 'next/navigation'
import { ArrowLeft, CheckCircle, FileText, Users } from 'lucide-react'
import { getSchemeById, getRecommendations } from '@/lib/server/api'
import type { Scheme } from '@/types'
import SchemeCard from '@/components/SchemeCard'
import { SchemeDetailActions } from '@/components/SchemeDetailActions'

interface SchemePageProps {
  params: Promise<{ slug: string }>
}

export async function generateMetadata({ params }: SchemePageProps) {
  const { slug } = await params
  console.log(slug)
  const scheme = await getSchemeById(slug)
  
  if (!scheme) {
    return {
      title: 'Scheme Not Found | WB Digital Sahayak',
    }
  }

  return {
    title: `${scheme.scheme_name} | WB Digital Sahayak`,
    description: scheme.scheme_name_bn || scheme.scheme_name,
  }
}

export default async function SchemePage({ params }: SchemePageProps) {
  const { slug } = await params
  const scheme = await getSchemeById(slug)

  if (!scheme) {
    notFound()
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <section className="bg-muted/60 border-b ">
        <div className="max-w-4xl mx-auto px-5 py-6">
          <a 
            href="/schemes" 
            className="inline-flex items-center gap-2 text-sm text-accent-foreground hover:text-blue-600 mb-4"
          >
            <ArrowLeft size={16} />
            Back to All Schemes
          </a>
          
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-secondary rounded-xl flex items-center justify-center">
              <FileText className="text-foreground" size={24} />
            </div>
            
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <span className="px-2 py-1 bg-primary-foreground text-primary text-xs font-medium rounded">
                  {scheme.tag?.toUpperCase() || 'SCHEME'}
                </span>
              </div>
              
              <h1 className="text-2xl font-bold mb-2">
                {scheme.scheme_name}
                {scheme.scheme_name_bn && (
                  <span className="block text-lg font-normal text-muted-foreground/80 mt-1">
                    {scheme.scheme_name_bn}
                  </span>
                )}
              </h1>
              
              {scheme.description && (
                <p className="text-muted-foreground/80 mb-3">{scheme.description}</p>
              )}
              
              <div className="flex items-center gap-4 text-sm text-muted-foreground/90">
                {scheme.department && (
                  <div className="flex items-center gap-1">
                    <FileText size={14} />
                    {scheme.department}
                  </div>
                )}
                {scheme.benefit_display && (
                  <div className="flex items-center gap-1">
                    <CheckCircle size={14} />
                    {scheme.benefit_display}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="max-w-4xl mx-auto px-5 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-8">
            
            {/* Eligibility Rules */}
            {scheme.eligibility && (
              <section className="bg-card rounded-xl border p-6">
                <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <CheckCircle className="text-green-600" size={20} />
                  Eligibility Criteria
                </h2>
                
                <div className="space-y-3 text-sm">
                  {scheme.eligibility.age_min && scheme.eligibility.age_max && (
                    <div className="flex items-start gap-3 p-3 bg-secondary rounded-lg">
                      <CheckCircle className="text-green-500 mt-0.5 shrink-0" size={16} />
                      <div>Age: {scheme.eligibility.age_min} - {scheme.eligibility.age_max} years</div>
                    </div>
                  )}
                  {scheme.eligibility.gender && scheme.eligibility.gender !== 'all' && (
                    <div className="flex items-start gap-3 p-3 bg-secondary rounded-lg">
                      <CheckCircle className="text-green-500 mt-0.5 shrink-0" size={16} />
                      <div>Gender: {scheme.eligibility.gender}</div>
                    </div>
                  )}
                  {scheme.eligibility.note_en && (
                    <div className="flex items-start gap-3 p-3 bg-secondary rounded-lg">
                      <FileText className="text-blue-500 mt-0.5 shrink-0" size={16} />
                      <div>{scheme.eligibility.note_en}</div>
                    </div>
                  )}
                </div>
              </section>
            )}

            {/* Required Documents */}
            {scheme.documents && scheme.documents.length > 0 && (
              <section className="bg-card rounded-xl border  p-6">
                <h2 className="text-lg font-semibold  mb-4 flex items-center gap-2">
                  <FileText className="text-blue-600" size={20} />
                  Required Documents
                </h2>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {scheme.documents.map((doc, index) => (
                    <div key={index} className="flex items-start gap-3 p-3  rounded-lg bg-secondary">
                      <div className={`w-2 h-2 rounded-full mt-2 shrink-0 ${
                        doc.required ? 'bg-red-500' : 'bg-yellow-500'
                      }`} />
                      <div>
                        <div className="font-medium">{doc.label}</div>
                        {doc.note_en && (
                          <div className="text-sm  text-muted-foreground">{doc.note_en}</div>
                        )}
                        <div className={`text-xs mt-1 ${
                          doc.required ? 'text-red-600' : 'text-yellow-600'
                        }`}>
                          {doc.required ? 'Mandatory' : 'Optional'}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Benefits */}
            {scheme.benefits && (
              <section className="bg-card rounded-xl border p-6">
                <h2 className="text-lg font-semibold mb-4">
                  Benefits
                </h2>
                
                <div className="space-y-2 text-sm text-accent-foreground/80">
                  {scheme.benefits.one_time_grant && (
                    <div>One-time grant: ₹{scheme.benefits.one_time_grant.toLocaleString('en-IN')}</div>
                  )}
                  {scheme.benefits.monthly_pension && (
                    <div>Monthly pension: ₹{scheme.benefits.monthly_pension.toLocaleString('en-IN')}</div>
                  )}
                  {scheme.benefits.note_en && (
                    <div className="mt-2 p-3 bg-secondary rounded-lg">{scheme.benefits.note_en}</div>
                  )}
                </div>
              </section>
            )}

            {/* Action Buttons */}
            <SchemeDetailActions
              schemeId={scheme.scheme_id}
              schemeName={scheme.scheme_name}
            />

            {/* Application Steps */}
            {scheme.apply_at && scheme.apply_at.length > 0 && (
              <section className="bg-card rounded-xl border p-6">
                <h2 className="text-lg font-semibold mb-4">
                  How to Apply
                </h2>
                
                <div className="space-y-3">
                  {scheme.apply_at.map((step, index) => (
                    <div key={index} className="flex items-start gap-3">
                      <div className="w-6 h-6 bg-purple-100 text-purple-600 rounded-full flex items-center justify-center text-sm font-medium shrink-0">
                        {step.step}
                      </div>
                      <div className="text-accent-foreground">{step.office}</div>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Related Schemes */}
            <Suspense fallback={<RelatedSchemesSkeleton />}>
              <RelatedSchemes currentSchemeId={scheme.scheme_id} />
            </Suspense>
          </div>
        </div>
      </div>
    </div>
  )
}

async function RelatedSchemes({ currentSchemeId }: { currentSchemeId: string }) {
  const data = await getRecommendations({ 
    scheme_id: currentSchemeId, 
    limit: 3 
  })
  
  const relatedSchemes = data?.schemes?.filter(
    (scheme: Scheme) => scheme.scheme_id !== currentSchemeId
  ) || []

  if (relatedSchemes.length === 0) {
    return null
  }

  return (
    <section className="bg-card rounded-xl border p-6">
      <h3 className="text-lg font-semibold mb-4">
        Related Schemes
      </h3>
      
      <div className="space-y-4">
        {relatedSchemes.map((scheme: Scheme) => (
          <div key={scheme.scheme_id} className="border rounded-lg p-3">
            <a 
              href={`/schemes/${scheme.scheme_id}`}
              className="block hover:text-blue-600 transition-colors"
            >
              <div className="font-medium text-sm mb-1">{scheme.scheme_name}</div>
              <div className="text-xs text-gray-600 line-clamp-2">
                {scheme.scheme_name_bn || scheme.description}
              </div>
            </a>
          </div>
        ))}
      </div>
    </section>
  )
}

function RelatedSchemesSkeleton() {
  return (
    <section className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="h-5 bg-gray-200 rounded w-32 mb-4 animate-pulse"></div>
      <div className="space-y-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="border border-gray-100 rounded-lg p-3">
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2 animate-pulse"></div>
            <div className="h-3 bg-gray-200 rounded w-full animate-pulse"></div>
          </div>
        ))}
      </div>
    </section>
  )
}