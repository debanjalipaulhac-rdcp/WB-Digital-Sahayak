'use client'

import { useState, useEffect } from 'react'
import { Calendar, CheckCircle, AlertCircle, XCircle } from 'lucide-react'
import { schemes } from '@/lib/client/api'
import type { ApplicationRecord } from '@/types'

interface ApplicationHistoryProps {
  limit?: number
}

export default function ApplicationHistory({ limit = 10 }: ApplicationHistoryProps) {
  const [applications, setApplications] = useState<ApplicationRecord[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadApplications = async () => {
      try {
        const data = await schemes.getApplications(limit)
        setApplications(data.applications)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load applications')
      } finally {
        setIsLoading(false)
      }
    }

    loadApplications()
  }, [limit])

  const getBandIcon = (band: string) => {
    switch (band.toLowerCase()) {
      case 'green': return <CheckCircle className="text-green-500" size={16} />
      case 'amber': return <AlertCircle className="text-yellow-500" size={16} />
      case 'red': return <XCircle className="text-red-500" size={16} />
      default: return <AlertCircle className="text-gray-500" size={16} />
    }
  }

  const getBandColor = (band: string) => {
    switch (band.toLowerCase()) {
      case 'green': return 'text-green-600 bg-green-50'
      case 'amber': return 'text-yellow-600 bg-yellow-50'
      case 'red': return 'text-red-600 bg-red-50'
      default: return 'text-gray-600 bg-gray-50'
    }
  }

  if (isLoading) {
    return <ApplicationHistorySkeleton />
  }

  if (error) {
    return (
      <div className="text-center py-4">
        <p className="text-sm text-red-600">{error}</p>
      </div>
    )
  }

  if (applications.length === 0) {
    return (
      <div className="text-center py-6">
        <div className="text-gray-400 mb-2">
          <Calendar size={24} className="mx-auto" />
        </div>
        <p className="text-sm text-gray-600">No applications yet</p>
        <p className="text-xs text-gray-500">Check your eligibility for schemes to get started</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {applications.map((app, index) => (
        <div key={index} className="p-3 border border-gray-100 rounded-lg hover:bg-gray-50 transition-colors">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-medium text-gray-900 truncate">
                {app.scheme_name}
              </h4>
              <div className="flex items-center gap-2 mt-1">
                {getBandIcon(app.band)}
                <span className={`text-xs px-2 py-1 rounded-full ${getBandColor(app.band)}`}>
                  {app.score}% Score
                </span>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {new Date(app.checked_at).toLocaleDateString('en-IN', {
                  day: 'numeric',
                  month: 'short',
                  year: 'numeric'
                })}
              </p>
            </div>
            
            <div className="text-right">
              <div className={`text-xs font-medium ${
                app.eligible ? 'text-green-600' : 'text-red-600'
              }`}>
                {app.eligible ? 'Eligible' : 'Not Eligible'}
              </div>
            </div>
          </div>
        </div>
      ))}
      
      {applications.length >= limit && (
        <div className="text-center pt-2">
          <a 
            href="/profile/applications" 
            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
          >
            View All Applications →
          </a>
        </div>
      )}
    </div>
  )
}

function ApplicationHistorySkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="p-3 border border-gray-100 rounded-lg">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1">
              <div className="h-4 bg-gray-200 rounded w-3/4 mb-2 animate-pulse"></div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-gray-200 rounded animate-pulse"></div>
                <div className="h-3 bg-gray-200 rounded w-16 animate-pulse"></div>
              </div>
              <div className="h-3 bg-gray-200 rounded w-20 mt-1 animate-pulse"></div>
            </div>
            <div className="h-3 bg-gray-200 rounded w-12 animate-pulse"></div>
          </div>
        </div>
      ))}
    </div>
  )
}