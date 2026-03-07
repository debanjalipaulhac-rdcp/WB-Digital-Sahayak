'use client'

import { useState, useEffect } from 'react'
import { Save, Loader2, CheckCircle } from 'lucide-react'
import { profile } from '@/lib/client/api'
import type { ProfileData } from '@/types'

export default function ProfileForm() {
  const [formData, setFormData] = useState<Partial<ProfileData>>({})
  const [initialData, setInitialData] = useState<ProfileData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)

  // Load profile data on mount
  useEffect(() => {
    const loadProfile = async () => {
      try {
        const data = await profile.getProfile()
        setInitialData(data)
        setFormData({
          name: data.name || '',
          age: data.age || undefined,
          gender: data.gender || '',
          caste: data.caste || '',
          district: data.district || '',
          is_govt_employee: data.is_govt_employee || false,
          pays_income_tax: data.pays_income_tax || false,
          has_daughter: data.has_daughter || false,
          has_school_child: data.has_school_child || false,
          is_enrolled_in_school: data.is_enrolled_in_school || false,
          is_unemployed: data.is_unemployed || true,
          annual_income_bracket: data.annual_income_bracket || '',
        })
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load profile')
      } finally {
        setIsLoading(false)
      }
    }

    loadProfile()
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSaving(true)
    setSaveStatus('idle')
    setError(null)

    try {
      await profile.saveProfile(formData)
      setSaveStatus('success')
      setTimeout(() => setSaveStatus('idle'), 3000)
    } catch (err) {
      setSaveStatus('error')
      setError(err instanceof Error ? err.message : 'Failed to save profile')
    } finally {
      setIsSaving(false)
    }
  }

  const handleInputChange = (field: keyof ProfileData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  if (isLoading) {
    return <ProfileFormSkeleton />
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <form onSubmit={handleSubmit} className="space-y-6">
        
        {/* Basic Information */}
        <section>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Basic Information</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Full Name *
              </label>
              <input
                type="text"
                value={formData.name || ''}
                onChange={(e) => handleInputChange('name', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Age *
              </label>
              <input
                type="number"
                min="1"
                max="120"
                value={formData.age || ''}
                onChange={(e) => handleInputChange('age', parseInt(e.target.value) || undefined)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Gender *
              </label>
              <select
                value={formData.gender || ''}
                onChange={(e) => handleInputChange('gender', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              >
                <option value="">Select Gender</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                District
              </label>
              <input
                type="text"
                value={formData.district || ''}
                onChange={(e) => handleInputChange('district', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., Kolkata, Howrah"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Caste Category
              </label>
              <select
                value={formData.caste || ''}
                onChange={(e) => handleInputChange('caste', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select Category</option>
                <option value="general">General</option>
                <option value="obc">OBC</option>
                <option value="sc">SC</option>
                <option value="st">ST</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Annual Income Bracket
              </label>
              <select
                value={formData.annual_income_bracket || ''}
                onChange={(e) => handleInputChange('annual_income_bracket', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select Income Range</option>
                <option value="below-1-lakh">Below ₹1 Lakh</option>
                <option value="1-2-lakh">₹1-2 Lakh</option>
                <option value="2-5-lakh">₹2-5 Lakh</option>
                <option value="5-10-lakh">₹5-10 Lakh</option>
                <option value="above-10-lakh">Above ₹10 Lakh</option>
              </select>
            </div>
          </div>
        </section>

        {/* Employment & Family */}
        <section>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Employment & Family</h3>
          
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="is_govt_employee"
                checked={formData.is_govt_employee || false}
                onChange={(e) => handleInputChange('is_govt_employee', e.target.checked)}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <label htmlFor="is_govt_employee" className="text-sm text-gray-700">
                I am a government employee
              </label>
            </div>

            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="pays_income_tax"
                checked={formData.pays_income_tax || false}
                onChange={(e) => handleInputChange('pays_income_tax', e.target.checked)}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <label htmlFor="pays_income_tax" className="text-sm text-gray-700">
                I pay income tax
              </label>
            </div>

            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="is_unemployed"
                checked={formData.is_unemployed || false}
                onChange={(e) => handleInputChange('is_unemployed', e.target.checked)}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <label htmlFor="is_unemployed" className="text-sm text-gray-700">
                I am currently unemployed
              </label>
            </div>

            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="has_daughter"
                checked={formData.has_daughter || false}
                onChange={(e) => handleInputChange('has_daughter', e.target.checked)}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <label htmlFor="has_daughter" className="text-sm text-gray-700">
                I have a daughter
              </label>
            </div>

            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="has_school_child"
                checked={formData.has_school_child || false}
                onChange={(e) => handleInputChange('has_school_child', e.target.checked)}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <label htmlFor="has_school_child" className="text-sm text-gray-700">
                I have a school-going child
              </label>
            </div>

            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="is_enrolled_in_school"
                checked={formData.is_enrolled_in_school || false}
                onChange={(e) => handleInputChange('is_enrolled_in_school', e.target.checked)}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <label htmlFor="is_enrolled_in_school" className="text-sm text-gray-700">
                I am currently enrolled in school/college
              </label>
            </div>
          </div>
        </section>

        {/* Error Display */}
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {/* Submit Button */}
        <div className="flex items-center justify-between pt-4 border-t border-gray-200">
          <div className="flex items-center gap-2">
            {saveStatus === 'success' && (
              <>
                <CheckCircle className="text-green-600" size={16} />
                <span className="text-sm text-green-600">Profile saved successfully!</span>
              </>
            )}
          </div>
          
          <button
            type="submit"
            disabled={isSaving}
            className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSaving ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save size={16} />
                Save Profile
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  )
}

function ProfileFormSkeleton() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="space-y-6">
        <div>
          <div className="h-5 bg-gray-200 rounded w-32 mb-4 animate-pulse"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i}>
                <div className="h-4 bg-gray-200 rounded w-24 mb-2 animate-pulse"></div>
                <div className="h-10 bg-gray-200 rounded animate-pulse"></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}