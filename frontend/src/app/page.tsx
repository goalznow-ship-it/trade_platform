"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useAuth } from "@/hooks/useAuth"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"
import {
  TrendingUp, BarChart3, Shield, Brain, Zap, Bell,
  Activity, Target, ArrowRight, Check, Menu, X,
  ChevronRight, Star, Users, LineChart, Wallet,
} from "lucide-react"

export default function LandingPage() {
  const { user } = useAuth()
  const router = useRouter()
  const [mobileMenu, setMobileMenu] = useState(false)
  const [overview, setOverview] = useState<any>(null)

  useEffect(() => {
    api.getOverview().then(setOverview).catch(() => {})
    if (user) router.push("/dashboard")
  }, [user])

  const features = [
    { icon: Brain, title: "AI Analysis", desc: "Multi-factor AI engine analyzing trend, momentum, volume, volatility, and market structure for actionable trade signals." },
    { icon: Zap, title: "Signal Scanner", desc: "Real-time scanning across 16+ technical and fundamental filters. Identify opportunities before the market moves." },
    { icon: Shield, title: "Risk Management", desc: "Advanced risk controls with Sharpe ratio, VaR, Kelly criterion, drawdown limits, and position sizing." },
    { icon: Activity, title: "Technical Indicators", desc: "20+ professional indicators including RSI, MACD, Bollinger, Ichimoku, VWAP, Supertrend, and custom SMC analysis." },
    { icon: Target, title: "Backtesting Engine", desc: "Test strategies against historical data with comprehensive metrics: win rate, profit factor, Sharpe, and equity curves." },
    { icon: Bell, title: "Smart Alerts", desc: "Price, volume, indicator, and signal-based alerts with multi-channel delivery (in-app, email, Telegram, Discord)." },
    { icon: Wallet, title: "Paper Trading", desc: "Practice strategies risk-free with $100K virtual account. Track performance and refine your edge." },
    { icon: BarChart3, title: "Portfolio Analytics", desc: "Comprehensive PnL tracking, monthly heatmaps, win/loss analysis, and performance attribution." },
    { icon: LineChart, title: "Multi-Exchange", desc: "Connect Binance, Bybit, OKX, Bitget, KuCoin, and HyperLiquid from a single unified interface." },
  ]

  const plans = [
    {
      name: "Free", price: "$0", period: "/month",
      features: ["3 AI signals/day", "Basic market data", "5 technical indicators", "3 alerts", "1 watchlist", "Paper trading"],
      cta: "Get Started", popular: false,
    },
    {
      name: "Pro", price: "$29", period: "/month",
      features: ["Unlimited AI signals", "AI prediction engine", "Futures intelligence", "Backtesting engine", "News intelligence", "Risk management"],
      cta: "Start Free Trial", popular: true,
    },
    {
      name: "Elite", price: "$99", period: "/month",
      features: ["Whale tracking", "Advanced AI predictions", "API access (100 req/min)", "Multi-exchange support", "Dedicated support 24/7", "Team accounts (up to 5)"],
      cta: "Go Elite", popular: false,
    },
  ]

  const stats = [
    { value: "15+", label: "Exchanges Supported" },
    { value: "20+", label: "Technical Indicators" },
    { value: "99.9%", label: "Platform Uptime" },
    { value: "8", label: "AI Analysis Factors" },
  ]

  return (
    <div className="min-h-screen bg-[#0a0e17] text-gray-100">
      {/* Navbar */}
      <header className="fixed top-0 left-0 right-0 z-50 border-b border-gray-800/50 bg-[#0a0e17]/90 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-white" />
              </div>
              <span className="text-lg font-bold text-white">TradeAnalyst</span>
              <span className="text-[10px] font-semibold text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded">PRO</span>
            </Link>

            <nav className="hidden md:flex items-center gap-6">
              {["Features", "AI Analysis", "Scanner", "Pricing"].map((item) => (
                <a key={item} href={`#${item.toLowerCase().replace(/\s+/g, "-")}`}
                  className="text-sm text-gray-400 hover:text-white transition-colors">
                  {item}
                </a>
              ))}
            </nav>

            <div className="flex items-center gap-3">
              <Link href="/login"
                className="hidden sm:inline-flex text-sm text-gray-400 hover:text-white transition-colors">
                Sign In
              </Link>
              <Link href="/register"
                className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors">
                Get Started <ArrowRight className="w-3.5 h-3.5" />
              </Link>
              <button onClick={() => setMobileMenu(!mobileMenu)} className="md:hidden p-2 text-gray-400">
                {mobileMenu ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              </button>
            </div>
          </div>
        </div>
        {mobileMenu && (
          <div className="md:hidden border-t border-gray-800 bg-[#0a0e17] px-4 py-4">
            <div className="flex flex-col gap-2">
              {["Features", "AI Analysis", "Scanner", "Pricing"].map((item) => (
                <a key={item} href={`#${item.toLowerCase().replace(/\s+/g, "-")}`}
                  onClick={() => setMobileMenu(false)}
                  className="text-sm text-gray-400 hover:text-white px-3 py-2 rounded-lg hover:bg-gray-800">
                  {item}
                </a>
              ))}
              <Link href="/login" className="text-sm text-gray-400 hover:text-white px-3 py-2" onClick={() => setMobileMenu(false)}>
                Sign In
              </Link>
            </div>
          </div>
        )}
      </header>

      {/* Hero */}
      <section className="relative pt-32 pb-20 px-4 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-blue-600/5 via-transparent to-transparent" />
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl" />
        <div className="absolute top-40 right-1/4 w-64 h-64 bg-purple-500/5 rounded-full blur-3xl" />
        <div className="max-w-7xl mx-auto text-center relative">
          <div className="inline-flex items-center gap-2 px-3 py-1 mb-6 text-xs font-medium text-blue-400 bg-blue-500/10 rounded-full border border-blue-500/20">
            <Zap className="w-3 h-3" /> AI-Powered Trading Intelligence Platform
          </div>
          <h1 className="text-4xl sm:text-5xl lg:text-7xl font-bold text-white leading-tight mb-6">
            Trade Smarter with
            <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-purple-400 to-blue-500">
              AI-Driven Insights
            </span>
          </h1>
          <p className="text-lg sm:text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Professional crypto market analysis with advanced AI, real-time signals,
            risk management, and multi-exchange support — all in one platform.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/register"
              className="inline-flex items-center justify-center gap-2 px-8 py-3.5 text-base font-semibold text-white bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl hover:from-blue-700 hover:to-purple-700 transition-all shadow-lg shadow-blue-600/20">
              Start Free Trial <ChevronRight className="w-4 h-4" />
            </Link>
            <a href="#features"
              className="inline-flex items-center justify-center gap-2 px-8 py-3.5 text-base font-medium text-gray-300 bg-gray-800/50 border border-gray-700 rounded-xl hover:bg-gray-800 transition-all">
              Explore Features
            </a>
          </div>

          {/* Market Ticker */}
          {overview && (
            <div className="mt-12 inline-flex items-center gap-4 sm:gap-8 px-6 py-3 bg-gray-900/50 border border-gray-800 rounded-2xl">
              <div className="flex items-center gap-2">
                <span className="text-orange-400 font-semibold text-sm">BTC</span>
                <span className="text-white font-mono text-sm">${(overview.btc_price || 0).toLocaleString()}</span>
                <span className={cn("text-xs font-mono", (overview.btc_change || 0) >= 0 ? "text-green-400" : "text-red-400")}>
                  {(overview.btc_change || 0) >= 0 ? "+" : ""}{overview.btc_change?.toFixed(2) || "0.00"}%
                </span>
              </div>
              <div className="hidden sm:block w-px h-6 bg-gray-800" />
              <div className="flex items-center gap-2">
                <span className="text-blue-400 font-semibold text-sm">ETH</span>
                <span className="text-white font-mono text-sm">${(overview.eth_price || 0).toLocaleString()}</span>
              </div>
              <div className="hidden sm:block w-px h-6 bg-gray-800" />
              <div className="hidden sm:flex items-center gap-1 text-xs text-gray-500">
                <Activity className="w-3 h-3" /> Live
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Stats */}
      <section className="py-12 border-y border-gray-800/50">
        <div className="max-w-7xl mx-auto px-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-3xl font-bold text-white font-mono">{s.value}</div>
                <div className="text-sm text-gray-500 mt-1">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-20 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
              Everything You Need to Trade
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              Professional-grade tools and analytics that give you an edge in the markets.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {features.map((f) => (
              <div key={f.title}
                className="group p-6 rounded-2xl border border-gray-800 bg-gray-900/50 hover:bg-gray-900 hover:border-gray-700 transition-all">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                  <f.icon className="w-5 h-5 text-blue-400" />
                </div>
                <h3 className="text-base font-semibold text-white mb-2">{f.title}</h3>
                <p className="text-sm text-gray-400 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* AI Analysis Section */}
      <section id="ai-analysis" className="py-20 px-4 bg-gradient-to-b from-transparent via-blue-600/5 to-transparent">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 mb-4 text-xs font-medium text-purple-400 bg-purple-500/10 rounded-full border border-purple-500/20">
                <Brain className="w-3 h-3" /> AI Analysis Engine
              </div>
              <h2 className="text-3xl sm:text-4xl font-bold text-white mb-6">
                Multi-Factor AI That Understands the Market
              </h2>
              <p className="text-gray-400 mb-8 leading-relaxed">
                Our proprietary AI engine analyzes 8 distinct factors simultaneously — trend,
                momentum, volume, volatility, market structure, Smart Money Concepts (SMC),
                news sentiment, and Fear & Greed — to deliver a unified confidence score.
              </p>
              <div className="space-y-4">
                {[
                  { label: "Trend Analysis", value: "20%", desc: "Moving averages, Ichimoku, market phase detection" },
                  { label: "Momentum", value: "20%", desc: "RSI, MACD, Stochastic, rate of change" },
                  { label: "Volume Profile", value: "15%", desc: "OBV, CMF, volume spikes, liquidity zones" },
                  { label: "SMC / Order Flow", value: "10%", desc: "FVG detection, order blocks, liquidity grabs" },
                ].map((f) => (
                  <div key={f.label} className="flex items-center gap-4 p-3 rounded-xl bg-gray-900/50 border border-gray-800">
                    <div className="text-lg font-bold text-blue-400 font-mono w-12">{f.value}</div>
                    <div>
                      <div className="text-sm font-medium text-white">{f.label}</div>
                      <div className="text-xs text-gray-500">{f.desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="relative">
              <div className="aspect-square rounded-2xl bg-gradient-to-br from-blue-600/10 to-purple-600/10 border border-blue-500/20 p-8 flex items-center justify-center">
                <div className="text-center">
                  <div className="text-7xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400 mb-4">87%</div>
                  <div className="text-lg text-gray-400 mb-6">Average AI Confidence Score</div>
                  <div className="grid grid-cols-2 gap-3">
                    {[{ label: "Win Rate", val: "64%" }, { label: "Profit Factor", val: "2.1" },
                      { label: "Signals/Day", val: "12" }, { label: "Accuracy", val: "71%" }].map((s) => (
                      <div key={s.label} className="p-3 rounded-xl bg-gray-900/50">
                        <div className="text-lg font-bold text-white font-mono">{s.val}</div>
                        <div className="text-xs text-gray-500">{s.label}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Scanner Section */}
      <section id="scanner" className="py-20 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="order-2 lg:order-1">
              <div className="aspect-video rounded-2xl bg-gradient-to-br from-green-600/10 to-emerald-600/10 border border-green-500/20 p-6 flex items-center justify-center">
                <div className="w-full max-w-sm">
                  <div className="flex flex-wrap gap-1.5 mb-4">
                    {["RSI Oversold", "Volume Spike", "Breakout", "Golden Cross", "Support Test", "MACD Bullish"].map((f) => (
                      <span key={f} className="px-2 py-1 text-[10px] font-medium rounded-full bg-blue-600/20 text-blue-400 border border-blue-500/30">
                        {f}
                      </span>
                    ))}
                  </div>
                  {[{ sym: "BTC/USDT", dir: "LONG", conf: 92, reason: "Volume Spike + RSI Oversold" },
                    { sym: "ETH/USDT", dir: "LONG", conf: 85, reason: "Golden Cross + Support Test" },
                    { sym: "SOL/USDT", dir: "SHORT", conf: 78, reason: "Death Cross + Resistance Test" },
                  ].map((s) => (
                    <div key={s.sym} className="flex items-center gap-3 px-3 py-2 mb-1 rounded-lg bg-gray-900/70 border border-gray-800">
                      <div className={cn("w-1.5 h-6 rounded-full", s.dir === "LONG" ? "bg-green-500" : "bg-red-500")} />
                      <span className="text-sm font-mono text-white flex-1">{s.sym}</span>
                      <span className={cn("text-[10px] font-bold px-1.5 py-0.5 rounded",
                        s.dir === "LONG" ? "bg-green-900/50 text-green-400" : "bg-red-900/50 text-red-400")}>
                        {s.dir}
                      </span>
                      <span className="text-xs font-mono text-white">{s.conf}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="order-1 lg:order-2">
              <div className="inline-flex items-center gap-2 px-3 py-1 mb-4 text-xs font-medium text-green-400 bg-green-500/10 rounded-full border border-green-500/20">
                <Zap className="w-3 h-3" /> Enterprise Scanner
              </div>
              <h2 className="text-3xl sm:text-4xl font-bold text-white mb-6">
                Scan Markets with 16+ Advanced Filters
              </h2>
              <p className="text-gray-400 mb-6 leading-relaxed">
                Combine any of 16 technical and fundamental filters to find exactly the setups
                you're looking for. From simple RSI oversold scans to complex multi-filter
                strategies, the scanner delivers results in real-time.
              </p>
              <ul className="space-y-3">
                {[
                  "Real-time multi-filter scanning engine",
                  "Combine any filters for precise screening",
                  "RSI, MACD, Volume, Breakout patterns",
                  "Support/Resistance, Volatility, Liquidity tests",
                  "Golden Cross, Death Cross detection",
                ].map((item) => (
                  <li key={item} className="flex items-center gap-2 text-sm text-gray-400">
                    <Check className="w-4 h-4 text-green-400 flex-shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Risk Management */}
      <section className="py-20 px-4 bg-gradient-to-b from-transparent via-red-600/5 to-transparent">
        <div className="max-w-7xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 mb-4 text-xs font-medium text-red-400 bg-red-500/10 rounded-full border border-red-500/20">
            <Shield className="w-3 h-3" /> Risk Management
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
            Institutional-Grade Risk Controls
          </h2>
          <p className="text-gray-400 max-w-2xl mx-auto mb-12">
            Protect your capital with advanced risk metrics and automated position sizing.
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { metric: "Sharpe Ratio", desc: "Risk-adjusted return measurement" },
              { metric: "VaR (95%)", desc: "Value at Risk calculation" },
              { metric: "Kelly Criterion", desc: "Optimal position sizing" },
              { metric: "Drawdown Control", desc: "Max drawdown limits & alerts" },
              { metric: "Profit Factor", desc: "Gross profit / gross loss ratio" },
              { metric: "Sortino Ratio", desc: "Downside risk-adjusted return" },
              { metric: "Exposure Limits", desc: "Per-symbol & total exposure caps" },
              { metric: "Correlation Monitor", desc: "Portfolio correlation tracking" },
            ].map((r) => (
              <div key={r.metric} className="p-5 rounded-xl border border-gray-800 bg-gray-900/50 text-left">
                <div className="text-sm font-semibold text-white mb-1">{r.metric}</div>
                <div className="text-xs text-gray-500">{r.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-20 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
              Simple, Transparent Pricing
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              Start free, upgrade as you grow. No hidden fees.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {plans.map((plan) => (
              <div key={plan.name}
                className={cn(
                  "relative p-6 rounded-2xl border transition-all",
                  plan.popular
                    ? "border-blue-500/50 bg-gradient-to-b from-blue-600/10 to-purple-600/5 scale-105"
                    : "border-gray-800 bg-gray-900/50 hover:border-gray-700"
                )}>
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 text-[10px] font-semibold text-white bg-gradient-to-r from-blue-600 to-purple-600 rounded-full">
                    MOST POPULAR
                  </div>
                )}
                <h3 className="text-lg font-semibold text-white mb-1">{plan.name}</h3>
                <div className="mb-4">
                  <span className="text-3xl font-bold text-white">{plan.price}</span>
                  <span className="text-sm text-gray-500">{plan.period}</span>
                </div>
                <ul className="space-y-2.5 mb-8">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-center gap-2 text-sm text-gray-400">
                      <Check className="w-4 h-4 text-blue-400 flex-shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link href={plan.name === "Enterprise" ? "/contact" : "/register"}
                  className={cn(
                    "block text-center py-2.5 rounded-xl text-sm font-medium transition-all",
                    plan.popular
                      ? "bg-blue-600 text-white hover:bg-blue-700"
                      : "bg-gray-800 text-gray-300 hover:bg-gray-700 border border-gray-700"
                  )}>
                  {plan.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto text-center p-12 rounded-3xl bg-gradient-to-br from-blue-600/10 via-purple-600/10 to-blue-600/5 border border-blue-500/20">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
            Ready to Transform Your Trading?
          </h2>
          <p className="text-gray-400 max-w-xl mx-auto mb-8">
            Join thousands of traders using TradeAnalyst Pro to make data-driven decisions.
            Start with a free account — no credit card required.
          </p>
          <Link href="/register"
            className="inline-flex items-center gap-2 px-8 py-3.5 text-base font-semibold text-white bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl hover:from-blue-700 hover:to-purple-700 transition-all shadow-lg shadow-blue-600/20">
            Get Started Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-12 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                  <TrendingUp className="w-4 h-4 text-white" />
                </div>
                <span className="font-bold text-white">TradeAnalyst</span>
              </div>
              <p className="text-sm text-gray-500 leading-relaxed">
                AI-powered crypto trading intelligence platform for professional traders.
              </p>
            </div>
            {[
              { title: "Product", links: ["Features", "Pricing", "AI Analysis", "Scanner", "API"] },
              { title: "Company", links: ["About", "Blog", "Careers", "Contact"] },
              { title: "Legal", links: ["Privacy", "Terms", "Security", "Cookies"] },
            ].map((col) => (
              <div key={col.title}>
                <h4 className="text-sm font-semibold text-white mb-3">{col.title}</h4>
                <ul className="space-y-2">
                  {col.links.map((link) => (
                    <li key={link}>
                      <a href="#" className="text-sm text-gray-500 hover:text-gray-300 transition-colors">{link}</a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div className="pt-8 border-t border-gray-800 text-center text-sm text-gray-600">
            &copy; {new Date().getFullYear()} TradeAnalyst Pro. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  )
}
