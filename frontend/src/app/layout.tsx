import type { Metadata } from "next"
import "./globals.css"
import { AuthGuard } from "@/components/AuthGuard"

export const metadata: Metadata = {
  title: "TradeAnalyst Pro - AI Trading Platform",
  description: "Professional AI-powered trading platform with real-time analysis, signals, and Binance Futures integration",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0d1117] text-gray-100 antialiased font-sans">
        <AuthGuard>{children}</AuthGuard>
      </body>
    </html>
  )
}
