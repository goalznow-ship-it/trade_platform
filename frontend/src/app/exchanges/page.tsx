"use client"

import { Navbar } from "@/components/Navbar"
import { ExchangeCredentialsPanel } from "@/components/exchanges/ExchangeCredentialsPanel"

export default function ExchangesRoute() {
  return (
    <div className="flex h-screen flex-col bg-[#0d1117]">
      <Navbar />
      <main className="flex-1 overflow-auto">
        <ExchangeCredentialsPanel />
      </main>
    </div>
  )
}
