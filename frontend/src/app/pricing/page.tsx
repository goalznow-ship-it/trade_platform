"use client"

import { useState } from "react"
import Link from "next/link"
import { Navbar } from "@/components/Navbar"
import { Check, ArrowRight, Zap, Shield, Star } from "lucide-react"
import { cn } from "@/lib/utils"

export default function PricingRoute() {
  const [annual, setAnnual] = useState(false)

  const plans = [
    {
      name: "Free",
      price: "$0",
      period: "forever",
      icon: Star,
      features: [
        "Basic market data & charts",
        "5 technical indicators",
        "3 signals per day",
        "1 watchlist (max 10 symbols)",
        "Paper trading ($100K virtual)",
        "Basic market overview",
        "5 min delayed data",
      ],
      cta: "Get Started",
      popular: false,
      color: "gray",
    },
    {
      name: "Pro",
      price: annual ? "$24" : "$29",
      period: annual ? "/month, billed yearly" : "/month",
      icon: Zap,
      features: [
        "Everything in Free",
        "Unlimited AI trading signals",
        "AI prediction engine",
        "Futures intelligence",
        "Real-time market data",
        "Advanced technical indicators",
        "Backtesting engine",
        "Risk management tools",
        "Trading journal",
        "Smart alerts (unlimited)",
        "Multi-watchlist support",
        "Market scanner",
        "News intelligence",
        "Email & Telegram alerts",
      ],
      cta: "Start Free Trial",
      popular: true,
      color: "blue",
    },
    {
      name: "Elite",
      price: annual ? "$79" : "$99",
      period: annual ? "/month, billed yearly" : "/month",
      icon: Shield,
      features: [
        "Everything in Pro",
        "Whale transaction tracking",
        "Advanced AI predictions",
        "API access (rate: 100/min)",
        "Multi-exchange support",
        "Portfolio analytics",
        "Admin dashboard access",
        "Priority support 24/7",
        "Custom indicators",
        "WebSocket real-time feed",
        "Export data (CSV/JSON)",
        "Team collaboration (up to 5)",
        "Dedicated account manager",
        "Early feature access",
      ],
      cta: "Go Elite",
      popular: false,
      color: "purple",
    },
  ]

  return (
    <div className="h-screen flex flex-col bg-[#0d1117]">
      <Navbar />
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-6xl mx-auto p-4 lg:p-8 space-y-8">
          {/* Header */}
          <div className="text-center pt-8">
            <div className="inline-flex items-center gap-2 px-3 py-1 mb-4 text-xs font-medium text-blue-400 bg-blue-500/10 rounded-full border border-blue-500/20">
              <Zap className="w-3 h-3" /> Premium Trading Intelligence
            </div>
            <h1 className="text-3xl lg:text-4xl font-bold text-white mb-3">
              Choose Your Plan
            </h1>
            <p className="text-gray-400 max-w-xl mx-auto text-sm">
              Start free, upgrade as you grow. All plans include a 7-day free trial on Pro.
            </p>
            {/* Toggle */}
            <div className="flex items-center justify-center gap-3 mt-6">
              <span className={cn("text-sm", !annual ? "text-white font-medium" : "text-gray-500")}>Monthly</span>
              <button onClick={() => setAnnual(!annual)}
                className={cn(
                  "relative w-12 h-6 rounded-full transition-colors",
                  annual ? "bg-blue-600" : "bg-gray-700"
                )}>
                <div className={cn(
                  "absolute top-1 w-4 h-4 rounded-full bg-white transition-all",
                  annual ? "left-7" : "left-1"
                )} />
              </button>
              <span className={cn("text-sm", annual ? "text-white font-medium" : "text-gray-500")}>
                Annual <span className="text-green-400 text-xs font-medium">Save 20%</span>
              </span>
            </div>
          </div>

          {/* Plans */}
          <div className="grid md:grid-cols-3 gap-5 max-w-5xl mx-auto">
            {plans.map((plan) => (
              <div key={plan.name} className={cn(
                "relative p-6 rounded-2xl border transition-all flex flex-col",
                plan.popular
                  ? "border-blue-500/50 bg-gradient-to-b from-blue-600/10 to-purple-600/5 shadow-lg shadow-blue-600/10 scale-[1.02]"
                  : "border-gray-800 bg-gray-900/50 hover:border-gray-700"
              )}>
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 text-[10px] font-semibold text-white bg-gradient-to-r from-blue-600 to-purple-600 rounded-full">
                    MOST POPULAR
                  </div>
                )}
                <div className="flex items-center gap-2 mb-4">
                  <div className={cn(
                    "w-8 h-8 rounded-lg flex items-center justify-center",
                    plan.color === "blue" ? "bg-blue-500/20" :
                    plan.color === "purple" ? "bg-purple-500/20" : "bg-gray-800"
                  )}>
                    <plan.icon className={cn(
                      "w-4 h-4",
                      plan.color === "blue" ? "text-blue-400" :
                      plan.color === "purple" ? "text-purple-400" : "text-gray-400"
                    )} />
                  </div>
                  <span className="text-lg font-semibold text-white">{plan.name}</span>
                </div>
                <div className="mb-4">
                  <span className="text-3xl font-bold text-white">{plan.price}</span>
                  <span className="text-xs text-gray-500 ml-1">{plan.period}</span>
                </div>
                <ul className="space-y-2.5 mb-6 flex-1">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-center gap-2 text-xs text-gray-400">
                      <Check className={cn(
                        "w-3.5 h-3.5 flex-shrink-0",
                        plan.color === "blue" ? "text-blue-400" :
                        plan.color === "purple" ? "text-purple-400" : "text-green-400"
                      )} />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link href="/register"
                  className={cn(
                    "block text-center py-2.5 rounded-xl text-xs font-medium transition-all",
                    plan.popular
                      ? "bg-blue-600 text-white hover:bg-blue-700"
                      : "bg-gray-800 text-gray-300 hover:bg-gray-700 border border-gray-700"
                  )}>
                  {plan.cta} <ArrowRight className="w-3 h-3 inline ml-1" />
                </Link>
              </div>
            ))}
          </div>

          {/* Feature Comparison */}
          <div className="p-6 rounded-2xl border border-gray-800 bg-gray-900/30 max-w-5xl mx-auto">
            <h2 className="text-sm font-semibold text-white mb-4 text-center">Detailed Feature Comparison</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-[10px] text-gray-500 uppercase border-b border-gray-800">
                    <th className="text-left py-2 pr-4">Feature</th>
                    <th className="text-center py-2 pr-4">Free</th>
                    <th className="text-center py-2 pr-4">Pro</th>
                    <th className="text-center py-2">Elite</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { f: "AI Trading Signals", free: "3/day", pro: "Unlimited", elite: "Unlimited" },
                    { f: "Signal Confidence Score", free: "Basic", pro: "Weighted AI", elite: "Weighted AI + Whale" },
                    { f: "Technical Indicators", free: "5", pro: "20+", elite: "25+ Custom" },
                    { f: "Market Scanner", free: "Basic", pro: "Advanced", elite: "Real-time" },
                    { f: "Futures Intelligence", free: "—", pro: "✓", elite: "✓ Priority" },
                    { f: "News Intelligence", free: "—", pro: "✓", elite: "✓ AI Enhanced" },
                    { f: "Backtesting Engine", free: "—", pro: "✓", elite: "✓ Advanced" },
                    { f: "Risk Management", free: "Basic", pro: "Advanced", elite: "Portfolio-level" },
                    { f: "Whale Tracking", free: "—", pro: "—", elite: "✓ Real-time" },
                    { f: "API Access", free: "—", pro: "—", elite: "✓ 100 req/min" },
                    { f: "Data Delay", free: "5 min", pro: "Real-time", elite: "Real-time" },
                    { f: "Support", free: "Email", pro: "Priority Email", elite: "24/7 Dedicated" },
                  ].map((row) => (
                    <tr key={row.f} className="border-b border-gray-800/50 text-gray-400">
                      <td className="py-2.5 pr-4 text-gray-300 font-medium">{row.f}</td>
                      <td className="py-2.5 pr-4 text-center">{row.free}</td>
                      <td className="py-2.5 pr-4 text-center text-blue-400 font-medium">{row.pro}</td>
                      <td className="py-2.5 text-center text-purple-400 font-medium">{row.elite}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
