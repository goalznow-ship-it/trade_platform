"use client"

import { SignalCenter } from "@/components/signals/SignalCenter"
import { Navbar } from "@/components/Navbar"

export default function SignalsRoute() {
  return (
    <div className="h-screen flex flex-col bg-[#0d1117]">
      <Navbar />
      <main className="flex-1 overflow-hidden">
        <SignalCenter />
      </main>
    </div>
  )
}
