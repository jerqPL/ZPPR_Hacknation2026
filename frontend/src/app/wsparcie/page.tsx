"use client";

import { useEffect, useState } from "react";
import { ExternalLink } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { api } from "@/lib/api";
import type { OfficialLink, SupportOrganization } from "@/lib/types";

export default function SupportPage() {
  const [orgs, setOrgs] = useState<SupportOrganization[]>([]);
  const [links, setLinks] = useState<OfficialLink[]>([]);

  useEffect(() => {
    api.getSupportOrganizations().then(setOrgs).catch(() => setOrgs([]));
    api.getOfficialLinks().then(setLinks).catch(() => setLinks([]));
  }, []);

  return (
    <div>
      <PageHeader
        badge="Moduł 7 • Szczególne sytuacje"
        title="Wsparcie w trudnych sytuacjach i podmioty charytatywne"
        description="Rzetelne informacje o uprawnieniach w przypadku urodzenia martwego dziecka, zgonu dziecka, wcześniactwa lub ciężkiej choroby oraz katalog podmiotów o charakterze wyłącznie charytatywnym."
      />

      {/* Najważniejsze uprawnienia w trudnych sytuacjach */}
      <section className="mb-8 grid gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
          <h2 className="text-sm font-bold text-slate-900">Urodzenie martwego dziecka</h2>
          <p className="mt-2 text-xs leading-relaxed text-slate-600">
            Przysługuje zasiłek macierzyński za okres urlopu macierzyńskiego w wymiarze{" "}
            <strong>8 tygodni</strong> po porodzie (nie krócej niż 7 dni od dnia zgonu). Podstawą
            jest akt urodzenia z adnotacją o martwym urodzeniu lub zaświadczenie lekarskie.
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
          <h2 className="text-sm font-bold text-slate-900">Wcześniak / hospitalizacja</h2>
          <p className="mt-2 text-xs leading-relaxed text-slate-600">
            Rodzicom przysługuje <strong>uzupełniający urlop macierzyński</strong> (do 8 lub 15
            tygodni w zależności od tygodnia ciąży, masy urodzeniowej i czasu hospitalizacji) płatny
            w 100% podstawy wymiaru.
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
          <h2 className="text-sm font-bold text-slate-900">
            Ciężka choroba lub śmierć matki dziecka
          </h2>
          <p className="mt-2 text-xs leading-relaxed text-slate-600">
            Ojciec dziecka może przejąć urlop macierzyński wcześniej niż po 14 tygodniach w razie
            hospitalizacji matki, orzeczenia o niezdolności do samodzielnej egzystencji lub jej
            śmierci.
          </p>
        </div>
      </section>

      {/* Organizacje wyłącznie charytatywne */}
      <section className="mb-8">
        <h2 className="text-lg font-bold text-slate-900">
          Organizacje i fundacje charytatywne (non-profit)
        </h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {orgs.map((org) => (
            <div
              key={org.name}
              className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-xs"
            >
              <div>
                <span className="rounded-full bg-[#e6f4ec] px-2.5 py-0.5 text-[11px] font-semibold text-[#005a27]">
                  {org.category.replace("_", " ")}
                </span>
                <h3 className="mt-2 text-sm font-bold text-slate-900">{org.name}</h3>
                <p className="mt-1.5 text-xs leading-relaxed text-slate-600">{org.description}</p>
              </div>
              <a
                href={org.website}
                target="_blank"
                rel="noreferrer"
                className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-[#007834] hover:underline"
              >
                Odwiedź stronę fundacji
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>
          ))}
        </div>
      </section>

      {/* Oficjalne przekierowania */}
      <section>
        <h2 className="text-lg font-bold text-slate-900">Oficjalne portale państwowe</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          {links.map((l) => (
            <a
              key={l.url}
              href={l.url}
              target="_blank"
              rel="noreferrer"
              className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs transition hover:border-[#007834]"
            >
              <p className="text-xs font-bold text-[#007834]">{l.institution}</p>
              <p className="mt-1 text-sm font-bold text-slate-900">{l.title}</p>
              <p className="mt-1 text-xs text-slate-600">{l.description}</p>
            </a>
          ))}
        </div>
      </section>
    </div>
  );
}
