"use client"

import { DashboardStats } from "@/components/dashboard/DashboardStats"
import { MarketOverview } from "@/components/dashboard/MarketOverview"
import { TopSignals } from "@/components/dashboard/TopSignals"
import { ActivePositions } from "@/components/dashboard/ActivePositions"
import { SentimentWidget } from "@/components/dashboard/SentimentWidget"
import { PortfolioSummary } from "@/components/dashboard/PortfolioSummary"
import { MarketSummary } from "@/components/dashboard/MarketSummary"

export function DashboardOverview() {
  return (
    <div className="h-full overflow-y-auto p-4 lg:p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-white">Dashboard</h1>
          <p className="text-xs text-gray-500 mt-0.5">Real-time portfolio overview and market intelligence</p>
        </div>
      </div>

      <MarketSummary />

      <DashboardStats />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          <MarketOverview />
          <TopSignals />
        </div>
        <div className="space-y-4">
          <SentimentWidget />
          <PortfolioSummary />
          <ActivePositions />
        </div>
      </div>
    </div>
  )
}
