"use client"

import { useEffect, useState } from "react"
import { Navbar } from "@/components/Navbar"
import { TradingChart } from "@/components/chart/TradingChart"
import { TradingPanel } from "@/components/trading/TradingPanel"
import { AnalysisPanel } from "@/components/trading/AnalysisPanel"
import { NewsPanel } from "@/components/news/NewsPanel"
import { AdminDashboard } from "@/components/admin/AdminDashboard"
import { useAuth } from "@/hooks/useAuth"
import { useMarketStore } from "@/store/market"
import {
  LayoutDashboard, LineChart, Activity, FileText, Settings,
  ChevronLeft, ChevronRight, PanelRightClose, PanelRightOpen,
} from "lucide-react"
import { cn } from "@/lib/utils"

type Tab = "dashboard" | "chart" | "analysis" | "admin" | "news"

export default function Home() {
  const { user, loadUser } = useAuth()
  const [activeTab, setActiveTab] = useState<Tab>("dashboard")
  const [showRightPanel, setShowRightPanel] = useState(true)
  const [showLeftPanel, setShowLeftPanel] = useState(true)
  const [rightPanelTab, setRightPanelTab] = useState<"trade" | "analysis" | "news">("trade")

  useEffect(() => { loadUser() }, [])

  const sidebarItems = [
    { id: "dashboard" as Tab, label: "Dashboard", icon: LayoutDashboard },
    { id: "chart" as Tab, label: "Charts", icon: LineChart },
    { id: "analysis" as Tab, label: "Analysis", icon: Activity },
    { id: "news" as Tab, label: "News", icon: FileText },
    ...(user?.is_admin ? [{ id: "admin" as Tab, label: "Admin", icon: Settings }] : []),
  ]

  return (
    <div className="h-screen flex flex-col bg-[#0d1117]">
      <Navbar />

      {activeTab === "admin" && user?.is_admin ? (
        <main className="flex-1 overflow-auto">
          <AdminDashboard />
        </main>
      ) : (
        <main className="flex-1 flex overflow-hidden">
          {/* Left Sidebar */}
          <div className={cn(
            "flex flex-col border-r border-gray-800 bg-gray-950 transition-all duration-300",
            showLeftPanel ? "w-12" : "w-0"
          )}>
            <div className="flex flex-col items-center py-2 gap-1">
              {sidebarItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={cn(
                    "p-2 rounded-lg transition-colors",
                    activeTab === item.id
                      ? "bg-blue-600/20 text-blue-400"
                      : "text-gray-500 hover:text-gray-300 hover:bg-gray-800"
                  )}
                  title={item.label}
                >
                  <item.icon className="w-5 h-5" />
                </button>
              ))}
              <div className="flex-1" />
              <button
                onClick={() => setShowLeftPanel(false)}
                className="p-2 text-gray-600 hover:text-gray-400"
                title="Collapse sidebar"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
            </div>
          </div>

          {!showLeftPanel && (
            <button
              onClick={() => setShowLeftPanel(true)}
              className="fixed left-0 top-1/2 -translate-y-1/2 z-10 p-1 bg-gray-900 border border-gray-800 rounded-r-lg text-gray-500 hover:text-gray-300"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          )}

          {/* Main Chart Area */}
          <div className="flex-1 flex flex-col min-w-0">
            {activeTab === "dashboard" && (
              <div className="flex-1 flex flex-col">
                <TradingChart />
              </div>
            )}
            {activeTab === "chart" && (
              <div className="flex-1">
                <TradingChart />
              </div>
            )}
            {activeTab === "analysis" && (
              <div className="flex-1 p-4 overflow-auto">
                <AnalysisPanel />
              </div>
            )}
            {activeTab === "news" && (
              <div className="flex-1 overflow-auto">
                <NewsPanel />
              </div>
            )}
          </div>

          {/* Right Panel Switcher */}
          <div className="flex flex-col border-l border-gray-800">
            <div className="flex border-b border-gray-800">
              {[
                { id: "trade", label: "Trade" },
                { id: "analysis", label: "Analysis" },
                { id: "news", label: "News" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setRightPanelTab(tab.id as any)}
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
            <div className={cn(
              "transition-all duration-300 overflow-hidden",
              showRightPanel ? "w-80" : "w-0"
            )}>
              {rightPanelTab === "trade" && <TradingPanel />}
              {rightPanelTab === "analysis" && <AnalysisPanel />}
              {rightPanelTab === "news" && <NewsPanel />}
            </div>
            <button
              onClick={() => setShowRightPanel(!showRightPanel)}
              className="p-2 text-gray-600 hover:text-gray-400 self-center"
            >
              {showRightPanel ? (
                <PanelRightClose className="w-4 h-4" />
              ) : (
                <PanelRightOpen className="w-4 h-4" />
              )}
            </button>
          </div>
        </main>
      )}
    </div>
  )
}
