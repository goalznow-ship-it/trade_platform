"use client"

import { useAuth } from "@/hooks/useAuth"
import { useRouter } from "next/navigation"
import { useEffect } from "react"
import { Navbar } from "@/components/Navbar"
import { AdminDashboard } from "@/components/admin/AdminDashboard"

export default function AdminRoute() {
  const { user, loadUser } = useAuth()
  const router = useRouter()

  useEffect(() => {
    loadUser()
    const token = localStorage.getItem("token")
    if (!token) router.push("/login")
  }, [])

  if (!user?.is_admin) {
    return (
      <div className="h-screen flex flex-col bg-[#0d1117]">
        <Navbar />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-gray-500">
            <div className="text-lg">Access Denied</div>
            <div className="text-sm mt-1">Admin privileges required</div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col bg-[#0d1117]">
      <Navbar />
      <main className="flex-1 overflow-hidden">
        <AdminDashboard />
      </main>
    </div>
  )
}
