import Link from "next/link";
import {
  Baby,
  Calculator,
  FileCheck2,
  FileSearch,
  HeartHandshake,
  ShieldAlert,
  Settings,
  UserCheck,
  ArrowRight,
} from "lucide-react";

const MODULES = [
  {
    href: "/pue-zus",
    title: "Logowanie mObywatel i dane z ZUS",
    desc: "Symulacja logowania, pobrania okresu ubezpieczenia, stanu zadłużenia (JDG), e-ZLA oraz zapytania PUE/eZUS.",
    icon: UserCheck,
    tag: "Symulacja integracji",
  },
  {
    href: "/ciaza",
    title: "Świadczenia w czasie ciąży",
    desc: "Sprawdź prawo do zasiłku chorobowego (kod B — 100%, 270 dni), świadczenia rehabilitacyjnego i zasiłku w wys. macierzyńskiego.",
    icon: Baby,
    tag: "Okres ciąży",
  },
  {
    href: "/kalkulator",
    title: "Zintegrowany Kalkulator Zasiłkowy",
    desc: "Macierzyński, uzupełniający (wcześniak), rodzicielski (w tym Za życiem), ojcowski, podział opieki, łączenie z pracą, adopcja.",
    icon: Calculator,
    tag: "Wszystkie tryby",
  },
  {
    href: "/sprawy-pdf",
    title: "Weryfikacja spraw i wniosków PDF",
    desc: "Prześlij formularz ZUS (ZAM, Z-3, Z-3a) lub wybierz przykładową sprawę testową i sprawdź poprawność wyliczeń.",
    icon: FileSearch,
    tag: "Testowanie spraw",
  },
  {
    href: "/dokumenty",
    title: "Dokumenty, terminy i kreator wniosków",
    desc: "Dowiedz się, kto wypłaca zasiłek (płatnik >20 vs ZUS) i zasymuluj złożenie wniosku o urlop, ZAM lub akt urodzenia (USC).",
    icon: FileCheck2,
    tag: "Procedury 2026",
  },
  {
    href: "/ryzyka",
    title: "Zagrożenia i ochrona prawna",
    desc: "Uniknij utraty lub obniżenia zasiłku (pozorność umowy, zadłużenie JDG, termin 21 dni) oraz poznaj ochronę z Kodeksu pracy.",
    icon: ShieldAlert,
    tag: "Bezpieczeństwo",
  },
  {
    href: "/wsparcie",
    title: "Wsparcie w szczególnych sytuacjach",
    desc: "Uprawnienia i lista wyłącznie charytatywnych fundacji (wcześniaki, urodzenie martwego dziecka, dziecko ciężko chore).",
    icon: HeartHandshake,
    tag: "Pomoc",
  },
  {
    href: "/admin",
    title: "Panel administracyjny",
    desc: "Konfiguracja parametrów prawnych (stawki %, wymiary urlopów, płaca minimalna 2026) na wypadek zmian legislacyjnych.",
    icon: Settings,
    tag: "Parametryzacja",
  },
];

export default function HomePage() {
  return (
    <div className="space-y-10">
      {/* Hero section */}
      <section className="rounded-2xl bg-gradient-to-br from-[#007834] to-[#004d21] p-6 text-white shadow-md sm:p-10">
        <span className="inline-block rounded-full bg-white dark:bg-[#111c17]/15 px-3 py-1 text-xs font-semibold tracking-wide">
          HackNation 2026 • Wyzwanie ZUS
        </span>
        <h1 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">
          Zasiłkowy Przewodnik Przyszłego Rodzica
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-emerald-50 sm:text-base">
          Sprawdź swoje uprawnienia z ubezpieczenia chorobowego w ciąży i po narodzinach lub
          przyjęciu dziecka na wychowanie. Zaplanuj urlopy, oblicz wysokość zasiłku i przygotuj
          komplet dokumentów bez stresu i niespodzianek.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            href="/kalkulator"
            className="inline-flex items-center gap-2 rounded-lg bg-white dark:bg-[#111c17] px-5 py-2.5 text-sm font-semibold text-[#005a27] dark:text-emerald-300 shadow-sm transition hover:bg-emerald-50"
          >
            Otwórz zintegrowany kalkulator
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/pue-zus"
            className="inline-flex items-center gap-2 rounded-lg border border-white/40 bg-white dark:bg-[#111c17]/10 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-white dark:bg-[#111c17]/20"
          >
            Zaloguj przez mObywatel (symulacja)
          </Link>
        </div>
      </section>

      {/* Modules grid */}
      <section>
        <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">Moduły przewodnika</h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Wybierz ścieżkę dopasowaną do Twojego etapu — od planowania ciąży po podział urlopu
          rodzicielskiego i powrót do pracy.
        </p>

        <div className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {MODULES.map((m) => {
            const Icon = m.icon;
            return (
              <Link
                key={m.href}
                href={m.href}
                className="group flex flex-col justify-between rounded-xl border border-slate-200 dark:border-emerald-950 bg-white dark:bg-[#111c17] p-5 shadow-xs transition hover:border-[#007834] hover:shadow-md"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#e6f4ec] dark:bg-[#007834]/20 text-[#007834] dark:text-emerald-400">
                      <Icon className="h-5 w-5" />
                    </span>
                    <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2.5 py-0.5 text-[11px] font-medium text-slate-600 dark:text-slate-400">
                      {m.tag}
                    </span>
                  </div>
                  <h3 className="mt-4 text-base font-bold text-slate-900 dark:text-slate-100 group-hover:text-[#007834] dark:text-emerald-400">
                    {m.title}
                  </h3>
                  <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">{m.desc}</p>
                </div>
                <div className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-[#007834] dark:text-emerald-400">
                  Przejdź
                  <ArrowRight className="h-3.5 w-3.5 transition group-hover:translate-x-0.5" />
                </div>
              </Link>
            );
          })}
        </div>
      </section>
    </div>
  );
}
