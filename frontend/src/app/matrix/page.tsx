"use client"

import { Navbar } from "@/components/Navbar"
import { MarketMatrix } from "@/components/matrix/MarketMatrix"

export default function MatrixRoute() {
  return (
    <div className="h-screen flex flex-col bg-[#0d1117]">
      <Navbar />
      <main className="flex-1 overflow-auto">
        <MarketMatrix />
      </main>
    </div>
  )
}
