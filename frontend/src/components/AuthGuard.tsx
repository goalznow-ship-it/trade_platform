"use client"

import { useEffect } from "react"
import { usePathname, useRouter } from "next/navigation"
import { useAuth } from "@/hooks/useAuth"

const PUBLIC_ROUTES = new Set(["/", "/login", "/register", "/pricing"])

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const { user, isLoading, loadUser } = useAuth()
  const isPublic = PUBLIC_ROUTES.has(pathname)

  useEffect(() => {
    if (!isPublic) void loadUser()
  }, [isPublic, loadUser])

  useEffect(() => {
    if (!isPublic && !isLoading && !user) router.replace(`/login?next=${encodeURIComponent(pathname)}`)
  }, [isLoading, isPublic, pathname, router, user])

  if (!isPublic && (isLoading || !user)) {
    return <div className="min-h-screen bg-[#0d1117]" aria-label="Authenticating" />
  }
  return children
}
