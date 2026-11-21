"use client";

import { useEffect, useState } from "react";
import { Lock } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { api } from "@/lib/api";
import type { LegalParameters } from "@/lib/types";

export default function AdminPanelPage() {
  const [params, setParams] = useState<LegalParameters | null>(null);
  const [adminKey, setAdminKey] = useState("zppr-admin-2026");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getParameters().then(setParams).catch((e) => setError(String(e)));
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!params) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const updated = await api.updateParameters(params, adminKey);
      setParams(updated);
      setMessage("Zapisano wszystkie parametry prawne. Kalkulatory używają już nowych wartości.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Błąd zapisu parametrów (sprawdź klucz administratora)");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const reset = await api.resetParameters(adminKey);
      setParams(reset);
      setMessage("Przywrócono ustawowe wartości domyślne 2026.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Błąd resetu (sprawdź klucz administratora)");
    } finally {
      setSaving(false);
    }
  };

  const updateNum = (field: keyof LegalParameters, value: string) => {
    if (!params) return;
    setParams({ ...params, [field]: Number(value) });
  };

  const updateMaternityByChildren = (childKey: string, value: string) => {
    if (!params) return;
    setParams({
      ...params,
      maternity_weeks_by_children: {
        ...params.maternity_weeks_by_children,
        [childKey]: Number(value),
      },
    });
  };

  const fieldInput = (label: string, field: keyof LegalParameters, _step?: string) => (
    <div key={String(field)}>
      <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">{label}</label>
      <input
        type="number"
        step="any"
        value={Number(params?.[field] ?? 0)}
        onChange={(e) => updateNum(field, e.target.value)}
        className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
      />
    </div>
  );

  return (
    <div>
      <PageHeader
        badge="Panel Administracyjny"
        title="Konfiguracja parametrów prawnych (zmiany legislacyjne)"
        description="Pełna edycja stawek procentowych, wymiarów urlopów, progów finansowych i okresów wyczekiwania bez modyfikacji kodu. Zmiany zapisywane są w trwałym wolumenie danych."
      />

      {!params ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">Ładowanie parametrów z API...</p>
      ) : (
        <form
          onSubmit={handleSave}
          className="space-y-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-xs dark:border-emerald-950 dark:bg-[#111c17]"
        >
          {/* Autoryzacja administratora */}
          <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-emerald-950 dark:bg-[#16241d] sm:flex-row sm:items-end">
            <div className="flex-1">
              <label className="flex items-center gap-1.5 text-xs font-bold text-slate-800 dark:text-slate-200">
                <Lock className="h-3.5 w-3.5 text-[#007834] dark:text-emerald-400" />
                Klucz autoryzacji administratora (nagłówek X-Admin-Key)
              </label>
              <input
                type="password"
                required
                value={adminKey}
                onChange={(e) => setAdminKey(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-[#111c17]"
              />
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 sm:max-w-xs">
              Wymagany do zapisu (`PUT`) i resetu (`POST`) parametrów. Odczyt (`GET`) pozostaje publiczny dla kalkulatorów.
            </p>
          </div>

          {/* Sekcja 1: Podstawy i progi finansowe */}
          <section>
            <h2 className="mb-3 text-sm font-bold text-slate-900 dark:text-white">
              1. Podstawy wymiaru, progi finansowe i składki
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {fieldInput("Rok obowiązywania", "year")}
              {fieldInput("Płaca minimalna brutto (zł)", "minimum_wage_gross", "0.01")}
              {fieldInput("Stopa składek pracownika (np. 0.1371)", "employee_social_security_rate", "0.0001")}
              {fieldInput("Maks. podstawa dobrowolna 250% (zł brutto)", "voluntary_sickness_max_monthly_gross", "0.01")}
              {fieldInput("Pułap podstawy po ustaniu (art. 46, zł brutto)", "post_employment_sickness_cap_monthly_gross", "0.01")}
              {fieldInput("JDG min. podstawa standardowa (zł)", "jdg_standard_min_base_gross", "0.01")}
              {fieldInput("JDG min. podstawa preferencyjna (zł)", "jdg_preferential_min_base_gross", "0.01")}
              {fieldInput("Podwyższenie zasiłku macierzyńskiego (zł/mies.)", "parental_benefit_minimum_monthly", "1")}
              {fieldInput("Próg zadłużenia JDG (ułamek płacy min., 0.01 = 1%)", "debt_threshold_min_wage_fraction", "0.001")}
              {fieldInput("Próg płatnika składek (liczba ubezp.)", "payer_employee_threshold")}
              {fieldInput("Zasiłek pogrzebowy (zł)", "funeral_grant_pln", "100")}
              {fieldInput("Przedawnienie roszczeń (miesiące)", "claim_limitation_months")}
            </div>
          </section>

          {/* Sekcja 2: Stawki procentowe */}
          <section>
            <h2 className="mb-3 text-sm font-bold text-slate-900 dark:text-white">
              2. Stawki procentowe zasiłków (ułamek: 1.0 = 100%)
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {fieldInput("Chorobowy w ciąży (kod B)", "sickness_benefit_pregnancy_rate", "0.01")}
              {fieldInput("Chorobowy standardowy", "sickness_benefit_standard_rate", "0.01")}
              {fieldInput("Macierzyński (standard)", "maternity_rate_standard", "0.01")}
              {fieldInput("Rodzicielski (standard)", "parental_rate_standard", "0.01")}
              {fieldInput("Wariant łączony (21 dni)", "combined_21_days_rate", "0.005")}
              {fieldInput("Nieprzenoszalne 9 tyg.", "non_transferable_parental_rate", "0.01")}
              {fieldInput("Urlop ojcowski", "paternity_rate", "0.01")}
              {fieldInput("Uzupełniający macierzyński", "supplementary_maternity_rate", "0.01")}
              {fieldInput("Świadczenie rehabilitacyjne (ciąża)", "rehabilitation_benefit_pregnancy_rate", "0.01")}
            </div>
          </section>

          {/* Sekcja 3: Wymiary urlopu macierzyńskiego wg liczby dzieci */}
          <section>
            <h2 className="mb-3 text-sm font-bold text-slate-900 dark:text-white">
              3. Wymiar urlopu macierzyńskiego wg liczby dzieci (tygodnie)
            </h2>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
              {["1", "2", "3", "4", "5"].map((k) => (
                <div key={k}>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                    {k === "5" ? "5+ dzieci" : `${k} ${k === "1" ? "dziecko" : "dzieci"}`}
                  </label>
                  <input
                    type="number"
                    min={1}
                    value={params.maternity_weeks_by_children[k] ?? 20}
                    onChange={(e) => updateMaternityByChildren(k, e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
                  />
                </div>
              ))}
            </div>
          </section>

          {/* Sekcja 4: Pozostałe wymiary i terminy */}
          <section>
            <h2 className="mb-3 text-sm font-bold text-slate-900 dark:text-white">
              4. Wymiary urlopów, okresy wyczekiwania i limity wieku
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {fieldInput("Rodzicielski — 1 dziecko (tyg.)", "parental_weeks_single")}
              {fieldInput("Rodzicielski — 2+ dzieci (tyg.)", "parental_weeks_multiple")}
              {fieldInput("Za życiem — 1 dziecko (tyg.)", "parental_weeks_za_zyciem_single")}
              {fieldInput("Za życiem — 2+ dzieci (tyg.)", "parental_weeks_za_zyciem_multiple")}
              {fieldInput("Nieprzenoszalna część (tyg.)", "parental_non_transferable_weeks")}
              {fieldInput("Maks. liczba części rodzicielskiego", "parental_max_parts")}
              {fieldInput("Maks. etat przy łączeniu z pracą", "parental_work_max_fte", "0.05")}
              {fieldInput("Urlop ojcowski (tyg.)", "paternity_weeks")}
              {fieldInput("Termin na wniosek 81,5% (dni)", "combined_application_deadline_days")}
              {fieldInput("Min. macierzyński matki (tyg.)", "maternity_min_mother_weeks")}
              {fieldInput("Maks. macierzyński przed porodem (tyg.)", "maternity_pre_birth_max_weeks")}
              {fieldInput("Uzupełniający <28 tyg./≤1000g (tyg.)", "supplementary_maternity_max_weeks_extreme")}
              {fieldInput("Uzupełniający standard (tyg.)", "supplementary_maternity_max_weeks_standard")}
              {fieldInput("Martwe urodzenie (tyg.)", "stillbirth_maternity_weeks")}
              {fieldInput("Min. dni po zgonie dziecka", "child_death_min_days")}
              {fieldInput("Okres zasiłkowy w ciąży (dni)", "sickness_benefit_pregnancy_max_days")}
              {fieldInput("Wyczekiwanie obowiązkowe (dni)", "waiting_period_mandatory_days")}
              {fieldInput("Wyczekiwanie dobrowolne (dni)", "waiting_period_voluntary_days")}
              {fieldInput("Wynagr. chorobowe <50 lat (dni)", "sickness_pay_employer_days_under_50")}
              {fieldInput("Wynagr. chorobowe 50+ lat (dni)", "sickness_pay_employer_days_over_50")}
              {fieldInput("Świadczenie rehabilitacyjne (dni)", "rehabilitation_benefit_max_days")}
              {fieldInput("Limit wieku: rodz. zastępcza (lata)", "foster_max_child_age")}
              {fieldInput("Limit wieku: odroczenie szkoły (lata)", "foster_deferred_school_max_child_age")}
              {fieldInput("Limit wieku: adopcja (lata)", "adoption_max_child_age")}
              {fieldInput("Min. urlop przy granicy wieku (tyg.)", "adoption_foster_min_maternity_weeks")}
              {fieldInput("Rodzicielski przy granicy wieku (tyg.)", "adoption_foster_reduced_parental_weeks")}
              {fieldInput("Rodzicielski Za życiem (granica, tyg.)", "adoption_foster_reduced_parental_weeks_za_zyciem")}
            </div>
          </section>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-[#007834] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#005a27] disabled:opacity-50"
            >
              {saving ? "Zapisywanie..." : "Zapisz parametry"}
            </button>
            <button
              type="button"
              disabled={saving}
              onClick={handleReset}
              className="rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-[#111c17] dark:text-slate-300 dark:hover:bg-[#1e3328]"
            >
              Przywróć domyślne (2026)
            </button>
          </div>

          {message && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs font-medium text-emerald-900 dark:border-emerald-800/60 dark:bg-emerald-950/40 dark:text-emerald-200">
              {message}
            </div>
          )}
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs font-medium text-red-800 dark:border-red-800/60 dark:bg-red-950/40 dark:text-red-200">
              {error}
            </div>
          )}
        </form>
      )}
    </div>
  );
}
