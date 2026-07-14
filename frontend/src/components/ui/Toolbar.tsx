"use client"

import { cn } from "@/lib/utils"

interface ToolbarProps {
  children: React.ReactNode
  className?: string
}

export function Toolbar({ children, className }: ToolbarProps) {
  return (
    <div className={cn("flex items-center gap-1 p-1 bg-gray-800/50 rounded-lg", className)}>
      {children}
    </div>
  )
}

export function ToolbarButton({
  icon: Icon,
  label,
  active,
  onClick,
  className,
}: {
  icon: React.ElementType
  label: string
  active?: boolean
  onClick?: () => void
  className?: string
}) {
  return (
    <button
      title={label}
      onClick={onClick}
      className={cn(
        "p-1.5 rounded-md transition-colors",
        active
          ? "bg-blue-600/30 text-blue-400"
          : "text-gray-500 hover:text-gray-300 hover:bg-gray-700/50",
        className
      )}
    >
      <Icon className="w-4 h-4" />
    </button>
  )
}
