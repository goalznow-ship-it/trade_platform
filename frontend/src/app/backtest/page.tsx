"use client"

import { useAuth } from "@/hooks/useAuth"
import { useRouter } from "next/navigation"
import { useEffect } from "react"
import { Navbar } from "@/components/Navbar"
import { BacktestPage } from "@/components/backtest/BacktestPage"

export default function BacktestRoute() {
  const { loadUser } = useAuth()
  const router = useRouter()

  useEffect(() => {
    loadUser()
    const token = localStorage.getItem("token")
    if (!token) router.push("/login")
  }, [loadUser, router])

  return (
    <div className="h-screen flex flex-col bg-[#0d1117]">
      <Navbar />
      <main className="flex-1 overflow-hidden">
        <BacktestPage />
      </main>
    </div>
  )
}
