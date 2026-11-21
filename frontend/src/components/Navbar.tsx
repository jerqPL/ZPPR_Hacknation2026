"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Menu, X, ShieldCheck, LogOut, Moon, Sun } from "lucide-react";
import { useUser } from "./UserContext";
import { useTheme } from "./ThemeContext";

const NAV_ITEMS = [
  { href: "/", label: "Start" },
  { href: "/ciaza", label: "Ciąża" },
  { href: "/kalkulator", label: "Kalkulator" },
  { href: "/sprawy-pdf", label: "Sprawy PDF" },
  { href: "/dokumenty", label: "Dokumenty" },
  { href: "/pue-zus", label: "mObywatel / ZUS" },
  { href: "/ryzyka", label: "Ryzyka" },
  { href: "/wsparcie", label: "Wsparcie" },
  { href: "/admin", label: "Admin" },
];

export function Navbar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const { user, logout } = useUser();
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur dark:border-emerald-950 dark:bg-[#0f1914]/95">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#007834] text-sm font-bold text-white shadow-sm">
            ZUS
          </span>
          <div className="leading-tight">
            <p className="text-sm font-bold text-slate-900 dark:text-slate-100 sm:text-base">
              Zasiłkowy Przewodnik
            </p>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              Przyszłego Rodzica • 2026
            </p>
          </div>
        </Link>

        {/* Desktop navigation */}
        <nav className="hidden items-center gap-1 lg:flex" aria-label="Nawigacja główna">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
                  active
                    ? "bg-[#e6f4ec] text-[#005a27] dark:bg-[#007834]/25 dark:text-emerald-300"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Theme toggle, user badge, mobile menu */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={toggleTheme}
            aria-label={theme === "dark" ? "Przełącz na jasny motyw" : "Przełącz na ciemny motyw"}
            title={theme === "dark" ? "Jasny motyw" : "Ciemny motyw"}
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>

          {user ? (
            <div className="hidden items-center gap-2 rounded-full border border-[#007834]/30 bg-[#e6f4ec] px-3 py-1 text-xs font-medium text-[#005a27] dark:border-emerald-700/50 dark:bg-[#007834]/25 dark:text-emerald-200 sm:flex">
              <ShieldCheck className="h-3.5 w-3.5" />
              <span>{user.full_name}</span>
              <button
                onClick={logout}
                title="Wyloguj (symulacja)"
                className="ml-1 rounded p-0.5 hover:bg-white/60 dark:hover:bg-black/30"
              >
                <LogOut className="h-3.5 w-3.5" />
              </button>
            </div>
          ) : (
            <Link
              href="/pue-zus"
              className="hidden rounded-lg bg-[#007834] px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-[#005a27] sm:inline-flex"
            >
              Zaloguj przez mObywatel
            </Link>
          )}

          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="inline-flex items-center justify-center rounded-md p-2 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800 lg:hidden"
            aria-label="Otwórz menu"
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile navigation drawer */}
      {open && (
        <nav className="border-t border-slate-200 bg-white px-4 py-3 dark:border-emerald-950 dark:bg-[#0f1914] lg:hidden">
          <div className="flex flex-col gap-1">
            {NAV_ITEMS.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setOpen(false)}
                  className={`rounded-md px-3 py-2 text-sm font-medium ${
                    active
                      ? "bg-[#e6f4ec] text-[#005a27] dark:bg-[#007834]/25 dark:text-emerald-300"
                      : "text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        </nav>
      )}
    </header>
  );
}
