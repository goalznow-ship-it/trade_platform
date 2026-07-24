"use client"

import { Navbar } from "@/components/Navbar"
import { PortfolioPanel } from "@/components/portfolio/PortfolioPanel"

export default function PortfolioRoute() {
  return <div className="h-screen flex flex-col bg-[#0d1117]"><Navbar/><main className="flex-1 overflow-auto"><PortfolioPanel/></main></div>
}
