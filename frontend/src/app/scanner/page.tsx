"use client"

import { Navbar } from "@/components/Navbar"
import { MarketScanner } from "@/components/scanner/MarketScanner"

export default function ScannerRoute() {
  return (
    <div className="h-screen flex flex-col bg-[#0d1117]">
      <Navbar />
      <main className="flex-1 overflow-hidden">
        <MarketScanner />
      </main>
    </div>
  )
}
