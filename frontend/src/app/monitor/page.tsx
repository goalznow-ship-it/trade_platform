"use client"

import { Navbar } from "@/components/Navbar"
import { SignalMonitor } from "@/components/monitor/SignalMonitor"

export default function SignalMonitorRoute() {
  return (
    <div className="flex h-screen flex-col bg-[#0d1117]">
      <Navbar />
      <main className="flex-1 overflow-hidden">
        <SignalMonitor />
      </main>
    </div>
  )
}
