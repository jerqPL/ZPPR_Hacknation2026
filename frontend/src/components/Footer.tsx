import { ExternalLink } from "lucide-react";

const OFFICIAL_SOURCES = [
  { label: "ZUS (www.zus.pl)", href: "https://www.zus.pl" },
  {
    label: "MRPiPS — Urlop rodzicielski",
    href: "https://www.gov.pl/web/rodzina/urlop-rodzicielski",
  },
  {
    label: "PIP — Porady prawne: Rodzicielstwo",
    href: "https://www.pip.gov.pl/dla-pracodawcow/porady-prawne/rodzicielstwo",
  },
  {
    label: "gov.pl — Rejestr Stanu Cywilnego",
    href: "https://www.gov.pl/web/cyfryzacja/rejestr-stanu-cywilnego",
  },
];

export function Footer() {
  return (
    <footer className="mt-16 border-t border-slate-200 bg-white dark:border-emerald-950 dark:bg-[#0f1914]">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        <div className="grid gap-6 md:grid-cols-2">
          <div>
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              Zasiłkowy Przewodnik Przyszłego Rodzica (ZPPR)
            </h2>
            <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
              Narzędzie informacyjno-kalkulacyjne wspierające przyszłych rodziców w ustalaniu
              uprawnień do świadczeń z ubezpieczenia chorobowego i macierzyńskiego w 2026 roku.
              Integracje z mObywatel, PUE/eZUS, e-ZLA, stanem zadłużenia oraz składaniem wniosków
              działają w trybie symulacji.
            </p>
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              Wyliczenia mają charakter informacyjny i opierają się na ustawie zasiłkowej oraz
              Kodeksie pracy (stan prawny 2026).
            </p>
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              Oficjalne źródła informacji
            </h3>
            <ul className="mt-2 space-y-1.5 text-xs">
              {OFFICIAL_SOURCES.map((link) => (
                <li key={link.href}>
                  <a
                    href={link.href}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 text-[#007834] hover:underline dark:text-emerald-400"
                  >
                    <span>{link.label}</span>
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </footer>
  );
}
