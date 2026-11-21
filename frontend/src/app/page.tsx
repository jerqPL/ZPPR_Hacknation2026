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
  Sparkles,
} from "lucide-react";

const MODULES = [
  {
    href: "/pue-zus",
    title: "Konto ZUS i mObywatel",
    desc: "Sprawdź status ubezpieczenia chorobowego, saldo składek (JDG), wystawione zwolnienia e-ZLA oraz wyślij zapytanie przez PUE/eZUS.",
    icon: UserCheck,
    tag: "e-Usługi",
  },
  {
    href: "/ciaza",
    title: "Świadczenia w czasie ciąży",
    desc: "Oblicz zasiłek chorobowy z kodem B (100% do 270 dni), świadczenie rehabilitacyjne oraz zasiłek w wysokości zasiłku macierzyńskiego.",
    icon: Baby,
    tag: "Okres ciąży",
  },
  {
    href: "/kalkulator",
    title: "Zintegrowany Kalkulator Zasiłkowy",
    desc: "Urlop macierzyński, uzupełniający (wcześniak), rodzicielski (w tym „Za życiem”), ojcowski, podział opieki, łączenie z pracą i adopcja.",
    icon: Calculator,
    tag: "Kalkulator",
  },
  {
    href: "/sprawy-pdf",
    title: "Weryfikacja wniosków PDF",
    desc: "Prześlij formularz ZUS (ZAM, Z-3, Z-3a) lub wybierz przykładową sprawę, aby automatycznie zweryfikować ubezpieczenie i kwoty.",
    icon: FileSearch,
    tag: "Analiza PDF",
  },
  {
    href: "/dokumenty",
    title: "Dokumenty, terminy i wnioski",
    desc: "Sprawdź, gdzie złożyć dokumenty (pracodawca czy ZUS) i przygotuj wniosek o urlop, formularz ZAM lub odpis aktu urodzenia.",
    icon: FileCheck2,
    tag: "Procedury",
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
    desc: "Uprawnienia oraz katalog sprawdzonych fundacji charytatywnych (wcześniaki, urodzenie martwego dziecka, dziecko ciężko chore).",
    icon: HeartHandshake,
    tag: "Pomoc",
  },
  {
    href: "/admin",
    title: "Panel administracyjny",
    desc: "Zarządzanie parametrami prawnymi (stawki procentowe, wymiary urlopów, płaca minimalna 2026) w razie zmian legislacyjnych.",
    icon: Settings,
    tag: "Konfiguracja",
  },
];

const HIGHLIGHTS = [
  { value: "100%", label: "Zasiłek chorobowy w ciąży (kod B) i macierzyński" },
  { value: "270 dni", label: "Maksymalny okres zasiłkowy w ciąży" },
  { value: "81,5%", label: "Równa stawka przy wniosku w ciągu 21 dni" },
  { value: "9 tyg.", label: "Nieprzenoszalny urlop dla drugiego rodzica" },
];

export default function HomePage() {
  return (
    <div className="space-y-12">
      {/* Hero section */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#007834] via-[#00662c] to-[#00421c] p-7 text-white shadow-xl shadow-emerald-950/15 sm:p-12">
        <div
          aria-hidden
          className="pointer-events-none absolute -top-24 -right-24 h-72 w-72 rounded-full bg-emerald-300/15 blur-3xl"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -bottom-24 left-1/3 h-64 w-64 rounded-full bg-white/10 blur-3xl"
        />

        <div className="relative z-10 max-w-3xl">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-3.5 py-1 text-xs font-semibold tracking-wide text-emerald-50 backdrop-blur-xs">
            <Sparkles className="h-3.5 w-3.5" />
            Zakład Ubezpieczeń Społecznych • Stan prawny 2026
          </span>
          <h1 className="mt-5 text-3xl font-extrabold tracking-tight text-white sm:text-5xl sm:leading-[1.1]">
            Zasiłkowy Przewodnik Przyszłego Rodzica
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-relaxed text-emerald-50/90 sm:text-base">
            Wszystkie informacje o świadczeniach w ciąży i po narodzinach lub przyjęciu dziecka w
            jednym miejscu. Oblicz wysokość zasiłku, zaplanuj podział urlopów i przygotuj komplet
            dokumentów bez stresu i niespodzianek.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link
              href="/kalkulator"
              className="inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-semibold text-[#005a27] shadow-md shadow-black/10 transition hover:-translate-y-0.5 hover:bg-emerald-50 dark:bg-[#0e1a14] dark:text-emerald-300 dark:hover:bg-[#15261e]"
            >
              Otwórz zintegrowany kalkulator
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/pue-zus"
              className="inline-flex items-center gap-2 rounded-xl border border-white/35 bg-white/10 px-5 py-3 text-sm font-semibold text-white backdrop-blur-xs transition hover:-translate-y-0.5 hover:bg-white/20"
            >
              Zaloguj przez mObywatel
            </Link>
          </div>
        </div>

        {/* Key figures strip */}
        <div className="relative z-10 mt-10 grid gap-3 border-t border-white/15 pt-6 sm:grid-cols-2 lg:grid-cols-4">
          {HIGHLIGHTS.map((item) => (
            <div
              key={item.label}
              className="rounded-2xl border border-white/15 bg-black/15 px-4 py-3 backdrop-blur-xs"
            >
              <p className="text-xl font-extrabold tracking-tight text-white">{item.value}</p>
              <p className="mt-0.5 text-xs leading-snug text-emerald-100/85">{item.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Modules grid */}
      <section>
        <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-end">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              W czym możemy Ci pomóc?
            </h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
              Wybierz narzędzie dopasowane do Twojej sytuacji — od planowania ciąży po powrót do
              pracy.
            </p>
          </div>
        </div>

        <div className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {MODULES.map((m) => {
            const Icon = m.icon;
            return (
              <Link
                key={m.href}
                href={m.href}
                className="group flex flex-col justify-between rounded-2xl border border-slate-200/90 bg-white p-5 shadow-xs transition duration-200 hover:-translate-y-1 hover:border-[#007834]/60 hover:shadow-lg hover:shadow-emerald-950/5 dark:border-emerald-950/90 dark:bg-[#101b16] dark:hover:border-emerald-600/60 dark:hover:bg-[#14231c]"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#e6f4ec] text-[#007834] transition group-hover:bg-[#007834] group-hover:text-white dark:bg-[#007834]/20 dark:text-emerald-400 dark:group-hover:bg-[#007834] dark:group-hover:text-white">
                      <Icon className="h-5 w-5" />
                    </span>
                    <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-[11px] font-medium text-slate-600 dark:border-slate-800 dark:bg-slate-900/70 dark:text-slate-400">
                      {m.tag}
                    </span>
                  </div>
                  <h3 className="mt-4 text-base font-bold text-slate-900 transition group-hover:text-[#007834] dark:text-slate-100 dark:group-hover:text-emerald-400">
                    {m.title}
                  </h3>
                  <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                    {m.desc}
                  </p>
                </div>
                <div className="mt-5 inline-flex items-center gap-1.5 text-xs font-semibold text-[#007834] dark:text-emerald-400">
                  Otwórz narzędzie
                  <ArrowRight className="h-3.5 w-3.5 transition group-hover:translate-x-1" />
                </div>
              </Link>
            );
          })}
        </div>
      </section>
    </div>
  );
}
