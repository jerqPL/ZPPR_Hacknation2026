"use client";

import { HelpCircle } from "lucide-react";

interface InfoTooltipProps {
  label: string;
  tooltip: string;
  className?: string;
}

export function InfoTooltip({ label, tooltip, className = "" }: InfoTooltipProps) {
  return (
    <span
      tabIndex={0}
      className={`group relative inline-flex cursor-help items-center gap-1 focus:outline-none ${className}`}
    >
      <span className="border-b border-dotted border-slate-400 dark:border-slate-500">
        {label}
      </span>
      <HelpCircle className="h-4 w-4 shrink-0 text-[#007834] opacity-80 transition group-hover:opacity-100 dark:text-emerald-400" />
      <span
        role="tooltip"
        className="pointer-events-none invisible absolute bottom-full left-0 z-50 mb-2 w-64 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-normal leading-relaxed text-white opacity-0 shadow-lg transition-all duration-150 group-hover:visible group-hover:opacity-100 group-focus:visible group-focus:opacity-100 dark:border-slate-200 dark:bg-slate-100 dark:text-slate-900 sm:w-80"
      >
        {tooltip}
        <span className="absolute top-full left-4 border-4 border-transparent border-t-slate-900 dark:border-t-slate-100" />
      </span>
    </span>
  );
}
