"use client"

import { useEffect, useState, Suspense } from "react"
import { useRouter } from "next/navigation"
import dynamic from "next/dynamic"
import { Navbar } from "@/components/Navbar"
import { DashboardOverview } from "@/components/dashboard/DashboardOverview"
import { WSProvider } from "@/components/WSProvider"
import { ConnectionQualityIndicator } from "@/components/dashboard/ConnectionQuality"
import { useAuth } from "@/hooks/useAuth"
import { useMarketStore } from "@/store/market"
import {
  LayoutDashboard, LineChart, Activity, FileText, Settings,
  List, Bell, Shield, BookOpen, Wallet, Search,
  PieChart, BarChart3, BellRing, Wifi,
  ChevronLeft, ChevronRight, PanelRightClose, PanelRightOpen,
} from "lucide-react"
import { cn } from "@/lib/utils"

const TradingChart = dynamic(() => import("@/components/chart/TradingChart").then((m) => ({ default: m.TradingChart })), { ssr: false })
const TradingPanel = dynamic(() => import("@/components/trading/TradingPanel").then((m) => ({ default: m.TradingPanel })), { ssr: false })
const AnalysisPanel = dynamic(() => import("@/components/trading/AnalysisPanel").then((m) => ({ default: m.AnalysisPanel })), { ssr: false })
const NewsPanel = dynamic(() => import("@/components/news/NewsPanel").then((m) => ({ default: m.NewsPanel })), { ssr: false })
const WatchlistPanel = dynamic(() => import("@/components/watchlist/WatchlistPanel").then((m) => ({ default: m.WatchlistPanel })), { ssr: false })
const AlertPanel = dynamic(() => import("@/components/alert/AlertPanel").then((m) => ({ default: m.AlertPanel })), { ssr: false })
const RiskPanel = dynamic(() => import("@/components/risk/RiskPanel").then((m) => ({ default: m.RiskPanel })), { ssr: false })
const JournalPanel = dynamic(() => import("@/components/journal/JournalPanel").then((m) => ({ default: m.JournalPanel })), { ssr: false })
const PaperTradingPanel = dynamic(() => import("@/components/paper/PaperTradingPanel").then((m) => ({ default: m.PaperTradingPanel })), { ssr: false })
const ScannerPanel = dynamic(() => import("@/components/scanner/ScannerPanel").then((m) => ({ default: m.ScannerPanel })), { ssr: false })
const PortfolioPanel = dynamic(() => import("@/components/portfolio/PortfolioPanel").then((m) => ({ default: m.PortfolioPanel })), { ssr: false })
const BacktestPanel = dynamic(() => import("@/components/backtest/BacktestPanel").then((m) => ({ default: m.BacktestPanel })), { ssr: false })
const NotificationsPanel = dynamic(() => import("@/components/notifications/NotificationsPanel").then((m) => ({ default: m.NotificationsPanel })), { ssr: false })
const AdminDashboard = dynamic(() => import("@/components/admin/AdminDashboard").then((m) => ({ default: m.AdminDashboard })), { ssr: false })

function PanelFallback() {
  return (
    <div className="flex-1 flex items-center justify-center bg-[#0d1117]">
      <div className="animate-pulse space-y-3 w-64">
        <div className="h-4 bg-gray-800 rounded w-3/4 mx-auto" />
        <div className="h-32 bg-gray-800 rounded" />
      </div>
    </div>
  )
}

type Tab = "dashboard" | "chart" | "analysis" | "scanner"
  | "watchlist" | "alerts" | "portfolio" | "journal"
  | "paper" | "risk" | "backtest" | "notifications"
  | "news" | "admin"

