"use client"

import { create } from "zustand"
import { api } from "@/lib/api"

interface User {
  id: number
  username: string
  email: string
  is_admin: boolean
  is_active?: boolean
  display_name?: string
  timezone?: string
  language?: string
  theme?: string
  balance?: number
  total_pnl?: number
  win_rate?: number
  subscription_tier?: string
  created_at?: string
}

interface AuthState {
  user: User | null
  token: string | null
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string) => Promise<void>
  logout: () => void
  loadUser: () => Promise<void>
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  token: typeof window !== "undefined" ? localStorage.getItem("token") : null,
  isLoading: true,

  login: async (username, password) => {
    const res = await api.login(username, password)
    localStorage.setItem("token", res.access_token)
    set({ user: res.user, token: res.access_token })
  },

  register: async (username, email, password) => {
    await api.register({ username, email, password })
    const res = await api.login(username, password)
    localStorage.setItem("token", res.access_token)
    set({ user: res.user, token: res.access_token })
  },

  logout: () => {
    localStorage.removeItem("token")
    set({ user: null, token: null })
  },

  loadUser: async () => {
    const token = localStorage.getItem("token")
    if (!token) {
      set({ isLoading: false })
      return
    }
    try {
      const user = await api.me()
      set({ user, token, isLoading: false })
    } catch {
      localStorage.removeItem("token")
      set({ user: null, token: null, isLoading: false })
    }
  },
}))
