"use client"

import { Navbar } from "@/components/Navbar"
import { NewsIntelligence } from "@/components/news/NewsIntelligence"

export default function NewsRoute() {
  return (
    <div className="h-screen flex flex-col bg-[#0d1117]">
      <Navbar />
      <main className="flex-1 overflow-hidden">
        <NewsIntelligence />
      </main>
    </div>
  )
}
