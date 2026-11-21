"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Menu, X, ShieldCheck, LogOut } from "lucide-react";
import { useUser } from "./UserContext";

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

  return (
    <header className="sticky top-0 z-40 border-b border-[#CCC5B9] bg-[#FFFCF2]/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3.5 sm:px-6">
        <Link href="/" className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-md bg-[#000000] text-xs font-bold tracking-wider text-[#FFFCF2]">
            ZUS
          </span>
          <div className="leading-tight">
            <p className="text-sm font-bold tracking-tight text-[#000000] sm:text-base">
              Zasiłkowy Przewodnik
            </p>
            <p className="text-[11px] text-[#403D39]">Przyszłego Rodzica • 2026</p>
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
                    ? "bg-[#000000] text-[#FFFCF2]"
                    : "text-[#403D39] hover:bg-[#CCC5B9]/40 hover:text-[#000000]"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* User badge / mobile menu button */}
        <div className="flex items-center gap-2">
          {user ? (
            <div className="hidden items-center gap-2 rounded-full border border-[#000000] bg-[#F5F1E6] px-3 py-1 text-xs font-medium text-[#000000] sm:flex">
              <ShieldCheck className="h-3.5 w-3.5" />
              <span>{user.full_name}</span>
              <button
                onClick={logout}
                title="Wyloguj (symulacja)"
                className="ml-1 rounded p-0.5 hover:bg-[#CCC5B9]/50"
              >
                <LogOut className="h-3.5 w-3.5" />
              </button>
            </div>
          ) : (
            <Link
              href="/pue-zus"
              className="hidden rounded-md bg-[#000000] px-3.5 py-2 text-xs font-semibold text-[#FFFCF2] transition hover:bg-[#262522] sm:inline-flex"
            >
              Zaloguj przez mObywatel
            </Link>
          )}

          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="inline-flex items-center justify-center rounded-md p-2 text-[#000000] hover:bg-[#CCC5B9]/40 lg:hidden"
            aria-label="Otwórz menu"
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile navigation drawer */}
      {open && (
        <nav className="border-t border-[#CCC5B9] bg-[#FFFCF2] px-4 py-3 lg:hidden">
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
                      ? "bg-[#000000] text-[#FFFCF2]"
                      : "text-[#403D39] hover:bg-[#CCC5B9]/40 hover:text-[#000000]"
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
