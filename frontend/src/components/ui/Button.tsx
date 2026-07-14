"use client"

import { cn } from "@/lib/utils"
import { forwardRef, ButtonHTMLAttributes } from "react"

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "success"
  size?: "sm" | "md" | "lg"
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center rounded-lg font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 disabled:opacity-50 disabled:cursor-not-allowed",
          {
            "bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800": variant === "primary",
            "bg-gray-800 text-gray-200 hover:bg-gray-700 border border-gray-700": variant === "secondary",
            "bg-transparent text-gray-400 hover:text-white hover:bg-gray-800": variant === "ghost",
            "bg-red-600 text-white hover:bg-red-700": variant === "danger",
            "bg-green-600 text-white hover:bg-green-700": variant === "success",
          },
          {
            "px-2 py-1 text-xs": size === "sm",
            "px-4 py-2 text-sm": size === "md",
            "px-6 py-3 text-base": size === "lg",
          },
          className
        )}
        {...props}
      >
        {children}
      </button>
    )
  }
)
Button.displayName = "Button"
