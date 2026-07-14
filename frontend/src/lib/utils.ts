import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatPrice(price: number | null | undefined, decimals = 2): string {
  if (price == null) return "$0.00"
  if (price >= 1e12) return "$" + (price / 1e12).toFixed(2) + "T"
  if (price >= 1e9) return "$" + (price / 1e9).toFixed(2) + "B"
  if (price >= 1e6) return "$" + (price / 1e6).toFixed(2) + "M"
  if (price >= 1e3 && decimals === 0) return "$" + (price / 1e3).toFixed(1) + "K"
  return "$" + price.toFixed(decimals)
}

export function formatPriceShort(price: number | null | undefined): string {
  if (price == null) return "$0"
  if (price >= 1e12) return "$" + (price / 1e12).toFixed(2) + "T"
  if (price >= 1e9) return "$" + (price / 1e9).toFixed(2) + "B"
  if (price >= 1e6) return "$" + (price / 1e6).toFixed(2) + "M"
  if (price >= 1e3) return "$" + (price / 1e3).toFixed(1) + "K"
  return "$" + price.toFixed(2)
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return "0.00%"
  return (value >= 0 ? "+" : "") + value.toFixed(2) + "%"
}

export function formatVolume(volume: number | null | undefined): string {
  if (volume == null) return "0"
  if (volume >= 1e9) return (volume / 1e9).toFixed(2) + "B"
  if (volume >= 1e6) return (volume / 1e6).toFixed(2) + "M"
  if (volume >= 1e3) return (volume / 1e3).toFixed(2) + "K"
  return volume.toFixed(2)
}

export function formatTime(timestamp: number | string | Date): string {
  const d = new Date(timestamp)
  return d.toLocaleTimeString("en-US", { hour12: false })
}

export function formatDate(timestamp: number | string | Date): string {
  const d = new Date(timestamp)
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
}

export function formatDuration(minutes: number): string {
  if (minutes < 60) return `${minutes}m`
  if (minutes < 1440) return `${Math.floor(minutes / 60)}h ${minutes % 60}m`
  return `${Math.floor(minutes / 1440)}d ${Math.floor((minutes % 1440) / 60)}h`
}

export function getChangeColor(value: number | null | undefined): string {
  if (value == null || value === 0) return "text-gray-400"
  return value >= 0 ? "text-green-400" : "text-red-400"
}

export function getChangeBg(value: number | null | undefined): string {
  if (value == null || value === 0) return "bg-gray-800"
  return value >= 0 ? "bg-green-900/30" : "bg-red-900/30"
}

export function confidenceColor(score: number): string {
  if (score >= 85) return "text-green-400"
  if (score >= 70) return "text-blue-400"
  if (score >= 50) return "text-yellow-400"
  return "text-red-400"
}

export function confidenceBg(score: number): string {
  if (score >= 85) return "bg-green-900/30 border-green-800/30"
  if (score >= 70) return "bg-blue-900/30 border-blue-800/30"
  if (score >= 50) return "bg-yellow-900/30 border-yellow-800/30"
  return "bg-red-900/30 border-red-800/30"
}

export function nowISO(): string {
  return new Date().toISOString()
}

export function ago(timestamp: string | Date): string {
  const diff = Date.now() - new Date(timestamp).getTime()
  const seconds = Math.floor(diff / 1000)
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}
