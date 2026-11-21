"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { InfoTooltip } from "@/components/InfoTooltip";
import { useUser } from "@/components/UserContext";
import { api } from "@/lib/api";
import type {
  BenefitScenario,
  FosterFamilyType,
  IndividualBaseCalculationResponse,
  InsuranceTitle,
  IntegratedCalculatorResponse,
  PaymentVariant,
  SampleCase,
} from "@/lib/types";

export default function IntegratedCalculatorPage() {
  const { user } = useUser();

  // Lista przykładowych spraw z zestawów ZUS (pkt f)
  const [sampleCases, setSampleCases] = useState<SampleCase[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>("");
  const [activeSampleCase, setActiveSampleCase] = useState<SampleCase | null>(null);

  // Scenariusz i ubezpieczenie (pkt b, e, j)
  const [scenario, setScenario] = useState<BenefitScenario>("birth");
  const [insuranceTitle, setInsuranceTitle] = useState<InsuranceTitle>(
    user?.insurance_title || "uop"
  );
  const [insuredOnDate, setInsuredOnDate] = useState(user ? user.has_sickness_insurance : true);
  const [childrenCount, setChildrenCount] = useState(1);
  const [childAgeYears, setChildAgeYears] = useState(3);
  const [fosterFamilyType, setFosterFamilyType] = useState<FosterFamilyType>("non_professional");
  const [fosterDeferred, setFosterDeferred] = useState(false);
  const [adoptionShort9Weeks, setAdoptionShort9Weeks] = useState(false);
  const [prevFosterMatWeeks, setPrevFosterMatWeeks] = useState(0);
  const [prevFosterParWeeks, setPrevFosterParWeeks] = useState(0);
  const [hasZaZyciem, setHasZaZyciem] = useState(false);

  const [premature, setPremature] = useState(false);
  const [gestationWeek, setGestationWeek] = useState(32);
  const [birthWeight, setBirthWeight] = useState(1400);
  const [hospWeeks, setHospWeeks] = useState(4);

  // Podstawa wymiaru zasiłku — standardowa lub indywidualna (pkt f)
  const [baseMode, setBaseMode] = useState<"standard" | "custom" | "creator">("standard");
  const [grossSalary, setGrossSalary] = useState(user?.declared_gross_salary ?? 7500);
  const [customBase1, setCustomBase1] = useState<string>("");
  const [secondParentGross, setSecondParentGross] = useState(8000);
  const [customBase2, setCustomBase2] = useState<string>("");

  // Kreator indywidualnej podstawy wymiaru (pkt f — Art. 36–50 ustawy zasiłkowej)
  const [creatorSubMode, setCreatorSubMode] = useState<
    "uop_12m" | "jdg_art48a" | "previous_benefit"
  >("uop_12m");
  const [creatorSalariesText, setCreatorSalariesText] = useState(
    "7500, 7500, 7500, 7500, 7500, 7500, 7800, 7800, 7800, 8000, 8000, 8000"
  );
  const [creatorQuarterlyBonus, setCreatorQuarterlyBonus] = useState(0);
  const [creatorAnnualBonus, setCreatorAnnualBonus] = useState(6000);
  const [creatorExcludedMonths, setCreatorExcludedMonths] = useState(0);
  const [creatorFte, setCreatorFte] = useState(1.0);
  const [creatorPrevBase, setCreatorPrevBase] = useState(5608.85);
  const [creatorJdgMonths, setCreatorJdgMonths] = useState(3);
  const [creatorJdgDeclared, setCreatorJdgDeclared] = useState(23550);
  const [creatorJdgMin, setCreatorJdgMin] = useState(5652);
  const [baseCalcResult, setBaseCalcResult] = useState<IndividualBaseCalculationResponse | null>(
    null
  );

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

  useEffect(() => {
    api.getSampleCases().then(setSampleCases).catch(() => setSampleCases([]));
  }, []);

  const handleLoadSampleCase = async (caseId: string) => {
    setSelectedCaseId(caseId);
    const found = sampleCases.find((c) => c.case_id === caseId);
    if (!found) {
      setActiveSampleCase(null);
      return;
    }
    setActiveSampleCase(found);
    setScenario(found.scenario || "birth");
    setInsuranceTitle(found.insurance_title);
    setInsuredOnDate(found.insured_on_event_date);
    setChildrenCount(found.children_count);
    if (found.child_age_years !== undefined && found.child_age_years !== null) {
      setChildAgeYears(found.child_age_years);
    }
    setFosterFamilyType(found.foster_family_type || "non_professional");
    setFosterDeferred(Boolean(found.foster_deferred_school));
    setHasZaZyciem(found.has_za_zyciem);
    setGrossSalary(found.gross_monthly_salary);
    if (found.custom_benefit_base) {
      setBaseMode("custom");
      setCustomBase1(String(found.custom_benefit_base));
    } else {
      setBaseMode("standard");
      setCustomBase1("");
    }
    if (found.second_parent_gross_salary) {
      setSecondParentGross(found.second_parent_gross_salary);
    }
    if (found.second_parent_custom_base) {
      setCustomBase2(String(found.second_parent_custom_base));
    } else {
      setCustomBase2("");
    }
    setPaymentVariant(found.payment_variant);
    setEmployerCount(found.employer_insured_count);
    if (found.mother_maternity_weeks !== undefined && found.mother_maternity_weeks !== null) {
      setMotherMaternityWeeks(found.mother_maternity_weeks);
    } else {
      setMotherMaternityWeeks(20);
    }
    setFatherParentalWeeks(found.father_takes_parental_weeks ?? 9);
    setFatherPaternity(Boolean(found.father_takes_paternity_leave));

    setLoading(true);
    setError(null);
    try {
      const res = await api.calculateIntegrated({
        scenario: found.scenario || "birth",
        insurance_title: found.insurance_title,
        has_sickness_insurance_on_birth_date: found.insured_on_event_date,
        children_count: found.children_count,
        child_age_years:
          (found.scenario || "birth") === "birth" ? null : (found.child_age_years ?? 3),
        foster_family_type: found.foster_family_type || "non_professional",
        foster_deferred_school: Boolean(found.foster_deferred_school),
        has_za_zyciem_certificate: found.has_za_zyciem,
        gross_monthly_salary: found.gross_monthly_salary,
        custom_benefit_base: found.custom_benefit_base ?? null,
        second_parent_gross_salary: found.second_parent_gross_salary ?? 8000,
        second_parent_custom_base: found.second_parent_custom_base ?? null,
        payment_variant: found.payment_variant,
        mother_maternity_weeks: found.mother_maternity_weeks ?? 20,
        father_takes_parental_weeks: found.father_takes_parental_weeks ?? 9,
        father_takes_paternity_leave: Boolean(found.father_takes_paternity_leave),
        employer_insured_count: found.employer_insured_count,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Błąd wyliczeń API");
    } finally {
      setLoading(false);
    }
  };

  const handleComputeIndividualBase = async () => {
    setError(null);
    try {
      const parsedSalaries = creatorSalariesText
        .split(/[,\s;]+/)
        .map((s) => Number(s.trim()))
        .filter((n) => !Number.isNaN(n) && n >= 0);

      const res = await api.calculateIndividualBase({
        insurance_title: insuranceTitle,
        mode: creatorSubMode,
        monthly_gross_salaries: parsedSalaries.length > 0 ? parsedSalaries : [grossSalary],
        quarterly_bonuses_total: Number(creatorQuarterlyBonus),
        annual_bonus_total: Number(creatorAnnualBonus),
        uncompleted_months_excluded: Number(creatorExcludedMonths),
        fte_fraction: Number(creatorFte),
        previous_benefit_base: Number(creatorPrevBase),
        jdg_insured_months: Number(creatorJdgMonths),
        jdg_declared_monthly_gross: Number(creatorJdgDeclared),
        jdg_min_monthly_gross: Number(creatorJdgMin),
      });
      setBaseCalcResult(res);
      setCustomBase1(String(res.computed_base_monthly));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Błąd wyliczania indywidualnej podstawy");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const useCustom1 =
        (baseMode === "custom" || baseMode === "creator") &&
        customBase1.trim() !== "" &&
        Number(customBase1) > 0
          ? Number(customBase1)
          : null;
      const useCustom2 =
        (baseMode === "custom" || baseMode === "creator") &&
        customBase2.trim() !== "" &&
        Number(customBase2) > 0
          ? Number(customBase2)
          : null;

      const res = await api.calculateIntegrated({
        scenario,
        insurance_title: insuranceTitle,
        has_sickness_insurance_on_birth_date: insuredOnDate,
        children_count: Number(childrenCount),
        child_age_years: scenario === "birth" ? null : Number(childAgeYears),
        foster_family_type: fosterFamilyType,
        foster_deferred_school: fosterDeferred,
        adoption_short_period_9_weeks: adoptionShort9Weeks,
        previously_used_foster_maternity_weeks:
          scenario === "adoption" ? Number(prevFosterMatWeeks) : 0,
        previously_used_foster_parental_weeks:
          scenario === "adoption" ? Number(prevFosterParWeeks) : 0,
        has_za_zyciem_certificate: hasZaZyciem,
        premature_or_hospitalized: premature,
        gestation_week: premature ? Number(gestationWeek) : null,
        birth_weight_grams: premature ? Number(birthWeight) : null,
        hospitalization_weeks: premature ? Number(hospWeeks) : 0,
        gross_monthly_salary: Number(grossSalary),
        custom_benefit_base: useCustom1,
        second_parent_gross_salary: Number(secondParentGross),
        second_parent_custom_base: useCustom2,
        payment_variant: paymentVariant,
        mother_maternity_weeks: Number(motherMaternityWeeks),
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
        badge="Moduł 2 • Zintegrowany Kalkulator (pkt b, c, d, e, f, j)"
        title="Zintegrowany Kalkulator Zasiłku Macierzyńskiego i Rodzicielskiego"
        description="Jedno narzędzie łączące wszystkie warianty: poród, podział opieki między oboje rodziców, łączenie urlopu rodzicielskiego z pracą, adopcję i rodzinę zastępczą (niezawodową i zawodową), indywidualną podstawę wymiaru zasiłku oraz symulację spraw z zestawów ZUS. Najedź kursorem na dowolną nazwę rubryki, aby zobaczyć podpowiedź."
      />

      {/* Pasek wyboru konkretnej sprawy z zestawów ZUS (pkt f) */}
      <div className="mb-6 rounded-xl border border-[#007834]/30 bg-[#e6f4ec]/60 p-4 shadow-xs dark:border-emerald-800/60 dark:bg-[#007834]/15">
        <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-[#005a27] dark:text-emerald-300">
              Symulacja konkretnej sprawy z zestawów ZUS (pkt f, e, j)
            </p>
            <p className="text-xs text-slate-700 dark:text-slate-300">
              Wybierz gotową sprawę z zestawu testowego ZUS, aby automatycznie wypełnić indywidualną
              podstawę wymiaru zasiłku oraz parametry sprawy:
            </p>
          </div>
          <select
            value={selectedCaseId}
            onChange={(e) => handleLoadSampleCase(e.target.value)}
            className="rounded-lg border border-[#007834] bg-white px-3 py-2 text-xs font-semibold text-slate-900 dark:border-emerald-700 dark:bg-[#111c17] dark:text-slate-100 md:w-96"
          >
            <option value="">-- Wybierz sprawę z zestawu ZUS lub konfiguruj ręcznie --</option>
            {sampleCases.map((c) => (
              <option key={c.case_id} value={c.case_id}>
                {c.title}
              </option>
            ))}
          </select>
        </div>

        {activeSampleCase && (
          <div className="mt-3 rounded-lg border border-[#007834]/20 bg-white p-3 text-xs text-slate-700 dark:border-emerald-900 dark:bg-[#111c17] dark:text-slate-300">
            <p className="font-bold text-slate-900 dark:text-slate-100">{activeSampleCase.title}</p>
            <p className="mt-0.5">{activeSampleCase.description}</p>
            {activeSampleCase.benefit_base_details && (
              <p className="mt-1 font-medium text-slate-800 dark:text-slate-200">
                <strong>Ustalenie indywidualnej podstawy wymiaru:</strong>{" "}
                {activeSampleCase.benefit_base_details}
              </p>
            )}
            <p className="mt-1 font-semibold text-[#005a27] dark:text-emerald-300">
              Rozstrzygnięcie wzorcowe ZUS: {activeSampleCase.expected_decision}
            </p>
          </div>
        )}
      </div>

      <div className="grid gap-8 lg:grid-cols-12">
        <form
          onSubmit={handleSubmit}
          className="space-y-5 rounded-xl border border-slate-200 bg-white p-6 shadow-xs dark:border-emerald-950 dark:bg-[#111c17] lg:col-span-5"
        >
          {/* Scenariusz */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wide text-slate-600 dark:text-slate-400">
              <InfoTooltip
                label="1. Scenariusz rodzicielstwa (pkt b, e, j)"
                tooltip="Wybierz, czy zasiłek dotyczy urodzenia dziecka, przysposobienia (adopcji do 14 r.ż.) czy przyjęcia dziecka na wychowanie jako rodzina zastępcza (do 7 lub 10 r.ż.)."
              />
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
                      ? "border-[#007834] bg-[#e6f4ec] text-[#005a27] dark:bg-[#007834]/20 dark:text-emerald-300"
                      : "border-slate-200 text-slate-600 hover:bg-slate-50 dark:border-emerald-950 dark:text-slate-300 dark:hover:border-emerald-700 dark:hover:bg-[#1e3328] dark:hover:text-white"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Szczegóły dla Adopcji i Rodziny zastępczej (pkt e oraz j) */}
          {scenario !== "birth" && (
            <div className="space-y-3 rounded-lg border border-[#007834]/30 bg-slate-50 p-3.5 dark:border-emerald-900 dark:bg-[#16241d]">
              <p className="text-xs font-bold text-[#005a27] dark:text-emerald-300">
                {scenario === "adoption"
                  ? "Parametry przysposobienia (adopcji) — art. 183 Kodeksu pracy (pkt e, j)"
                  : "Parametry rodziny zastępczej — art. 183 Kodeksu pracy (pkt e, j)"}
              </p>

              {scenario === "foster" && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                    <InfoTooltip
                      label="Forma rodziny zastępczej (art. 29 ust. 1 pkt 3 ustawy zasiłkowej)"
                      tooltip="Zgodnie z art. 183 § 1 Kodeksu pracy i art. 29 ust. 1 pkt 3 ustawy zasiłkowej prawo do urlopu i zasiłku macierzyńskiego przysługuje rodzinom zastępczym niezawodowym (z wyjątkiem rodzin zastępczych zawodowych)."
                    />
                  </label>
                  <select
                    value={fosterFamilyType}
                    onChange={(e) => setFosterFamilyType(e.target.value as FosterFamilyType)}
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs dark:border-slate-700 dark:bg-[#111c17]"
                  >
                    <option value="non_professional">
                      Rodzina zastępcza niezawodowa / spokrewniona (przysługuje zasiłek)
                    </option>
                    <option value="professional">
                      Rodzina zastępcza zawodowa (brak prawa do urlopu i zasiłku — art. 183 § 1 KP)
                    </option>
                  </select>
                </div>
              )}

              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                    <InfoTooltip
                      label="Wiek dziecka (lata, np. 6.9)"
                      tooltip="Urlop na warunkach macierzyńskiego przysługuje do 7. roku życia (rodzina zastępcza), 10. roku życia (przy odroczeniu szkoły) lub 14. roku życia (adopcja). Gdy do granicy wieku zostało mniej niż 9 tygodni, przysługuje gwarantowane 9 tyg. + 38 tyg. rodzicielskiego (art. 183 § 3 KP)."
                    />
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={18}
                    step={0.1}
                    value={childAgeYears}
                    onChange={(e) => setChildAgeYears(Number(e.target.value))}
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm dark:border-slate-700 dark:bg-[#111c17]"
                  />
                </div>
                {scenario === "foster" && (
                  <label className="flex items-center gap-2 self-end text-xs text-slate-700 dark:text-slate-300">
                    <input
                      type="checkbox"
                      checked={fosterDeferred}
                      onChange={(e) => setFosterDeferred(e.target.checked)}
                      className="h-4 w-4 accent-[#007834]"
                    />
                    <InfoTooltip
                      label="Odroczenie obowiązku szkolnego (do 10 lat)"
                      tooltip="Jeśli wobec dziecka podjęto decyzję o odroczeniu obowiązku szkolnego, limit wieku dla rodziny zastępczej wzrasta z 7 do 10 lat."
                    />
                  </label>
                )}
              </div>

              <label className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={adoptionShort9Weeks}
                  onChange={(e) => setAdoptionShort9Weeks(e.target.checked)}
                  className="h-4 w-4 accent-[#007834]"
                />
                <InfoTooltip
                  label="Tryb minimalny z art. 183 § 3 KP (9 tyg. + 38/62 tyg. rodzicielskiego)"
                  tooltip="Minimalny okres zasiłku za urlop na warunkach macierzyńskiego to 9 tygodni (gdy dziecko kończy 7/10/14 lat przed upływem pełnego wymiaru). Urlop rodzicielski wynosi wówczas 38 tygodni (lub 62 tyg. z zaświadczeniem Za życiem)."
                />
              </label>

              {scenario === "adoption" && (
                <div className="grid grid-cols-2 gap-2 border-t border-slate-200 pt-2 dark:border-slate-700">
                  <div>
                    <label className="block text-[10px] text-slate-600 dark:text-slate-400">
                      <InfoTooltip
                        label="Wcześniej w rodz. zastępczej — macierzyński (tyg.)"
                        tooltip="Art. 183 § 7 KP: jeśli przed adopcją korzystano z urlopu jako rodzina zastępcza na to samo dziecko, wymiar urlopu adopcyjnego pomniejsza się o wykorzystane tygodnie."
                      />
                    </label>
                    <input
                      type="number"
                      min={0}
                      max={37}
                      value={prevFosterMatWeeks}
                      onChange={(e) => setPrevFosterMatWeeks(Number(e.target.value))}
                      className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-1 text-xs dark:border-slate-700 dark:bg-[#111c17]"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] text-slate-600 dark:text-slate-400">
                      <InfoTooltip
                        label="Wcześniej w rodz. zastępczej — rodzicielski (tyg.)"
                        tooltip="Art. 183 § 8 KP: wymiar urlopu rodzicielskiego po wystąpieniu o adopcję pomniejsza się o urlop rodzicielski wykorzystany wcześniej jako rodzina zastępcza."
                      />
                    </label>
                    <input
                      type="number"
                      min={0}
                      max={67}
                      value={prevFosterParWeeks}
                      onChange={(e) => setPrevFosterParWeeks(Number(e.target.value))}
                      className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-1 text-xs dark:border-slate-700 dark:bg-[#111c17]"
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Ubezpieczenie i dzieci */}
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                <InfoTooltip
                  label="Tytuł ubezpieczenia"
                  tooltip="Forma zatrudnienia decyduje o tym, czy ubezpieczenie chorobowe jest obowiązkowe (umowa o pracę), czy dobrowolne (zlecenie, JDG), oraz jakie formularze trzeba złożyć."
                />
              </label>
              <select
                value={insuranceTitle}
                onChange={(e) => setInsuranceTitle(e.target.value as InsuranceTitle)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
              >
                <option value="uop">Umowa o pracę</option>
                <option value="zlecenie">Umowa zlecenie</option>
                <option value="jdg">Działalność (JDG)</option>
                <option value="none">Brak ubezpieczenia</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                <InfoTooltip
                  label="Liczba dzieci (1 poród/przyjęcie)"
                  tooltip="Im więcej dzieci urodzonych przy jednym porodzie (lub przyjętych jednocześnie), tym dłuższy urlop macierzyński (od 20 do 37 tygodni) i rodzicielski (41 lub 43 tygodnie)."
                />
              </label>
              <input
                type="number"
                min={1}
                max={6}
                value={childrenCount}
                onChange={(e) => setChildrenCount(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
              />
            </div>
          </div>

          <label className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300">
            <input
              type="checkbox"
              checked={insuredOnDate}
              onChange={(e) => setInsuredOnDate(e.target.checked)}
              className="h-4 w-4 accent-[#007834]"
            />
            <InfoTooltip
              label="Podleganie ubezpieczeniu chorobowemu na dzień porodu / przyjęcia dziecka"
              tooltip="Warunek konieczny do uzyskania zasiłku macierzyńskiego. Przy umowie o pracę jest automatyczny; na zleceniu i JDG musisz być zgłoszony/a do dobrowolnego ubezpieczenia chorobowego."
            />
          </label>

          {/* Podstawa wymiaru zasiłku — w tym indywidualna podstawa wymiaru (pkt f) */}
          <div className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-3.5 dark:border-emerald-950 dark:bg-[#16241d]">
            <p className="text-xs font-bold text-slate-800 dark:text-slate-200">
              <InfoTooltip
                label="Podstawa wymiaru zasiłku — standardowa lub indywidualna (pkt f)"
                tooltip="Możesz wyliczyć podstawę automatycznie z kwoty brutto, wpisać indywidualną podstawę wymiaru bezpośrednio z dokumentu (Z-3/Z-3a) lub użyć kreatora (średnia z 12 mies. z premiami, art. 48a dla JDG, art. 43)."
              />
            </p>
            <div className="grid grid-cols-3 gap-1.5">
              {(
                [
                  { id: "standard", label: "Z kwoty brutto" },
                  { id: "custom", label: "Indywidualna podstawa" },
                  { id: "creator", label: "Kalkulator podstawy" },
                ] as const
              ).map((m) => (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => setBaseMode(m.id)}
                  className={`rounded border px-2 py-1.5 text-[11px] font-semibold transition ${
                    baseMode === m.id
                      ? "border-[#007834] bg-[#007834] text-white"
                      : "border-slate-300 bg-white text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-[#111c17] dark:text-slate-300 dark:hover:border-emerald-700 dark:hover:bg-[#1e3328] dark:hover:text-white"
                  }`}
                >
                  {m.label}
                </button>
              ))}
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  <InfoTooltip
                    label="Brutto rodzica 1 (zł)"
                    tooltip="Przeciętne miesięczne wynagrodzenie brutto z ostatnich 12 miesięcy przed porodem. ZUS pomniejsza je o 13,71% (składki pracownika), aby ustalić podstawę wymiaru zasiłku."
                  />
                </label>
                <input
                  type="number"
                  min={0}
                  step={100}
                  value={grossSalary}
                  onChange={(e) => setGrossSalary(Number(e.target.value))}
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm dark:border-slate-700 dark:bg-[#111c17]"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  <InfoTooltip
                    label="Brutto rodzica 2 (zł)"
                    tooltip="Średnie wynagrodzenie brutto drugiego rodzica (np. ojca) — służy do wyliczenia jego zasiłku za przejęty macierzyński, 9 tygodni rodzicielskiego oraz urlop ojcowski."
                  />
                </label>
                <input
                  type="number"
                  min={0}
                  step={100}
                  value={secondParentGross}
                  onChange={(e) => setSecondParentGross(Number(e.target.value))}
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm dark:border-slate-700 dark:bg-[#111c17]"
                />
              </div>
            </div>

            {(baseMode === "custom" || baseMode === "creator") && (
              <div className="grid gap-3 border-t border-slate-200 pt-2 dark:border-slate-700 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-bold text-[#005a27] dark:text-emerald-300">
                    <InfoTooltip
                      label="Indywidualna podstawa Rodzica 1 (zł)"
                      tooltip="Indywidualna podstawa wymiaru zasiłku po odliczeniu 13,71% (np. wyliczona z formularza Z-3/Z-3a lub poświadczenia ubezpieczenia ZUS)."
                    />
                  </label>
                  <input
                    type="number"
                    min={0}
                    step={0.01}
                    placeholder="np. 6903.20"
                    value={customBase1}
                    onChange={(e) => setCustomBase1(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-[#007834] bg-white px-3 py-1.5 text-sm font-semibold dark:bg-[#111c17]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300">
                    <InfoTooltip
                      label="Indywidualna podstawa Rodzica 2 (zł)"
                      tooltip="Opcjonalna indywidualna podstawa wymiaru zasiłku dla drugiego rodzica (po odliczeniu 13,71%)."
                    />
                  </label>
                  <input
                    type="number"
                    min={0}
                    step={0.01}
                    placeholder="np. 7075.78"
                    value={customBase2}
                    onChange={(e) => setCustomBase2(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm dark:border-slate-700 dark:bg-[#111c17]"
                  />
                </div>
              </div>
            )}

            {baseMode === "creator" && (
              <div className="space-y-2.5 rounded-lg border border-[#007834]/30 bg-white p-3 text-xs dark:border-emerald-900 dark:bg-[#111c17]">
                <p className="font-bold text-[#005a27] dark:text-emerald-300">
                  Kreator indywidualnej podstawy wymiaru zasiłku (Art. 36–50 ustawy zasiłkowej)
                </p>
                <select
                  value={creatorSubMode}
                  onChange={(e) =>
                    setCreatorSubMode(
                      e.target.value as "uop_12m" | "jdg_art48a" | "previous_benefit"
                    )
                  }
                  className="w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs dark:border-slate-700"
                >
                  <option value="uop_12m">
                    Pracownik / Zlecenie: średnia z miesięcy (Z-3/Z-3a) + premie kwartalne/roczne (1/12)
                  </option>
                  <option value="jdg_art48a">
                    Działalność gospodarcza (JDG): proporcjonalna podstawa wg Art. 48a (&lt; 12 mies.)
                  </option>
                  <option value="previous_benefit">
                    Zachowana podstawa z poprzedniego zasiłku (przerwa &lt; 1 mies. — Art. 43)
                  </option>
                </select>

                {creatorSubMode === "uop_12m" && (
                  <div className="space-y-2">
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                        Wynagrodzenia brutto z pełnych miesięcy (oddzielone przecinkiem, do 12 mies.)
                      </label>
                      <input
                        type="text"
                        value={creatorSalariesText}
                        onChange={(e) => setCreatorSalariesText(e.target.value)}
                        className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="block text-[10px] text-slate-600 dark:text-slate-400">
                          Suma premii kwartalnych z 4 kw. (1/12 — art. 42 ust. 2)
                        </label>
                        <input
                          type="number"
                          min={0}
                          value={creatorQuarterlyBonus}
                          onChange={(e) => setCreatorQuarterlyBonus(Number(e.target.value))}
                          className="w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] text-slate-600 dark:text-slate-400">
                          Nagroda roczna / 13-tka za rok poprz. (1/12 — art. 42 ust. 3)
                        </label>
                        <input
                          type="number"
                          min={0}
                          value={creatorAnnualBonus}
                          onChange={(e) => setCreatorAnnualBonus(Number(e.target.value))}
                          className="w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="block text-[10px] text-slate-600 dark:text-slate-400">
                          Miesiące wyłączone (&lt;1/2 czasu pracy — art. 38)
                        </label>
                        <input
                          type="number"
                          min={0}
                          max={11}
                          value={creatorExcludedMonths}
                          onChange={(e) => setCreatorExcludedMonths(Number(e.target.value))}
                          className="w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] text-slate-600 dark:text-slate-400">
                          Wymiar etatu (dla min. podstawy z art. 45)
                        </label>
                        <input
                          type="number"
                          min={0.1}
                          max={1.0}
                          step={0.1}
                          value={creatorFte}
                          onChange={(e) => setCreatorFte(Number(e.target.value))}
                          className="w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                        />
                      </div>
                    </div>
                  </div>
                )}

                {creatorSubMode === "jdg_art48a" && (
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <label className="block text-[10px] text-slate-600 dark:text-slate-400">
                        Pełne mies. chorobowego (1–12)
                      </label>
                      <input
                        type="number"
                        min={1}
                        max={12}
                        value={creatorJdgMonths}
                        onChange={(e) => setCreatorJdgMonths(Number(e.target.value))}
                        className="w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] text-slate-600 dark:text-slate-400">
                        Deklarowana podstawa (zł)
                      </label>
                      <input
                        type="number"
                        min={0}
                        step={100}
                        value={creatorJdgDeclared}
                        onChange={(e) => setCreatorJdgDeclared(Number(e.target.value))}
                        className="w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] text-slate-600 dark:text-slate-400">
                        Najniższa podstawa JDG (zł)
                      </label>
                      <input
                        type="number"
                        min={0}
                        step={100}
                        value={creatorJdgMin}
                        onChange={(e) => setCreatorJdgMin(Number(e.target.value))}
                        className="w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                      />
                    </div>
                  </div>
                )}

                {creatorSubMode === "previous_benefit" && (
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                      Poprzednia podstawa wymiaru zasiłku (np. z zasiłku chorobowego w ciąży, zł)
                    </label>
                    <input
                      type="number"
                      min={0}
                      step={0.01}
                      value={creatorPrevBase}
                      onChange={(e) => setCreatorPrevBase(Number(e.target.value))}
                      className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                    />
                  </div>
                )}

                <button
                  type="button"
                  onClick={handleComputeIndividualBase}
                  className="w-full rounded bg-[#007834] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#005a27]"
                >
                  Wylicz indywidualną podstawę wymiaru i wstaw do kalkulatora
                </button>

                {baseCalcResult && (
                  <div className="rounded bg-[#e6f4ec] p-2.5 text-[11px] text-[#005a27] dark:bg-[#007834]/20 dark:text-emerald-300">
                    <p className="font-bold">
                      Wyliczona podstawa: {baseCalcResult.computed_base_monthly.toFixed(2)} zł (stawka
                      dzienna 100%: {baseCalcResult.daily_rate_100_percent.toFixed(2)} zł | 81,5%:{" "}
                      {baseCalcResult.daily_rate_81_5_percent.toFixed(2)} zł | 70%:{" "}
                      {baseCalcResult.daily_rate_70_percent.toFixed(2)} zł)
                    </p>
                    <ul className="mt-1 list-disc pl-4">
                      {baseCalcResult.explanation_steps.map((s, idx) => (
                        <li key={idx}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                <InfoTooltip
                  label="Wariant wypłaty"
                  tooltip="81,5% przez cały okres wymaga złożenia jednego wniosku w ciągu 21 dni od porodu/przyjęcia dziecka. Wariant 100% + 70% oznacza 100% na macierzyńskim i 70% na rodzicielskim."
                />
              </label>
              <select
                value={paymentVariant}
                onChange={(e) => setPaymentVariant(e.target.value as PaymentVariant)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
              >
                <option value="81_5">81,5% (wniosek w 21 dni)</option>
                <option value="100_70">100% macierzyński + 70% rodzicielski</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                <InfoTooltip
                  label="Ubezpieczeni u płatnika"
                  tooltip="Liczba osób zgłoszonych do ubezpieczenia chorobowego przez Twojego pracodawcę na dzień 30 listopada poprzedniego roku. Powyżej 20 osób zasiłek wypłaca pracodawca, do 20 osób — ZUS."
                />
              </label>
              <input
                type="number"
                min={0}
                value={employerCount}
                onChange={(e) => setEmployerCount(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
              />
            </div>
          </div>

          {/* Podział między rodziców */}
          <div className="space-y-2 rounded-lg border border-slate-200 p-3 dark:border-emerald-950">
            <p className="text-xs font-bold text-slate-700 dark:text-slate-300">
              <InfoTooltip
                label="2. Podział opieki między rodziców (pkt d, e, j)"
                tooltip="Urlopem macierzyńskim (po pierwszych 14 tygodniach przy porodzie) lub urlopem na warunkach macierzyńskiego i rodzicielskim możecie się podzielić między oboje rodziców."
              />
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="block text-[11px] text-slate-600 dark:text-slate-400">
                  <InfoTooltip
                    label={
                      scenario === "birth"
                        ? "Macierzyński matki (min. 14 tyg.)"
                        : "Urlop na warunkach macierzyńskiego — Rodzic 1 (tyg.)"
                    }
                    tooltip={
                      scenario === "birth"
                        ? "Pierwsze 14 tygodni po porodzie matka musi wykorzystać osobiście. Pozostałą część (np. 6 tygodni przy 1 dziecku) może przejąć ojciec dziecka."
                        : "Liczba tygodni urlopu na warunkach urlopu macierzyńskiego wykorzystana przez pierwszego rodzica adopcyjnego/zastępczego (pozostałą część może wykorzystać drugi rodzic)."
                    }
                  />
                </label>
                <input
                  type="number"
                  min={scenario === "birth" ? 14 : 0}
                  max={37}
                  value={motherMaternityWeeks}
                  onChange={(e) => setMotherMaternityWeeks(Number(e.target.value))}
                  className="mt-1 w-full rounded border border-slate-300 px-2.5 py-1.5 text-sm dark:border-slate-700"
                />
              </div>
              <div>
                <label className="block text-[11px] text-slate-600 dark:text-slate-400">
                  <InfoTooltip
                    label="Rodzicielski dla 2. rodzica (tyg.)"
                    tooltip="Każdemu z rodziców przysługuje 9 tygodni wyłącznego, nieprzenoszalnego urlopu rodzicielskiego (płatne 70%). Jeśli drugi rodzic ich nie wykorzysta, przepadają."
                  />
                </label>
                <input
                  type="number"
                  min={0}
                  max={67}
                  value={fatherParentalWeeks}
                  onChange={(e) => setFatherParentalWeeks(Number(e.target.value))}
                  className="mt-1 w-full rounded border border-slate-300 px-2.5 py-1.5 text-sm dark:border-slate-700"
                />
              </div>
            </div>
            {scenario !== "foster" && (
              <label className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={fatherPaternity}
                  onChange={(e) => setFatherPaternity(e.target.checked)}
                  className="h-4 w-4 accent-[#007834]"
                />
                <InfoTooltip
                  label="Uwzględnij urlop ojcowski (2 tygodnie, 100%)"
                  tooltip="Wyłączne prawo ojca biologicznego lub adopcyjnego (14 dni kalendarzowych jednorazowo lub w 2 częściach po 7 dni)."
                />
              </label>
            )}
          </div>

          {/* Opcje zaawansowane */}
          <div className="space-y-2 rounded-lg border border-slate-200 p-3 dark:border-emerald-950">
            <p className="text-xs font-bold text-slate-700 dark:text-slate-300">3. Opcje dodatkowe</p>
            <label className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                checked={hasZaZyciem}
                onChange={(e) => setHasZaZyciem(e.target.checked)}
                className="h-4 w-4 accent-[#007834]"
              />
              <InfoTooltip
                label="Zaświadczenie „Za życiem” (65/67 tyg.)"
                tooltip="Wydawane przez lekarza specjalistę przy ciężkim i nieodwracalnym upośledzeniu lub nieuleczalnej chorobie zagrażającej życiu. Wydłuża urlop rodzicielski o 24 tygodnie."
              />
            </label>

            <label className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                checked={premature}
                onChange={(e) => setPremature(e.target.checked)}
                className="h-4 w-4 accent-[#007834]"
              />
              <InfoTooltip
                label="Wcześniak / hospitalizacja (uzupełniający urlop)"
                tooltip="Dodatkowy urlop macierzyński (płatny 100%) udzielany jednorazowo po macierzyńskim: 1 tydzień za każdy tydzień pobytu dziecka w szpitalu (do 8 lub 15 tygodni)."
              />
            </label>
            {premature && (
              <div className="grid grid-cols-3 gap-2 pt-1">
                <div>
                  <label className="block text-[10px] text-slate-500 dark:text-slate-400">
                    <InfoTooltip
                      label="Tydzień ciąży"
                      tooltip="Urodzenie przed 28. tygodniem ciąży daje wyższy limit uzupełniającego urlopu (do 15 tygodni zamiast 8)."
                    />
                  </label>
                  <input
                    type="number"
                    min={20}
                    max={42}
                    value={gestationWeek}
                    onChange={(e) => setGestationWeek(Number(e.target.value))}
                    className="w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-slate-500 dark:text-slate-400">
                    <InfoTooltip
                      label="Masa (g)"
                      tooltip="Masa urodzeniowa ≤ 1000 g również uprawnia do wyższego limitu uzupełniającego urlopu (maks. 15 tygodni)."
                    />
                  </label>
                  <input
                    type="number"
                    min={300}
                    max={6000}
                    value={birthWeight}
                    onChange={(e) => setBirthWeight(Number(e.target.value))}
                    className="w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-slate-500 dark:text-slate-400">
                    <InfoTooltip
                      label="Szpital (tyg.)"
                      tooltip="Łączna liczba tygodni pobytu dziecka w szpitalu po porodzie (niepełny tydzień zaokrągla się w górę)."
                    />
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={20}
                    value={hospWeeks}
                    onChange={(e) => setHospWeeks(Number(e.target.value))}
                    className="w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                  />
                </div>
              </div>
            )}

            <label className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                checked={combineWork}
                onChange={(e) => setCombineWork(e.target.checked)}
                className="h-4 w-4 accent-[#007834]"
              />
              <InfoTooltip
                label="Łączenie urlopu rodzicielskiego z pracą (maks. 1/2 etatu)"
                tooltip="Pracownik na umowie o pracę może pracować u swojego pracodawcy maks. na pół etatu podczas urlopu rodzicielskiego — urlop ulega wtedy proporcjonalnemu wydłużeniu."
              />
            </label>
            {combineWork && (
              <div className="grid grid-cols-2 gap-2 pt-1">
                <div>
                  <label className="block text-[10px] text-slate-500 dark:text-slate-400">
                    <InfoTooltip
                      label="Wymiar etatu (0.1–0.5)"
                      tooltip="Część pełnego etatu, na jaką wracasz do pracy podczas urlopu rodzicielskiego (np. 0.5 = pół etatu)."
                    />
                  </label>
                  <input
                    type="number"
                    min={0.1}
                    max={0.5}
                    step={0.1}
                    value={workFte}
                    onChange={(e) => setWorkFte(Number(e.target.value))}
                    className="w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-slate-500 dark:text-slate-400">
                    <InfoTooltip
                      label="Liczba tyg. pracy"
                      tooltip="Przez ile tygodni urlopu rodzicielskiego planujesz łączyć opiekę nad dzieckiem z pracą na część etatu."
                    />
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={41}
                    value={workWeeks}
                    onChange={(e) => setWorkWeeks(Number(e.target.value))}
                    className="w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                  />
                </div>
              </div>
            )}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-[#007834] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#005a27] disabled:opacity-50"
          >
            {loading ? "Obliczanie..." : "Oblicz wymiary i wysokość zasiłku"}
          </button>

          {error && <p className="text-xs text-red-600">{error}</p>}
        </form>

        {/* Wyniki */}
        <div className="space-y-5 lg:col-span-7">
          {result ? (
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs dark:border-emerald-950 dark:bg-[#111c17]">
              {!result.eligible ? (
                <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-800/60 dark:bg-red-950/40 dark:text-red-200">
                  <p className="font-bold">Brak uprawnień do zasiłku macierzyńskiego</p>
                  <p className="mt-1">{result.ineligibility_reason}</p>
                </div>
              ) : (
                <>
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <div className="rounded-lg bg-[#e6f4ec] p-4 dark:bg-[#007834]/20">
                      <p className="text-xs text-[#005a27] dark:text-emerald-300">
                        Łączny czas urlopów
                      </p>
                      <p className="mt-1 text-2xl font-bold text-[#005a27] dark:text-emerald-300">
                        {result.total_weeks} tyg.
                      </p>
                    </div>
                    <div className="rounded-lg bg-slate-50 p-4 dark:bg-[#16241d]">
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        Szacowana suma brutto
                      </p>
                      <p className="mt-1 text-xl font-bold text-slate-900 dark:text-slate-100">
                        {result.total_estimated_gross_pln.toLocaleString("pl-PL")} zł
                      </p>
                    </div>
                    <div className="rounded-lg bg-slate-50 p-4 dark:bg-[#16241d]">
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        Podstawa Rodzica 1
                      </p>
                      <p className="mt-1 text-lg font-bold text-slate-900 dark:text-slate-100">
                        {result.benefit_base_parent1.toFixed(2)} zł
                      </p>
                    </div>
                    <div className="rounded-lg bg-slate-50 p-4 dark:bg-[#16241d]">
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        Podstawa Rodzica 2
                      </p>
                      <p className="mt-1 text-lg font-bold text-slate-900 dark:text-slate-100">
                        {result.benefit_base_parent2.toFixed(2)} zł
                      </p>
                    </div>
                  </div>

                  {/* Szczegółowe wyjaśnienie podstawy wymiaru zasiłku (pkt f) */}
                  {result.benefit_base_explanation && (
                    <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700 dark:border-emerald-950 dark:bg-[#16241d] dark:text-slate-300">
                      <p className="font-bold text-slate-900 dark:text-slate-100">
                        Sposób ustalenia podstawy wymiaru zasiłku (pkt f):
                      </p>
                      <p className="mt-1">
                        <strong>Rodzic 1:</strong> {result.benefit_base_explanation}
                      </p>
                      {result.benefit_base_parent2_explanation && (
                        <p className="mt-0.5">
                          <strong>Rodzic 2:</strong> {result.benefit_base_parent2_explanation}
                        </p>
                      )}
                    </div>
                  )}

                  <p className="mt-4 text-xs text-slate-600 dark:text-slate-400">
                    <strong>Płatnik świadczenia:</strong> {result.payer}
                  </p>

                  {/* Tabela harmonogramu */}
                  <div className="mt-5 overflow-x-auto">
                    <table className="w-full border-collapse text-left text-xs">
                      <thead>
                        <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 dark:border-emerald-950 dark:bg-[#16241d] dark:text-slate-400">
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
                          <tr
                            key={idx}
                            className="border-b border-slate-100 dark:border-slate-800"
                          >
                            <td className="p-2.5 font-medium text-slate-900 dark:text-slate-100">
                              {row.label}
                              {row.notes && (
                                <p className="mt-0.5 text-[11px] font-normal text-slate-500 dark:text-slate-400">
                                  {row.notes}
                                </p>
                              )}
                            </td>
                            <td className="p-2.5 text-slate-700 dark:text-slate-300">
                              {row.parent}
                            </td>
                            <td className="p-2.5 text-right font-semibold">{row.weeks}</td>
                            <td className="p-2.5 text-right">{row.rate_percent}%</td>
                            <td className="p-2.5 text-right">
                              {row.monthly_gross_pln.toFixed(2)} zł
                            </td>
                            <td className="p-2.5 text-right font-semibold text-[#005a27] dark:text-emerald-300">
                              {row.total_gross_pln.toFixed(2)} zł
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {result.required_documents.length > 0 && (
                    <div className="mt-5 rounded-lg bg-slate-50 p-4 dark:bg-[#16241d]">
                      <p className="text-xs font-bold text-slate-800 dark:text-slate-200">
                        Wymagane dokumenty
                      </p>
                      <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-slate-700 dark:text-slate-300">
                        {result.required_documents.map((doc, i) => (
                          <li key={i}>{doc}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              )}

              {result.warnings.length > 0 && (
                <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-800/60 dark:bg-amber-950/40">
                  <p className="text-xs font-bold text-amber-900 dark:text-amber-200">
                    Uwagi i zasady prawne
                  </p>
                  <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-amber-900 dark:text-amber-200">
                    {result.warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500 dark:border-slate-700 dark:bg-[#111c17] dark:text-slate-400">
              Skonfiguruj parametry po lewej stronie (lub wybierz gotową sprawę z zestawu ZUS u góry)
              i kliknij „Oblicz wymiary i wysokość zasiłku”, aby wygenerować symulację dla obojga
              rodziców.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
