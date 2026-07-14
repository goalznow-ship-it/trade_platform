"use client"

import { cn } from "@/lib/utils"

interface BadgeProps {
  variant?: "default" | "success" | "danger" | "warning" | "info"
  children: React.ReactNode
  className?: string
}

export function Badge({ variant = "default", children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        {
          "bg-gray-800 text-gray-300": variant === "default",
          "bg-green-900/50 text-green-400": variant === "success",
          "bg-red-900/50 text-red-400": variant === "danger",
          "bg-yellow-900/50 text-yellow-400": variant === "warning",
          "bg-blue-900/50 text-blue-400": variant === "info",
        },
        className
      )}
    >
      {children}
    </span>
  )
}
