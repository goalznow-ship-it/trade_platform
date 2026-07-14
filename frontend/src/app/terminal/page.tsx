"use client"

import { TerminalPage } from "@/components/terminal/TerminalPage"
import { Navbar } from "@/components/Navbar"

export default function TerminalRoute() {
  return (
    <div className="h-screen flex flex-col bg-[#0d1117]">
      <Navbar />
      <main className="flex-1 overflow-hidden">
        <TerminalPage />
      </main>
    </div>
  )
}
