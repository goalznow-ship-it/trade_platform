import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "TradeAnalyst Pro - AI Trading Platform",
  description: "Professional AI-powered trading platform with real-time analysis, signals, and Binance Futures integration",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-[#0d1117] text-gray-100 antialiased`}>
        {children}
      </body>
    </html>
  )
}
