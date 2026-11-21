"use client";

import { useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { useUser } from "@/components/UserContext";
import { api } from "@/lib/api";
import type {
  BenefitScenario,
  InsuranceTitle,
  IntegratedCalculatorResponse,
  PaymentVariant,
} from "@/lib/types";

export default function IntegratedCalculatorPage() {
  const { user } = useUser();

  const [scenario, setScenario] = useState<BenefitScenario>("birth");
  const [insuranceTitle, setInsuranceTitle] = useState<InsuranceTitle>(
    user?.insurance_title || "uop"
  );
  const [insuredOnDate, setInsuredOnDate] = useState(user ? user.has_sickness_insurance : true);
  const [childrenCount, setChildrenCount] = useState(1);
  const [childAgeYears, setChildAgeYears] = useState(3);
  const [fosterDeferred, setFosterDeferred] = useState(false);
  const [hasZaZyciem, setHasZaZyciem] = useState(false);

  const [premature, setPremature] = useState(false);
  const [gestationWeek, setGestationWeek] = useState(32);
  const [birthWeight, setBirthWeight] = useState(1400);
  const [hospWeeks, setHospWeeks] = useState(4);

  const [grossSalary, setGrossSalary] = useState(user?.declared_gross_salary ?? 7500);
  const [secondParentGross, setSecondParentGross] = useState(8000);
  const [paymentVariant, setPaymentVariant] = useState<PaymentVariant>("81_5");
  const [motherMaternityWeeks, setMotherMaternityWeeks] = useState(20);
  const [fatherParentalWeeks, setFatherParentalWeeks] = useState(9);
  const [fatherPaternity, setFatherPaternity] = useState(true);

  const [combineWork, setCombineWork] = useState(false);
  const [workFte, setWorkFte] = useState(0.5);
  const [workWeeks, setWorkWeeks] = useState(10);
  const [employerCount, setEmployerCount] = useState(user?.employer_insured_count ?? 30);

  const [result, setResult] = useState<IntegratedCalculatorResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await api.calculateIntegrated({
        scenario,
        insurance_title: insuranceTitle,
        has_sickness_insurance_on_birth_date: insuredOnDate,
        children_count: Number(childrenCount),
        child_age_years: scenario === "birth" ? null : Number(childAgeYears),
        foster_deferred_school: fosterDeferred,
        has_za_zyciem_certificate: hasZaZyciem,
        premature_or_hospitalized: premature,
        gestation_week: premature ? Number(gestationWeek) : null,
        birth_weight_grams: premature ? Number(birthWeight) : null,
        hospitalization_weeks: premature ? Number(hospWeeks) : 0,
        gross_monthly_salary: Number(grossSalary),
        second_parent_gross_salary: Number(secondParentGross),
        payment_variant: paymentVariant,
        mother_maternity_weeks: scenario === "birth" ? Number(motherMaternityWeeks) : null,
        father_takes_parental_weeks: Number(fatherParentalWeeks),
        father_takes_paternity_leave: fatherPaternity,
        combine_parental_with_work: combineWork,
        work_fte_fraction: combineWork ? Number(workFte) : 0,
        combined_work_weeks: combineWork ? Number(workWeeks) : 0,
        employer_insured_count: Number(employerCount),
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Błąd wyliczeń API");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <PageHeader
        badge="Moduł 2 • Zintegrowany Kalkulator"
        title="Zintegrowany Kalkulator Zasiłku Macierzyńskiego i Rodzicielskiego"
        description="Jedno narzędzie łączące wszystkie warianty: poród, podział opieki między oboje rodziców, łączenie urlopu rodzicielskiego z pracą, adopcję i rodzinę zastępczą, wcześniaki oraz zaświadczenie „Za życiem”."
      />

      <div className="grid gap-8 lg:grid-cols-12">
        <form
          onSubmit={handleSubmit}
          className="space-y-5 rounded-xl border border-[#CCC5B9] bg-[#FFFCF2] p-6 shadow-xs lg:col-span-5"
        >
          {/* Scenariusz */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wide text-[#403D39]">
              1. Scenariusz rodzicielstwa
            </label>
            <div className="mt-2 grid grid-cols-3 gap-2">
              {(
                [
                  { id: "birth", label: "Poród" },
                  { id: "adoption", label: "Adopcja" },
                  { id: "foster", label: "Rodz. zastępcza" },
                ] as const
              ).map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setScenario(opt.id)}
                  className={`rounded-lg border px-2 py-2 text-xs font-semibold transition ${
                    scenario === opt.id
                      ? "border-[#000000] bg-[#F5F1E6] text-[#000000]"
                      : "border-[#CCC5B9] text-[#403D39] hover:bg-[#F5F1E6]"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Ubezpieczenie i dzieci */}
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold text-[#262522]">
                Tytuł ubezpieczenia
              </label>
              <select
                value={insuranceTitle}
                onChange={(e) => setInsuranceTitle(e.target.value as InsuranceTitle)}
                className="mt-1 w-full rounded-lg border border-[#CCC5B9] px-3 py-2 text-sm"
              >
                <option value="uop">Umowa o pracę</option>
                <option value="zlecenie">Umowa zlecenie</option>
                <option value="jdg">Działalność (JDG)</option>
                <option value="none">Brak ubezpieczenia</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-[#262522]">
                Liczba dzieci (1 poród/przyjęcie)
              </label>
              <input
                type="number"
                min={1}
                max={6}
                value={childrenCount}
                onChange={(e) => setChildrenCount(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-[#CCC5B9] px-3 py-2 text-sm"
              />
            </div>
          </div>

          <label className="flex items-center gap-2 text-xs text-[#262522]">
            <input
              type="checkbox"
              checked={insuredOnDate}
              onChange={(e) => setInsuredOnDate(e.target.checked)}
              className="h-4 w-4 accent-[#000000]"
            />
            Podleganie ubezpieczeniu chorobowemu na dzień porodu / przyjęcia dziecka
          </label>

          {scenario !== "birth" && (
            <div className="grid gap-3 rounded-lg bg-[#F5F1E6] p-3 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-semibold text-[#262522]">
                  Wiek dziecka (lata)
                </label>
                <input
                  type="number"
                  min={0}
                  max={18}
                  step={0.5}
                  value={childAgeYears}
                  onChange={(e) => setChildAgeYears(Number(e.target.value))}
                  className="mt-1 w-full rounded-lg border border-[#CCC5B9] bg-[#FFFCF2] px-3 py-1.5 text-sm"
                />
              </div>
              {scenario === "foster" && (
                <label className="flex items-center gap-2 self-end text-xs text-[#262522]">
                  <input
                    type="checkbox"
                    checked={fosterDeferred}
                    onChange={(e) => setFosterDeferred(e.target.checked)}
                    className="h-4 w-4 accent-[#000000]"
                  />
                  Odroczenie obowiązku szkolnego (do 10 lat)
                </label>
              )}
            </div>
          )}

          {/* Podstawa i wariant */}
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold text-[#262522]">
                Brutto rodzica 1 (zł)
              </label>
              <input
                type="number"
                min={0}
                step={100}
                value={grossSalary}
                onChange={(e) => setGrossSalary(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-[#CCC5B9] px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[#262522]">
                Brutto rodzica 2 (zł)
              </label>
              <input
                type="number"
                min={0}
                step={100}
                value={secondParentGross}
                onChange={(e) => setSecondParentGross(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-[#CCC5B9] px-3 py-2 text-sm"
              />
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold text-[#262522]">Wariant wypłaty</label>
              <select
                value={paymentVariant}
                onChange={(e) => setPaymentVariant(e.target.value as PaymentVariant)}
                className="mt-1 w-full rounded-lg border border-[#CCC5B9] px-3 py-2 text-sm"
              >
                <option value="81_5">81,5% (wniosek w 21 dni)</option>
                <option value="100_70">100% macierzyński + 70% rodzicielski</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-[#262522]">
                Ubezpieczeni u płatnika
              </label>
              <input
                type="number"
                min={0}
                value={employerCount}
                onChange={(e) => setEmployerCount(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-[#CCC5B9] px-3 py-2 text-sm"
              />
            </div>
          </div>

          {/* Podział między rodziców */}
          <div className="space-y-2 rounded-lg border border-[#CCC5B9] p-3">
            <p className="text-xs font-bold text-[#262522]">2. Podział opieki między rodziców</p>
            <div className="grid gap-3 sm:grid-cols-2">
              {scenario === "birth" && (
                <div>
                  <label className="block text-[11px] text-[#403D39]">
                    Macierzyński matki (min. 14 tyg.)
                  </label>
                  <input
                    type="number"
                    min={14}
                    max={37}
                    value={motherMaternityWeeks}
                    onChange={(e) => setMotherMaternityWeeks(Number(e.target.value))}
                    className="mt-1 w-full rounded border border-[#CCC5B9] px-2.5 py-1.5 text-sm"
                  />
                </div>
              )}
              <div>
                <label className="block text-[11px] text-[#403D39]">
                  Rodzicielski dla 2. rodzica (tyg., min. 9)
                </label>
                <input
                  type="number"
                  min={0}
                  max={67}
                  value={fatherParentalWeeks}
                  onChange={(e) => setFatherParentalWeeks(Number(e.target.value))}
                  className="mt-1 w-full rounded border border-[#CCC5B9] px-2.5 py-1.5 text-sm"
                />
              </div>
            </div>
            <label className="flex items-center gap-2 text-xs text-[#262522]">
              <input
                type="checkbox"
                checked={fatherPaternity}
                onChange={(e) => setFatherPaternity(e.target.checked)}
                className="h-4 w-4 accent-[#000000]"
              />
              Uwzględnij urlop ojcowski (2 tygodnie, 100%)
            </label>
          </div>

          {/* Opcje zaawansowane */}
          <div className="space-y-2 rounded-lg border border-[#CCC5B9] p-3">
            <p className="text-xs font-bold text-[#262522]">3. Opcje dodatkowe</p>
            <label className="flex items-center gap-2 text-xs text-[#262522]">
              <input
                type="checkbox"
                checked={hasZaZyciem}
                onChange={(e) => setHasZaZyciem(e.target.checked)}
                className="h-4 w-4 accent-[#000000]"
              />
              Zaświadczenie „Za życiem” (wydłużony urlop rodzicielski 65/67 tyg.)
            </label>

            <label className="flex items-center gap-2 text-xs text-[#262522]">
              <input
                type="checkbox"
                checked={premature}
                onChange={(e) => setPremature(e.target.checked)}
                className="h-4 w-4 accent-[#000000]"
              />
              Wcześniak / hospitalizacja (uzupełniający urlop macierzyński)
            </label>
            {premature && (
              <div className="grid grid-cols-3 gap-2 pt-1">
                <div>
                  <label className="block text-[10px] text-[#403D39]/80">Tydzień ciąży</label>
                  <input
                    type="number"
                    min={20}
                    max={42}
                    value={gestationWeek}
                    onChange={(e) => setGestationWeek(Number(e.target.value))}
                    className="w-full rounded border border-[#CCC5B9] px-2 py-1 text-xs"
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-[#403D39]/80">Masa (g)</label>
                  <input
                    type="number"
                    min={300}
                    max={6000}
                    value={birthWeight}
                    onChange={(e) => setBirthWeight(Number(e.target.value))}
                    className="w-full rounded border border-[#CCC5B9] px-2 py-1 text-xs"
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-[#403D39]/80">Szpital (tyg.)</label>
                  <input
                    type="number"
                    min={0}
                    max={20}
                    value={hospWeeks}
                    onChange={(e) => setHospWeeks(Number(e.target.value))}
                    className="w-full rounded border border-[#CCC5B9] px-2 py-1 text-xs"
                  />
                </div>
              </div>
            )}

            <label className="flex items-center gap-2 text-xs text-[#262522]">
              <input
                type="checkbox"
                checked={combineWork}
                onChange={(e) => setCombineWork(e.target.checked)}
                className="h-4 w-4 accent-[#000000]"
              />
              Łączenie urlopu rodzicielskiego z pracą (maks. 1/2 etatu)
            </label>
            {combineWork && (
              <div className="grid grid-cols-2 gap-2 pt-1">
                <div>
                  <label className="block text-[10px] text-[#403D39]/80">Wymiar etatu (0.1–0.5)</label>
                  <input
                    type="number"
                    min={0.1}
                    max={0.5}
                    step={0.1}
                    value={workFte}
                    onChange={(e) => setWorkFte(Number(e.target.value))}
                    className="w-full rounded border border-[#CCC5B9] px-2 py-1 text-xs"
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-[#403D39]/80">Liczba tyg. pracy</label>
                  <input
                    type="number"
                    min={1}
                    max={41}
                    value={workWeeks}
                    onChange={(e) => setWorkWeeks(Number(e.target.value))}
                    className="w-full rounded border border-[#CCC5B9] px-2 py-1 text-xs"
                  />
                </div>
              </div>
            )}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-[#000000] px-4 py-2.5 text-sm font-semibold text-[#FFFCF2] transition hover:bg-[#262522] disabled:opacity-50"
          >
            {loading ? "Obliczanie..." : "Oblicz wymiary i wysokość zasiłku"}
          </button>

          {error && <p className="text-xs text-red-600">{error}</p>}
        </form>

        {/* Wyniki */}
        <div className="space-y-5 lg:col-span-7">
          {result ? (
            <div className="rounded-xl border border-[#CCC5B9] bg-[#FFFCF2] p-6 shadow-xs">
              {!result.eligible ? (
                <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
                  <p className="font-bold">Brak uprawnień do zasiłku macierzyńskiego</p>
                  <p className="mt-1">{result.ineligibility_reason}</p>
                </div>
              ) : (
                <>
                  <div className="grid gap-4 sm:grid-cols-3">
                    <div className="rounded-lg bg-[#F5F1E6] p-4">
                      <p className="text-xs text-[#000000]">Łączny czas urlopów</p>
                      <p className="mt-1 text-2xl font-bold text-[#000000]">
                        {result.total_weeks} tyg.
                      </p>
                    </div>
                    <div className="rounded-lg bg-[#F5F1E6] p-4">
                      <p className="text-xs text-[#403D39]/80">Szacowana suma brutto</p>
                      <p className="mt-1 text-2xl font-bold text-[#000000]">
                        {result.total_estimated_gross_pln.toLocaleString("pl-PL")} zł
                      </p>
                    </div>
                    <div className="rounded-lg bg-[#F5F1E6] p-4">
                      <p className="text-xs text-[#403D39]/80">Podstawa rodzica 1</p>
                      <p className="mt-1 text-xl font-bold text-[#000000]">
                        {result.benefit_base_parent1.toFixed(2)} zł
                      </p>
                    </div>
                  </div>

                  <p className="mt-4 text-xs text-[#403D39]">
                    <strong>Płatnik świadczenia:</strong> {result.payer}
                  </p>

                  {/* Tabela harmonogramu */}
                  <div className="mt-5 overflow-x-auto">
                    <table className="w-full border-collapse text-left text-xs">
                      <thead>
                        <tr className="border-b border-[#CCC5B9] bg-[#F5F1E6] text-[#403D39]">
                          <th className="p-2.5">Rodzaj urlopu / zasiłku</th>
                          <th className="p-2.5">Rodzic</th>
                          <th className="p-2.5 text-right">Tyg.</th>
                          <th className="p-2.5 text-right">Stawka</th>
                          <th className="p-2.5 text-right">Miesięcznie</th>
                          <th className="p-2.5 text-right">Łącznie brutto</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.breakdown.map((row, idx) => (
                          <tr key={idx} className="border-b border-[#CCC5B9]/60">
                            <td className="p-2.5 font-medium text-[#000000]">
                              {row.label}
                              {row.notes && (
                                <p className="mt-0.5 text-[11px] font-normal text-[#403D39]/80">
                                  {row.notes}
                                </p>
                              )}
                            </td>
                            <td className="p-2.5 text-[#262522]">{row.parent}</td>
                            <td className="p-2.5 text-right font-semibold">{row.weeks}</td>
                            <td className="p-2.5 text-right">{row.rate_percent}%</td>
                            <td className="p-2.5 text-right">
                              {row.monthly_gross_pln.toFixed(2)} zł
                            </td>
                            <td className="p-2.5 text-right font-semibold text-[#000000]">
                              {row.total_gross_pln.toFixed(2)} zł
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {result.required_documents.length > 0 && (
                    <div className="mt-5 rounded-lg bg-[#F5F1E6] p-4">
                      <p className="text-xs font-bold text-[#000000]">Wymagane dokumenty</p>
                      <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-[#262522]">
                        {result.required_documents.map((doc, i) => (
                          <li key={i}>{doc}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              )}

              {result.warnings.length > 0 && (
                <div className="mt-4 rounded-lg border border-[#CCC5B9] bg-[#F5F1E6] p-4">
                  <p className="text-xs font-bold text-[#000000]">Uwagi i zasady prawne</p>
                  <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-[#000000]">
                    {result.warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-[#CCC5B9] bg-[#FFFCF2] p-10 text-center text-sm text-[#403D39]/80">
              Skonfiguruj parametry po lewej stronie i kliknij „Oblicz wymiary i wysokość zasiłku”,
              aby wygenerować symulację dla obojga rodziców.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
