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

  // Listen for the soft-navigation signal emitted by api.ts when a
  // 401 comes back. Using window.location.assign() would do a full
  // page reload, losing all React state and cached data — we use
  // router.replace() instead, which keeps the SPA tree alive.
  useEffect(() => {
    if (isPublic) return
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<{ next: string }>).detail
      router.replace(`/login?next=${detail?.next || encodeURIComponent(pathname)}`)
    }
    window.addEventListener("app:auth:expired", handler)
    return () => window.removeEventListener("app:auth:expired", handler)
  }, [isPublic, pathname, router])

  if (!isPublic && (isLoading || !user)) {
    return <div className="min-h-screen bg-[#0d1117]" aria-label="Authenticating" />
  }
  return children
}
