import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatPrice(price: number | null | undefined, decimals = 2): string {
  if (price == null) return "$0.00"
  return "$" + price.toFixed(decimals)
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

export function formatTime(timestamp: number): string {
  const d = new Date(timestamp * 1000)
  return d.toLocaleTimeString("en-US", { hour12: false })
}

export function formatDate(timestamp: number): string {
  const d = new Date(timestamp * 1000)
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
}