export default function DashboardPage() {
  const { user, loadUser } = useAuth()
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<Tab>("dashboard")
  const [showRightPanel, setShowRightPanel] = useState(true)
  const [showLeftPanel, setShowLeftPanel] = useState(true)
  const [rightPanelTab, setRightPanelTab] = useState<"trade" | "analysis" | "news">("trade")

  useEffect(() => {
    loadUser()
    const token = localStorage.getItem("token")
    if (!token) router.push("/login")
  }, [])

  const sidebarItems = [
    { id: "dashboard" as Tab, label: "Dashboard", icon: LayoutDashboard },
    { id: "chart" as Tab, label: "Charts", icon: LineChart },
    { id: "analysis" as Tab, label: "Analysis", icon: Activity },
    { id: "scanner" as Tab, label: "Scanner", icon: Search },
    { id: "watchlist" as Tab, label: "Watchlist", icon: List },
    { id: "alerts" as Tab, label: "Alerts", icon: Bell },
    { id: "portfolio" as Tab, label: "Portfolio", icon: PieChart },
    { id: "journal" as Tab, label: "Journal", icon: BookOpen },
    { id: "paper" as Tab, label: "Paper", icon: Wallet },
    { id: "risk" as Tab, label: "Risk", icon: Shield },
    { id: "backtest" as Tab, label: "Backtest", icon: BarChart3 },
    { id: "notifications" as Tab, label: "Notify", icon: BellRing },
    { id: "news" as Tab, label: "News", icon: FileText },
    ...(user?.is_admin ? [{ id: "admin" as Tab, label: "Admin", icon: Settings }] : []),
  ]

  const showRight = !["admin", "scanner", "watchlist", "alerts", "portfolio",
    "journal", "paper", "risk", "backtest", "notifications"].includes(activeTab)

  return (
    <WSProvider>
    <div className="h-screen flex flex-col bg-[#0d1117]">
      <Navbar />

      <ConnectionQualityIndicator />

      <main className="flex-1 flex overflow-hidden">
        <div className={cn(
          "flex flex-col border-r border-gray-800 bg-gray-950 transition-all duration-300",
          showLeftPanel ? "w-12" : "w-0"
        )}>
          <div className="flex-1 overflow-y-auto py-1 scrollbar-thin">
            <div className="flex flex-col items-center gap-0.5 px-1">
              {sidebarItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={cn(
                    "p-2 rounded-lg transition-colors relative",
                    activeTab === item.id
                      ? "bg-blue-600/20 text-blue-400"
                      : "text-gray-500 hover:text-gray-300 hover:bg-gray-800"
                  )}
                  title={item.label}
                >
                  <item.icon className="w-5 h-5" />
                </button>
              ))}
            </div>
          </div>
          <button
            onClick={() => setShowLeftPanel(false)}
            className="p-2 text-gray-600 hover:text-gray-400 border-t border-gray-800"
            title="Collapse sidebar"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
        </div>

        {!showLeftPanel && (
          <button
            onClick={() => setShowLeftPanel(true)}
            className="fixed left-0 top-1/2 -translate-y-1/2 z-10 p-1 bg-gray-900 border border-gray-800 rounded-r-lg text-gray-500 hover:text-gray-300"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        )}

        <div className={cn("flex-1 flex flex-col min-w-0", showRight ? "" : "w-full")}>
          <Suspense fallback={<PanelFallback />}>
            {activeTab === "dashboard" && <DashboardOverview />}
            {activeTab === "chart" && <TradingChart />}
            {activeTab === "analysis" && <div className="flex-1 p-4 overflow-auto"><AnalysisPanel /></div>}
            {activeTab === "scanner" && <ScannerPanel />}
            {activeTab === "watchlist" && <WatchlistPanel />}
            {activeTab === "alerts" && <AlertPanel />}
            {activeTab === "portfolio" && <PortfolioPanel />}
            {activeTab === "journal" && <JournalPanel />}
            {activeTab === "paper" && <PaperTradingPanel />}
            {activeTab === "risk" && <RiskPanel />}
            {activeTab === "backtest" && <BacktestPanel />}
            {activeTab === "notifications" && <NotificationsPanel />}
            {activeTab === "news" && <div className="flex-1 overflow-auto"><NewsPanel /></div>}
            {activeTab === "admin" && <AdminDashboard />}
          </Suspense>
        </div>

        {showRight && (
          <div className="flex flex-col border-l border-gray-800">
            <div className="flex border-b border-gray-800">
              {[
                { id: "trade" as const, label: "Trade" },
                { id: "analysis" as const, label: "Analysis" },
                { id: "news" as const, label: "News" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setRightPanelTab(tab.id)}
                  className={cn(
                    "px-3 py-2 text-xs font-medium transition-colors",
                    rightPanelTab === tab.id
                      ? "text-blue-400 border-b-2 border-blue-500 bg-gray-900"
                      : "text-gray-500 hover:text-gray-300 bg-gray-950"
                  )}
                >
                  {tab.label}
                </button>
              ))}
            </div>
            <div className={cn("transition-all duration-300 overflow-hidden", showRightPanel ? "w-80" : "w-0")}>
              {rightPanelTab === "trade" && <TradingPanel />}
              {rightPanelTab === "analysis" && <AnalysisPanel />}
              {rightPanelTab === "news" && <NewsPanel />}
            </div>
            <button
              onClick={() => setShowRightPanel(!showRightPanel)}
              className="p-2 text-gray-600 hover:text-gray-400 self-center"
            >
              {showRightPanel ? <PanelRightClose className="w-4 h-4" /> : <PanelRightOpen className="w-4 h-4" />}
            </button>
          </div>
        )}
      </main>
    </div>
    </WSProvider>
  )
}
