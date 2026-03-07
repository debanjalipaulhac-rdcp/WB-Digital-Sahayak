"use client"
export default function Loading() {
  return (
    <div className="min-h-screen bg-gray-50 animate-pulse">

      {/* Hero skeleton */}
      <div className="bg-gradient-to-br from-blue-600 to-blue-800 py-16 px-5">
        <div className="max-w-2xl mx-auto flex flex-col items-center gap-4">
          <div className="h-5 w-40 bg-white/20 rounded-full" />
          <div className="h-10 w-80 bg-white/20 rounded-xl" />
          <div className="h-4 w-64 bg-white/15 rounded-lg" />
          <div className="h-12 w-full max-w-md bg-white/20 rounded-xl mt-2" />
          <div className="flex gap-2 mt-1">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-8 w-28 bg-white/15 rounded-full" />
            ))}
          </div>
        </div>
      </div>

      {/* Recommended banner skeleton */}
      <div className="pt-7 px-5 max-w-6xl mx-auto">
        <div className="bg-white border border-gray-200 rounded-2xl p-6 flex items-center justify-between gap-5">
          <div className="flex-1 space-y-2">
            <div className="h-3 w-24 bg-gray-200 rounded" />
            <div className="h-6 w-64 bg-gray-200 rounded" />
            <div className="h-3 w-48 bg-gray-200 rounded" />
          </div>
          <div className="h-10 w-36 bg-gray-200 rounded-xl shrink-0" />
        </div>
      </div>

      {/* Scheme cards skeleton */}
      <div className="pt-10 pb-5 px-5 max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-5">
          <div className="h-6 w-56 bg-gray-200 rounded-lg" />
          <div className="h-4 w-16 bg-gray-200 rounded" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-36 bg-white border border-gray-200 rounded-2xl" />
          ))}
        </div>
      </div>
    </div>
  )
}