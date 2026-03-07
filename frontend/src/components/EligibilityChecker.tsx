'use client'

import { useState } from 'react'
import { CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { eligibilityClient } from '@/lib/client/api'
import type { EligibilityCheckBody, EligibilityResult } from '@/types'

interface EligibilityCheckerProps {
  schemeId: string
}

export default function EligibilityChecker({ schemeId }: EligibilityCheckerProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<EligibilityResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleQuickCheck = async () => {
    setIsLoading(true)
    setError(null)

    try {
      // Basic eligibility check with minimal profile data
      const request: EligibilityCheckBody = {
        scheme_id: schemeId,
        profile: {
          age: 25, // Default values for quick check
          gender: 'female',
          is_govt_employee: false,
          pays_income_tax: false,
          is_unemployed: true,
        },
        lang: 'en',
        save: false, // Don't save quick checks
      }

      const eligibilityResult = await eligibilityClient.check(request)
      setResult(eligibilityResult)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to check eligibility')
    } finally {
      setIsLoading(false)
    }
  }

  const getBandColor = (band: string) => {
    switch (band.toLowerCase()) {
      case 'green': return 'text-green-600 bg-green-50 border-green-200'
      case 'amber': return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      case 'red': return 'text-red-600 bg-red-50 border-red-200'
      default: return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Quick Eligibility Check
      </h3>

      {!result && !error && (
        <div className="text-center">
          <p className="text-sm text-gray-600 mb-4">
            Get a quick assessment of your eligibility for this scheme.
          </p>
          <button
            onClick={handleQuickCheck}
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Checking...
              </>
            ) : (
              <>
                <CheckCircle size={16} />
                Check Eligibility
              </>
            )}
          </button>
        </div>
      )}

      {error && (
        <div className="text-center">
          <div className="flex items-center justify-center gap-2 text-red-600 mb-3">
            <AlertCircle size={16} />
            <span className="text-sm font-medium">Check Failed</span>
          </div>
          <p className="text-sm text-gray-600 mb-4">{error}</p>
          <button
            onClick={handleQuickCheck}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
          >
            Try Again
          </button>
        </div>
      )}

      {result && (
        <div className="space-y-4">
          <div className="text-center">
            <div className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg border text-sm font-medium ${getBandColor(result.band)}`}>
              {result.band === 'GREEN' && <CheckCircle size={16} />}
              {result.band === 'AMBER' && <AlertCircle size={16} />}
              {result.band === 'RED' && <AlertCircle size={16} />}
              Score: {result.score}%
            </div>
          </div>

          <div className="text-center">
            <p className="text-sm text-gray-600">
              {result.eligible_basic 
                ? 'You may be eligible for this scheme!' 
                : 'You may not meet all requirements.'}
            </p>
          </div>

          {result.issues && result.issues.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-gray-900">Issues to Address:</h4>
              {result.issues.slice(0, 3).map((issue, index) => (
                <div key={index} className="text-xs text-gray-600 p-2 bg-gray-50 rounded">
                  {issue.message}
                </div>
              ))}
            </div>
          )}

          <div className="pt-3 border-t border-gray-100">
            <a
              href="/profile"
              className="w-full block text-center px-4 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-200 transition-colors"
            >
              Complete Profile for Accurate Results
            </a>
          </div>
        </div>
      )}
    </div>
  )
}