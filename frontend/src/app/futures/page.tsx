"use client"

import { FuturesDashboard } from "@/components/futures/FuturesDashboard"
import { Navbar } from "@/components/Navbar"

export default function FuturesRoute() {
  return (
    <div className="h-screen flex flex-col bg-[#0d1117]">
      <Navbar />
      <main className="flex-1 overflow-hidden">
        <FuturesDashboard />
      </main>
    </div>
  )
}
