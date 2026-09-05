"use client"

import { Navbar } from "@/components/Navbar"
import { PerformanceDashboard } from "@/components/performance/PerformanceDashboard"

export default function PerformanceRoute() {
  return (
    <div className="min-h-screen bg-[#0d1117]">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <PerformanceDashboard />
      </main>
    </div>
  )
}
