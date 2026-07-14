"use client"

import { Navbar } from "@/components/Navbar"
import { MarketRadar } from "@/components/radar/MarketRadar"

export default function RadarRoute() {
  return (
    <div className="h-screen flex flex-col bg-[#0d1117]">
      <Navbar />
      <main className="flex-1 overflow-hidden">
        <MarketRadar />
      </main>
    </div>
  )
}
