'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import SchemeCard from '@/components/SchemeCard'
import type { Scheme } from '@/types'
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from '@/lib/utils'
import SchemeCard2 from './SchemeCard2'
const GENDERS = [
  { value: 'female', label: 'Female', emoji: '👩' },
  { value: 'male', label: 'Male', emoji: '👨' },
]

const CASTES = [
  { value: 'sc', label: 'SC' },
  { value: 'st', label: 'ST' },
  { value: 'obc', label: 'OBC' },
  { value: 'general', label: 'General' },
]

const AGE_GROUPS = [
  { value: '22', label: '18–25', min: 18, max: 25 },
  { value: '32', label: '26–40', min: 26, max: 40 },
  { value: '50', label: '41–60', min: 41, max: 60 },
  { value: '65', label: '60+', min: 60, max: 100 },
]

export function QuickEligibilityFilter() {
  const router = useRouter()
  const [gender, setGender] = useState<string>('')
  const [caste, setCaste] = useState<string>('')
  const [age, setAge] = useState<string>('')
  const [schemes, setSchemes] = useState<Scheme[]>([])
  const [loading, setLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)

  // Fetch recommendations whenever any filter changes
  const fetchRecs = useCallback(async () => {
    if (!gender && !caste && !age) return // nothing selected yet

    setLoading(true)
    setHasSearched(true)

    try {
      const params = new URLSearchParams({ limit: '6' })
      if (gender) params.set('gender', gender)
      if (caste) params.set('caste', caste)
      if (age) params.set('age', age)

      // Goes through the /api proxy → backend /recommendations
      const res = await fetch(`/api/recommendations?${params}`, {
        credentials: 'include',
      })

      if (!res.ok) throw new Error('fetch failed')

      const data = (await res.json()) as { schemes: Scheme[]; mode: string }
      setSchemes(data.schemes ?? [])
    } catch {
      setSchemes([])
    } finally {
      setLoading(false)
    }
  }, [gender, caste, age])

  useEffect(() => {
    fetchRecs()
  }, [fetchRecs])

  const handleSeeAll = () => {
    const params = new URLSearchParams()
    if (gender) params.set('gender', gender)
    if (caste) params.set('category', caste.toUpperCase())
    router.push(`/schemes?${params}`)
  }

  return (
    <div className="py-8">
      <div className="flex justify-between items-center">
        {/* Section header */}
        <div className="flex items-center gap-2 mb-5 flex-wrap">
          <span className="text-lg">🎯</span>
          <div>
            <h2 className="text-base font-bold m-0">FIND SCHEMES FOR YOU</h2>
            <p className="text-xs text-muted-foreground m-0">
              Select your details — see matching schemes instantly
            </p>
          </div>
        </div>

        {/* Filter pills row */}
        <div className="flex gap-4 mb-6">
          {/* Gender */}
          <div className='flex-wrap'>
            <p className="text-xs font-semibold text-muted-foreground mb-2 uppercase tracking-wider">
              Gender
            </p>
            <Select onValueChange={(e) => setGender((prev) => (prev === e ? '' : e))}>
              <SelectTrigger className="w-[120px]">
                <SelectValue placeholder="Gender" />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  {GENDERS.map((g) => (
                    <SelectItem value={g.value} key={g.value}>
                      {g.label}
                    </SelectItem>
                  ))}

                </SelectGroup>
              </SelectContent>
            </Select>
          </div>

          {/* Caste */}
          <div className='flex-wrap'>
            <p className="text-xs font-semibold text-muted-foreground mb-2 uppercase tracking-wider">
              Social Category
            </p>
            <Select onValueChange={(e) => setCaste((prev) => (prev === e ? '' : e))}>
              <SelectTrigger className="w-[120px]">
                <SelectValue placeholder="Cast" />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  {CASTES.map((g) => (
                    <SelectItem value={g.value} key={g.value}>
                      {g.label}
                    </SelectItem>
                  ))}

                </SelectGroup>
              </SelectContent>
            </Select>
          </div>

          {/* Age group */}
          <div className='flex-wrap'>
            <p className="text-xs font-semibold text-muted-foreground mb-2 uppercase tracking-wider">
              Age Group
            </p>
            <div className="flex gap-2 flex-wrap">
              <RadioGroup defaultValue={age} onValueChange={(a) => setAge((prev) => (prev === a ? '' : a))} className='flex gap-4'>
                {AGE_GROUPS.map((a) => (
                  <label className={cn("flex items-center border rounded-full p-2 py-1.5 cursor-pointer", age === a.value && "border-blue-600 bg-secondary text-blue-800 font-semibold")} htmlFor={a.value} key={a.value}>
                    <RadioGroupItem value={a.value} id={a.value} className='cursor-pointer' />
                    <Label htmlFor={a.value} className='pl-3 cursor-pointer text-sm'>{a.label}</Label>
                  </label>
                ))}
              </RadioGroup>
            </div>
          </div>
        </div>
      </div>
      {/* Results */}
      {!hasSearched && (
        <div className="text-center py-8 px-4 border border-dashed border-border rounded-xl text-muted-foreground text-sm">
          👆 Select your gender or category above to see matching schemes
        </div>
      )}

      {hasSearched && loading && (
        <div className="text-center py-8 text-muted-foreground">
          <div className="text-2xl mb-2">🔍</div>
          Finding schemes for you...
        </div>
      )}

      {hasSearched && !loading && schemes.length === 0 && (
        <div className="text-center py-8 px-4 border border-border rounded-xl text-muted-foreground text-sm">
          No schemes found for this combination. Try changing the filters.
        </div>
      )}

      {hasSearched && !loading && schemes.length > 0 && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-5">
            {schemes.slice(0, 6).map((s) => (
              <SchemeCard2 key={s.scheme_id} scheme={s} />
            ))}
          </div>
          <div className="text-center">
            <button
              onClick={handleSeeAll}
              className="px-8 py-3 rounded-full border border-blue-600 bg-transparent text-blue-600 text-sm font-semibold cursor-pointer hover:bg-blue-50 transition-colors"
            >
              See all matching schemes →
            </button>
          </div>
        </>
      )}
    </div>
  )
}
