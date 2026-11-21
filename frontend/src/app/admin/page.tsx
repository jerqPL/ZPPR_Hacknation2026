"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { api } from "@/lib/api";
import type { LegalParameters } from "@/lib/types";

export default function AdminPanelPage() {
  const [params, setParams] = useState<LegalParameters | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    api.getParameters().then(setParams).catch((e) => setMessage(String(e)));
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!params) return;
    setSaving(true);
    setMessage(null);
    try {
      const updated = await api.updateParameters(params);
      setParams(updated);
      setMessage("Zapisano parametry prawne. Wszystkie kalkulatory używają już nowych wartości.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Błąd zapisu parametrów");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const reset = await api.resetParameters();
      setParams(reset);
      setMessage("Przywrócono domyślne parametry prawne 2026.");
    } finally {
      setSaving(false);
    }
  };

  const updateNum = (field: keyof LegalParameters, value: string) => {
    if (!params) return;
    setParams({ ...params, [field]: Number(value) });
  };

  return (
    <div>
      <PageHeader
        badge="Panel Administracyjny"
        title="Konfiguracja parametrów prawnych (zmiany legislacyjne)"
        description="Edytuj stawki procentowe zasiłków, maksymalne wymiary urlopów, płacę minimalną lub progi płatnika bez konieczności modyfikacji kodu źródłowego."
      />

      {!params ? (
        <p className="text-sm text-slate-500">Ładowanie parametrów z API...</p>
      ) : (
        <form
          onSubmit={handleSave}
          className="space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-xs"
        >
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700">Rok obowiązywania</label>
              <input
                type="number"
                value={params.year}
                onChange={(e) => updateNum("year", e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700">
                Płaca minimalna brutto (zł)
              </label>
              <input
                type="number"
                step="0.01"
                value={params.minimum_wage_gross}
                onChange={(e) => updateNum("minimum_wage_gross", e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700">
                Składki społeczne pracownika (ułamek, np. 0.1371)
              </label>
              <input
                type="number"
                step="0.0001"
                value={params.employee_social_security_rate}
                onChange={(e) => updateNum("employee_social_security_rate", e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700">
                Stawka łączona (wniosek w 21 dni, np. 0.815)
              </label>
              <input
                type="number"
                step="0.005"
                value={params.combined_21_days_rate}
                onChange={(e) => updateNum("combined_21_days_rate", e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700">
                Stawka rodzicielskiego (np. 0.7)
              </label>
              <input
                type="number"
                step="0.01"
                value={params.parental_rate_standard}
                onChange={(e) => updateNum("parental_rate_standard", e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700">
                Maks. okres zasiłkowy w ciąży (dni)
              </label>
              <input
                type="number"
                value={params.sickness_benefit_pregnancy_max_days}
                onChange={(e) => updateNum("sickness_benefit_pregnancy_max_days", e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700">
                Urlop rodzicielski — 1 dziecko (tyg.)
              </label>
              <input
                type="number"
                value={params.parental_weeks_single}
                onChange={(e) => updateNum("parental_weeks_single", e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700">
                Część nieprzenoszalna rodzica (tyg.)
              </label>
              <input
                type="number"
                value={params.parental_non_transferable_weeks}
                onChange={(e) => updateNum("parental_non_transferable_weeks", e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700">
                Próg płatnika składek (liczba ubezpieczonych)
              </label>
              <input
                type="number"
                value={params.payer_employee_threshold}
                onChange={(e) => updateNum("payer_employee_threshold", e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
          </div>

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
              className="rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              Przywróć domyślne (2026)
            </button>
          </div>

          {message && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs font-medium text-emerald-900">
              {message}
            </div>
          )}
        </form>
      )}
    </div>
  );
}
