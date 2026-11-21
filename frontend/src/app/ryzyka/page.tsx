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
            className="rounded-xl border border-[#CCC5B9] bg-[#FFFCF2] p-5 shadow-xs"
          >
            <div className="flex items-center justify-between gap-2">
              <span
                className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold uppercase ${
                  risk.severity === "high"
                    ? "bg-[#000000] text-[#FFFCF2]"
                    : risk.severity === "medium"
                    ? "bg-[#CCC5B9] text-[#000000]"
                    : "bg-[#F5F1E6] border border-[#CCC5B9] text-[#000000]"
                }`}
              >
                {risk.severity === "high"
                  ? "Wysokie ryzyko"
                  : risk.severity === "medium"
                  ? "Ważny termin"
                  : "Informacja prawna"}
              </span>
              <span className="text-[11px] text-[#403D39]/80">{risk.applies_to.join(" • ")}</span>
            </div>
            <h2 className="mt-3 text-base font-bold text-[#000000]">{risk.title}</h2>
            <p className="mt-2 text-xs leading-relaxed text-[#403D39]">{risk.description}</p>
            <div className="mt-3 rounded-lg bg-[#F5F1E6] p-3 text-xs text-[#000000]">
              <strong>Jak uniknąć problemu:</strong> {risk.how_to_avoid}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
