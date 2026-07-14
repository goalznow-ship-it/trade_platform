"use client"

import { useState, useRef, useEffect } from "react"
import { cn } from "@/lib/utils"

interface DropdownProps {
  trigger: React.ReactNode
  children: React.ReactNode
  align?: "left" | "right"
  className?: string
}

export function Dropdown({ trigger, children, align = "left", className }: DropdownProps) {
  const [isOpen, setIsOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setIsOpen(false)
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [])

  return (
    <div ref={ref} className="relative">
      <div onClick={() => setIsOpen(!isOpen)}>{trigger}</div>
      {isOpen && (
        <div
          className={cn(
            "absolute z-50 mt-1 min-w-[180px] rounded-lg border border-gray-700 bg-gray-900 shadow-xl py-1",
            align === "right" ? "right-0" : "left-0",
            className
          )}
          onClick={() => setIsOpen(false)}
        >
          {children}
        </div>
      )}
    </div>
  )
}

export function DropdownItem({
  children,
  onClick,
  className,
}: {
  children: React.ReactNode
  onClick?: () => void
  className?: string
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full text-left px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 hover:text-white transition-colors",
        className
      )}
    >
      {children}
    </button>
  )
}
