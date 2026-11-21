"use client";

import { useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { useUser } from "@/components/UserContext";
import { api } from "@/lib/api";
import type { InsuranceTitle, PregnancyBenefitResponse } from "@/lib/types";

export default function PregnancyPage() {
  const { user } = useUser();

  const [insuranceTitle, setInsuranceTitle] = useState<InsuranceTitle>(
    user?.insurance_title || "uop"
  );
  const [hasVoluntary, setHasVoluntary] = useState(user ? user.has_sickness_insurance : true);
  const [insuranceDays, setInsuranceDays] = useState(user?.insurance_days ?? 180);
  const [grossSalary, setGrossSalary] = useState(user?.declared_gross_salary ?? 6500);
  const [hasCodeB, setHasCodeB] = useState(true);
  const [employerCount, setEmployerCount] = useState(user?.employer_insured_count ?? 25);
  const [specialTermination, setSpecialTermination] = useState(false);
  const [terminationReason, setTerminationReason] = useState("bankruptcy_liquidation");

  const [result, setResult] = useState<PregnancyBenefitResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleCalculate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await api.calculatePregnancy({
        insurance_title: insuranceTitle,
        has_voluntary_sickness_insurance: hasVoluntary,
        insurance_days: Number(insuranceDays),
        gross_monthly_salary: Number(grossSalary),
        has_code_b: hasCodeB,
        employer_insured_count: Number(employerCount),
        employment_terminated_special: specialTermination,
        termination_reason: specialTermination ? terminationReason : null,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Błąd połączenia z API");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <PageHeader
        badge="Moduł 1 • Okres ciąży"
        title="Świadczenia w czasie ciąży"
        description="Sprawdź uprawnienia do zasiłku chorobowego (kod literowy B = 100% do 270 dni), świadczenia rehabilitacyjnego oraz zasiłku w wysokości zasiłku macierzyńskiego po ustaniu zatrudnienia."
      />

      <div className="grid gap-8 lg:grid-cols-12">
        <form
          onSubmit={handleCalculate}
          className="space-y-4 rounded-xl border border-slate-200 dark:border-emerald-950 bg-white dark:bg-[#111c17] p-6 shadow-xs lg:col-span-5"
        >
          <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">Twoja sytuacja ubezpieczeniowa</h2>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
              Tytuł ubezpieczenia
            </label>
            <select
              value={insuranceTitle}
              onChange={(e) => setInsuranceTitle(e.target.value as InsuranceTitle)}
              className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm"
            >
              <option value="uop">Umowa o pracę (obowiązkowe chorobowe)</option>
              <option value="zlecenie">Umowa zlecenie (dobrowolne chorobowe)</option>
              <option value="jdg">Działalność gospodarcza — JDG (dobrowolne chorobowe)</option>
              <option value="none">Brak ubezpieczenia chorobowego</option>
            </select>
          </div>

          {(insuranceTitle === "zlecenie" || insuranceTitle === "jdg") && (
            <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                checked={hasVoluntary}
                onChange={(e) => setHasVoluntary(e.target.checked)}
                className="h-4 w-4 accent-[#007834]"
              />
              Podlegam dobrowolnemu ubezpieczeniu chorobowemu
            </label>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                Okres nieprzerwanego ubezpieczenia (dni)
              </label>
              <input
                type="number"
                min={0}
                value={insuranceDays}
                onChange={(e) => setInsuranceDays(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                Wynagrodzenie / podstawa brutto (zł)
              </label>
              <input
                type="number"
                min={0}
                step={100}
                value={grossSalary}
                onChange={(e) => setGrossSalary(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
              Liczba ubezpieczonych u płatnika (stan na 30.11)
            </label>
            <input
              type="number"
              min={0}
              value={employerCount}
              onChange={(e) => setEmployerCount(Number(e.target.value))}
              className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm"
            />
          </div>

          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
            <input
              type="checkbox"
              checked={hasCodeB}
              onChange={(e) => setHasCodeB(e.target.checked)}
              className="h-4 w-4 accent-[#007834]"
            />
            Zaświadczenie lekarskie e-ZLA zawiera kod literowy „B” (ciąża)
          </label>

          <div className="rounded-lg border border-slate-200 dark:border-emerald-950 bg-slate-50 dark:bg-[#16241d] p-3">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-800 dark:text-slate-200">
              <input
                type="checkbox"
                checked={specialTermination}
                onChange={(e) => setSpecialTermination(e.target.checked)}
                className="h-4 w-4 accent-[#007834]"
              />
              Szczególna sytuacja: utrata zatrudnienia w ciąży
            </label>
            {specialTermination && (
              <select
                value={terminationReason}
                onChange={(e) => setTerminationReason(e.target.value)}
                className="mt-2 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-[#111c17] px-3 py-2 text-xs"
              >
                <option value="bankruptcy_liquidation">Upadłość lub likwidacja pracodawcy</option>
                <option value="employer_death">Śmierć pracodawcy</option>
                <option value="unlawful_termination_court_ruling">
                  Rozwiązanie umowy z naruszeniem prawa (prawomocny wyrok sądu)
                </option>
              </select>
            )}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-[#007834] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#005a27] disabled:opacity-50"
          >
            {loading ? "Sprawdzanie..." : "Sprawdź uprawnienia i oblicz zasiłek"}
          </button>

          {error && <p className="text-xs text-red-600">{error}</p>}
        </form>

        <div className="space-y-4 lg:col-span-7">
          {result ? (
            <div className="rounded-xl border border-slate-200 dark:border-emerald-950 bg-white dark:bg-[#111c17] p-6 shadow-xs">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">Wynik analizy</h2>
                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${
                    result.eligible_sickness_benefit || result.eligible_maternity_equivalent
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-red-100 text-red-800 dark:text-red-200"
                  }`}
                >
                  {result.eligible_maternity_equivalent
                    ? "Zasiłek w wys. macierzyńskiego"
                    : result.eligible_sickness_benefit
                    ? "Uprawnienie potwierdzone"
                    : "Brak uprawnień"}
                </span>
              </div>

              <p className="mt-3 text-sm text-slate-700 dark:text-slate-300">{result.summary}</p>

              <div className="mt-5 grid gap-4 sm:grid-cols-3">
                <div className="rounded-lg bg-slate-50 dark:bg-[#16241d] p-4">
                  <p className="text-xs text-slate-500 dark:text-slate-400">Podstawa wymiaru (mies.)</p>
                  <p className="mt-1 text-lg font-bold text-slate-900 dark:text-slate-100">
                    {result.benefit_base_monthly.toFixed(2)} zł
                  </p>
                </div>
                <div className="rounded-lg bg-[#e6f4ec] dark:bg-[#007834]/20 p-4">
                  <p className="text-xs text-[#005a27] dark:text-emerald-300">
                    Zasiłek miesięczny ({result.benefit_rate_percent}%)
                  </p>
                  <p className="mt-1 text-lg font-bold text-[#005a27] dark:text-emerald-300">
                    {result.monthly_benefit_gross.toFixed(2)} zł
                  </p>
                </div>
                <div className="rounded-lg bg-slate-50 dark:bg-[#16241d] p-4">
                  <p className="text-xs text-slate-500 dark:text-slate-400">Stawka dzienna (1/30)</p>
                  <p className="mt-1 text-lg font-bold text-slate-900 dark:text-slate-100">
                    {result.daily_benefit_gross.toFixed(2)} zł
                  </p>
                </div>
              </div>

              <dl className="mt-5 grid gap-2 text-xs text-slate-700 dark:text-slate-300 sm:grid-cols-2">
                <div className="rounded border border-slate-100 dark:border-slate-800 p-2.5">
                  <dt className="text-slate-500 dark:text-slate-400">Kto wypłaca zasiłek</dt>
                  <dd className="font-semibold text-slate-900 dark:text-slate-100">{result.payer}</dd>
                </div>
                <div className="rounded border border-slate-100 dark:border-slate-800 p-2.5">
                  <dt className="text-slate-500 dark:text-slate-400">Okres zasiłkowy / wynagrodzenie chorobowe</dt>
                  <dd className="font-semibold text-slate-900 dark:text-slate-100">
                    Maks. {result.max_benefit_days} dni (pierwsze {result.employer_pay_days} dni
                    pracodawca)
                  </dd>
                </div>
              </dl>

              {result.warnings.length > 0 && (
                <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-800/60 dark:bg-amber-950/40 p-4">
                  <p className="text-xs font-bold text-amber-900 dark:text-amber-200">Ważne uwagi</p>
                  <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-amber-900 dark:text-amber-200">
                    {result.warnings.map((w, idx) => (
                      <li key={idx}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-[#111c17] p-8 text-center text-sm text-slate-500 dark:text-slate-400">
              Uzupełnij formularz po lewej i kliknij „Sprawdź uprawnienia”, aby zobaczyć wyliczenie
              zasiłku chorobowego w ciąży.
            </div>
          )}

          <div className="rounded-xl border border-slate-200 dark:border-emerald-950 bg-white dark:bg-[#111c17] p-5 text-xs text-slate-600 dark:text-slate-400">
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">Świadczenie rehabilitacyjne</h3>
            <p className="mt-1 leading-relaxed">
              Jeśli po wyczerpaniu 270 dni okresu zasiłkowego kobieta nadal jest niezdolna do pracy,
              a dalsze leczenie rokuje odzyskanie zdolności, może ubiegać się o świadczenie
              rehabilitacyjne (w okresie ciąży wynosi 100% podstawy wymiaru).
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
