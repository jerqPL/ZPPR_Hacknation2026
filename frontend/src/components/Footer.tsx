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
    <footer className="mt-16 border-t border-slate-200 bg-white">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        <div className="grid gap-6 md:grid-cols-2">
          <div>
            <h2 className="text-sm font-bold text-slate-900">
              Zasiłkowy Przewodnik Przyszłego Rodzica (ZPPR)
            </h2>
            <p className="mt-2 text-xs leading-relaxed text-slate-600">
              Prototyp narzędzia informacyjno-kalkulacyjnego przygotowany na HackNation 2026
              (wyzwanie ZUS). Logowanie mObywatel, pobieranie danych ZUS, stan zadłużenia,
              e-ZLA, PUE/eZUS oraz wysyłka wniosków działają w trybie symulacji.
            </p>
            <p className="mt-2 text-xs text-slate-500">
              <strong>Zakres użycia AI:</strong> Szkielet aplikacji wykorzystuje deterministyczny
              silnik reguł prawnych (bez halucynacji w wyliczeniach); architektura przewiduje
              opcjonalne wsparcie AI do OCR skanowanych wniosków PDF oraz asystenta wyjaśnień.
            </p>
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">Oficjalne źródła informacji</h3>
            <ul className="mt-2 space-y-1.5 text-xs">
              {OFFICIAL_SOURCES.map((link) => (
                <li key={link.href}>
                  <a
                    href={link.href}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 text-[#007834] hover:underline"
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
