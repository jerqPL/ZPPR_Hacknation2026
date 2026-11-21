"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { useUser } from "@/components/UserContext";
import { api } from "@/lib/api";
import type { DebtStatusResponse, EzlaCertificate, SimulatedUserProfile } from "@/lib/types";

export default function PueZusSimulationPage() {
  const { user, loginAs, logout, loading } = useUser();
  const [personas, setPersonas] = useState<SimulatedUserProfile[]>([]);
  const [ezla, setEzla] = useState<EzlaCertificate[]>([]);
  const [debt, setDebt] = useState<DebtStatusResponse | null>(null);

  const [subject, setSubject] = useState("Pytanie o podstawę wymiaru zasiłku macierzyńskiego");
  const [message, setMessage] = useState(
    "Proszę o potwierdzenie, czy mój okres dobrowolnego ubezpieczenia chorobowego jest ciągły."
  );
  const [ticketInfo, setTicketInfo] = useState<string | null>(null);

  useEffect(() => {
    api.getPersonas().then(setPersonas).catch(() => setPersonas([]));
  }, []);

  useEffect(() => {
    if (!user) {
      setEzla([]);
      setDebt(null);
      return;
    }
    api.getEzla(user.id).then(setEzla).catch(() => setEzla([]));
    api.getDebtStatus(user.id).then(setDebt).catch(() => setDebt(null));
  }, [user]);

  const handleInquiry = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await api.submitPueInquiry({
      persona_id: user?.id || "uop_standard",
      subject,
      message,
    });
    setTicketInfo(`${res.status} — numer zgłoszenia: ${res.ticket_id} (${res.estimated_response})`);
  };

  return (
    <div>
      <PageHeader
        badge="Moduł 5 • Symulacje e-Usług"
        title="Symulacja mObywatel, danych z ZUS, zadłużenia, e-ZLA i PUE/eZUS"
        description="Wybierz profil testowy, aby zasymulować logowanie przez mObywatel i automatyczne pobranie danych z systemów ZUS do kalkulatorów."
      />

      {/* Wybór persony mObywatel */}
      <section className="rounded-xl border border-slate-200 dark:border-emerald-950 bg-white dark:bg-[#111c17] p-6 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
            1. Logowanie przez mObywatel (wyłącznie symulacja)
          </h2>
          {user && (
            <button
              type="button"
              onClick={logout}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-[#111c17] dark:text-slate-300 dark:hover:bg-[#1e3328]"
            >
              Wyloguj ({user.full_name})
            </button>
          )}
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {personas.map((p) => {
            const active = user?.id === p.id;
            return (
              <button
                key={p.id}
                type="button"
                disabled={loading}
                onClick={() => loginAs(p.id)}
                className={`rounded-xl border p-4 text-left transition ${
                  active
                    ? "border-[#007834] bg-[#e6f4ec] dark:bg-[#007834]/20 ring-1 ring-[#007834]"
                    : "border-slate-200 hover:border-[#007834]/60 hover:bg-slate-50 dark:border-emerald-950 dark:bg-[#111c17] dark:hover:border-emerald-700 dark:hover:bg-[#1e3328]"
                }`}
              >
                <p className="text-sm font-bold text-slate-900 dark:text-slate-100">{p.full_name}</p>
                <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">{p.role_label}</p>
                <p className="mt-2 text-[11px] font-semibold text-[#005a27] dark:text-emerald-300">
                  {active ? "Zalogowano przez mObywatel" : "Kliknij, aby zalogować"}
                </p>
              </button>
            );
          })}
        </div>
      </section>

      {user && (
        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          {/* Dane o ubezpieczeniu */}
          <section className="rounded-xl border border-slate-200 dark:border-emerald-950 bg-white dark:bg-[#111c17] p-6 shadow-xs">
            <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">2. Dane pobrane z ZUS</h3>
            <dl className="mt-3 space-y-2 text-xs">
              <div className="flex justify-between border-b border-slate-100 dark:border-slate-800 py-1.5">
                <dt className="text-slate-500 dark:text-slate-400">Ubezpieczony</dt>
                <dd className="font-semibold text-slate-900 dark:text-slate-100">
                  {user.full_name} ({user.pesel_masked})
                </dd>
              </div>
              <div className="flex justify-between border-b border-slate-100 dark:border-slate-800 py-1.5">
                <dt className="text-slate-500 dark:text-slate-400">Tytuł ubezpieczenia</dt>
                <dd className="font-semibold uppercase text-slate-900 dark:text-slate-100">{user.insurance_title}</dd>
              </div>
              <div className="flex justify-between border-b border-slate-100 dark:border-slate-800 py-1.5">
                <dt className="text-slate-500 dark:text-slate-400">Ubezpieczenie chorobowe</dt>
                <dd
                  className={`font-bold ${
                    user.has_sickness_insurance ? "text-emerald-700" : "text-red-700"
                  }`}
                >
                  {user.has_sickness_insurance
                    ? `Aktywne (${user.insurance_days} dni)`
                    : "Brak ubezpieczenia chorobowego"}
                </dd>
              </div>
              <div className="flex justify-between border-b border-slate-100 dark:border-slate-800 py-1.5">
                <dt className="text-slate-500 dark:text-slate-400">Płatnik składek</dt>
                <dd className="font-semibold text-slate-900 dark:text-slate-100">
                  {user.employer_name || "Brak"} ({user.employer_insured_count} ubezp.)
                </dd>
              </div>
              <div className="flex justify-between py-1.5">
                <dt className="text-slate-500 dark:text-slate-400">Deklarowane brutto</dt>
                <dd className="font-semibold text-slate-900 dark:text-slate-100">
                  {user.declared_gross_salary.toFixed(2)} zł
                </dd>
              </div>
            </dl>
          </section>

          {/* Stan zadłużenia */}
          <section className="rounded-xl border border-slate-200 dark:border-emerald-950 bg-white dark:bg-[#111c17] p-6 shadow-xs">
            <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
              3. Stan zadłużenia z tytułu składek (symulacja)
            </h3>
            {debt ? (
              <div className="mt-3 space-y-3 text-xs">
                <div
                  className={`rounded-lg p-4 ${
                    debt.has_debt
                      ? "border border-red-200 bg-red-50 dark:border-red-800/60 dark:bg-red-950/40 text-red-900 dark:text-red-200"
                      : "border border-emerald-200 bg-emerald-50 dark:border-emerald-800/60 dark:bg-emerald-950/40 text-emerald-900 dark:text-emerald-200"
                  }`}
                >
                  <p className="text-sm font-bold">
                    {debt.has_debt
                      ? `Wykryto zadłużenie: ${debt.debt_amount_pln.toFixed(2)} zł`
                      : "Brak zadłużenia (0,00 zł)"}
                  </p>
                  <p className="mt-1">{debt.impact_warning}</p>
                </div>
                <p className="text-slate-500 dark:text-slate-400">
                  Nr symulowanego zaświadczenia: <strong>{debt.certificate_number}</strong> (stan na{" "}
                  {debt.checked_at})
                </p>
              </div>
            ) : (
              <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">Ładowanie stanu zadłużenia...</p>
            )}
          </section>

          {/* Podgląd e-ZLA */}
          <section className="rounded-xl border border-slate-200 dark:border-emerald-950 bg-white dark:bg-[#111c17] p-6 shadow-xs">
            <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
              4. Podgląd zaświadczeń lekarskich e-ZLA (symulacja)
            </h3>
            {ezla.length > 0 ? (
              <div className="mt-3 space-y-2">
                {ezla.map((item) => (
                  <div
                    key={item.certificate_number}
                    className="rounded-lg border border-slate-200 dark:border-emerald-950 p-3 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-slate-900 dark:text-slate-100">
                        {item.certificate_number}
                      </span>
                      <span className="rounded bg-[#e6f4ec] dark:bg-[#007834]/20 px-2 py-0.5 font-bold text-[#005a27] dark:text-emerald-300">
                        Kod: {item.letter_code || "brak"}
                      </span>
                    </div>
                    <p className="mt-1 text-slate-700 dark:text-slate-300">
                      Okres: <strong>{item.date_from}</strong> – <strong>{item.date_to}</strong> (
                      {item.days} dni)
                    </p>
                    <p className="mt-0.5 text-slate-500 dark:text-slate-400">
                      {item.doctor_specialty} • {item.status}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
                Brak wystawionych zaświadczeń e-ZLA dla wybranego profilu.
              </p>
            )}
          </section>

          {/* Połączenie z PUE/eZUS */}
          <section className="rounded-xl border border-slate-200 dark:border-emerald-950 bg-white dark:bg-[#111c17] p-6 shadow-xs">
            <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
              5. Połączenie z PUE/eZUS — zadaj pytanie (symulacja)
            </h3>
            <form onSubmit={handleInquiry} className="mt-3 space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">Temat</label>
                <input
                  type="text"
                  required
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-xs"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">Treść pytania</label>
                <textarea
                  rows={3}
                  required
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-xs"
                />
              </div>
              <button
                type="submit"
                className="rounded-lg bg-[#007834] px-4 py-2 text-xs font-semibold text-white hover:bg-[#005a27]"
              >
                Wyślij zapytanie przez PUE/eZUS (symulacja)
              </button>
              {ticketInfo && (
                <p className="rounded bg-emerald-50 p-2.5 text-xs text-emerald-900 dark:text-emerald-200">{ticketInfo}</p>
              )}
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
