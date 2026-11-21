"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Clock, Info, ShieldCheck } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { api } from "@/lib/api";
import type { RiskItem } from "@/lib/types";

type SeverityFilter = "all" | "high" | "medium" | "info";

const SEVERITY_META = {
  high: {
    label: "Wysokie ryzyko",
    icon: AlertTriangle,
    badgeClass:
      "border border-red-200 bg-red-50 text-red-700 dark:border-red-500/30 dark:bg-red-500/15 dark:text-red-300",
    accentClass: "border-l-red-500 dark:border-l-red-500/80",
  },
  medium: {
    label: "Ważny termin",
    icon: Clock,
    badgeClass:
      "border border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/15 dark:text-amber-300",
    accentClass: "border-l-amber-500 dark:border-l-amber-400/80",
  },
  info: {
    label: "Informacja prawna",
    icon: Info,
    badgeClass:
      "border border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-500/30 dark:bg-sky-500/15 dark:text-sky-300",
    accentClass: "border-l-sky-500 dark:border-l-sky-400/80",
  },
} as const;

export default function RisksPage() {
  const [risks, setRisks] = useState<RiskItem[]>([]);
  const [filter, setFilter] = useState<SeverityFilter>("all");

  useEffect(() => {
    api.getRisks().then(setRisks).catch(() => setRisks([]));
  }, []);

  const filtered = filter === "all" ? risks : risks.filter((r) => r.severity === filter);

  return (
    <div>
      <PageHeader
        badge="Ochrona i bezpieczeństwo"
        title="Zagrożenia, ryzyka utraty zasiłku i szczególna ochrona prawna"
        description="Poznaj najczęstsze przyczyny sporów z ZUS, obniżenia podstawy zasiłku lub utraty prawa do świadczeń oraz zasady ochrony kobiet w ciąży w Kodeksie pracy."
      />

      {/* Filter pills */}
      <div className="mb-6 flex flex-wrap gap-2">
        {(
          [
            { id: "all", label: `Wszystkie (${risks.length})` },
            { id: "high", label: "Wysokie ryzyko" },
            { id: "medium", label: "Ważne terminy" },
            { id: "info", label: "Informacje prawne" },
          ] as const
        ).map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setFilter(tab.id)}
            className={`rounded-full border px-3.5 py-1.5 text-xs font-semibold transition ${
              filter === tab.id
                ? "border-[#007834] bg-[#007834] text-white shadow-xs"
                : "border-slate-200 bg-white text-slate-600 hover:border-[#007834]/50 hover:bg-slate-50 dark:border-emerald-950 dark:bg-[#101b16] dark:text-slate-300 dark:hover:border-emerald-700 dark:hover:bg-[#182920]"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        {filtered.map((risk) => {
          const meta = SEVERITY_META[risk.severity] ?? SEVERITY_META.info;
          const Icon = meta.icon;
          return (
            <article
              key={risk.id}
              className={`flex flex-col justify-between rounded-2xl border border-slate-200/90 border-l-4 bg-white p-6 shadow-xs transition hover:shadow-md dark:border-emerald-950/90 dark:bg-[#101b16] ${meta.accentClass}`}
            >
              <div>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span
                    className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-bold tracking-wide uppercase ${meta.badgeClass}`}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {meta.label}
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {risk.applies_to.map((tag) => (
                      <span
                        key={tag}
                        className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600 dark:bg-slate-800/80 dark:text-slate-300"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>

                <h2 className="mt-4 text-base font-bold leading-snug text-slate-900 dark:text-white">
                  {risk.title}
                </h2>
                <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-300">
                  {risk.description}
                </p>
              </div>

              <div className="mt-5 flex items-start gap-2.5 rounded-xl border border-[#007834]/20 bg-[#e6f4ec]/70 p-3.5 text-xs text-[#005a27] dark:border-emerald-700/40 dark:bg-emerald-950/45 dark:text-emerald-200">
                <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-[#007834] dark:text-emerald-400" />
                <div>
                  <span className="font-bold">Jak uniknąć problemu: </span>
                  <span>{risk.how_to_avoid}</span>
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
