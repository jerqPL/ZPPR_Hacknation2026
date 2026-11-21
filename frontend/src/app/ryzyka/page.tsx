"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { api } from "@/lib/api";
import type { RiskItem } from "@/lib/types";

export default function RisksPage() {
  const [risks, setRisks] = useState<RiskItem[]>([]);

  useEffect(() => {
    api.getRisks().then(setRisks).catch(() => setRisks([]));
  }, []);

  return (
    <div>
      <PageHeader
        badge="Moduł 6 • Bezpieczeństwo uprawnień"
        title="Zagrożenia, ryzyka utraty zasiłku i szczególna ochrona prawna"
        description="Poznaj najczęstsze przyczyny sporów z ZUS, obniżenia podstawy zasiłku lub utraty prawa do świadczeń oraz zasady ochrony kobiet w ciąży w Kodeksie pracy."
      />

      <div className="grid gap-4 md:grid-cols-2">
        {risks.map((risk) => (
          <article
            key={risk.id}
            className="rounded-xl border border-slate-200 dark:border-emerald-950 bg-white dark:bg-[#111c17] p-5 shadow-xs"
          >
            <div className="flex items-center justify-between gap-2">
              <span
                className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold uppercase ${
                  risk.severity === "high"
                    ? "bg-red-100 text-red-800 dark:text-red-200"
                    : risk.severity === "medium"
                    ? "bg-amber-100 text-amber-800"
                    : "bg-sky-100 text-sky-800"
                }`}
              >
                {risk.severity === "high"
                  ? "Wysokie ryzyko"
                  : risk.severity === "medium"
                  ? "Ważny termin"
                  : "Informacja prawna"}
              </span>
              <span className="text-[11px] text-slate-500 dark:text-slate-400">{risk.applies_to.join(" • ")}</span>
            </div>
            <h2 className="mt-3 text-base font-bold text-slate-900 dark:text-slate-100">{risk.title}</h2>
            <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">{risk.description}</p>
            <div className="mt-3 rounded-lg bg-[#e6f4ec] dark:bg-[#007834]/20 p-3 text-xs text-[#005a27] dark:text-emerald-300">
              <strong>Jak uniknąć problemu:</strong> {risk.how_to_avoid}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
