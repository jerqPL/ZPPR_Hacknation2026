"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { InfoTooltip } from "@/components/InfoTooltip";
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
  const [waitingExempt, setWaitingExempt] = useState(false);
  const [ageOver50, setAgeOver50] = useState(false);
  const [grossSalary, setGrossSalary] = useState(user?.declared_gross_salary ?? 6500);
  const [customBase, setCustomBase] = useState<string>("");
  const [hasCodeB, setHasCodeB] = useState(true);
  const [employerCount, setEmployerCount] = useState(user?.employer_insured_count ?? 25);
  const [contributionDebt, setContributionDebt] = useState(user?.debt_amount_pln ?? 0);
  const [specialTermination, setSpecialTermination] = useState(false);
  const [terminationReason, setTerminationReason] = useState("bankruptcy_liquidation");

  const [result, setResult] = useState<PregnancyBenefitResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) {
      setInsuranceTitle(user.insurance_title);
      setHasVoluntary(user.has_sickness_insurance);
      setInsuranceDays(user.insurance_days);
      setGrossSalary(user.declared_gross_salary);
      setEmployerCount(user.employer_insured_count);
      setContributionDebt(user.debt_amount_pln || 0);
    }
  }, [user]);

  const handleCalculate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await api.calculatePregnancy({
        insurance_title: insuranceTitle,
        has_voluntary_sickness_insurance: hasVoluntary,
        insurance_days: Number(insuranceDays),
        waiting_period_exempt: waitingExempt,
        age_over_50: ageOver50,
        gross_monthly_salary: Number(grossSalary),
        custom_benefit_base:
          customBase.trim() !== "" && Number(customBase) > 0 ? Number(customBase) : null,
        has_code_b: hasCodeB,
        employer_insured_count: Number(employerCount),
        contribution_debt_pln: insuranceTitle === "jdg" ? Number(contributionDebt) : 0,
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
        badge="Moduł 1 • Okres ciąży (pkt a)"
        title="Świadczenia w czasie ciąży"
        description="Sprawdź uprawnienia do zasiłku chorobowego (kod literowy B = 100% do 270 dni), świadczenia rehabilitacyjnego (100% do 12 miesięcy) oraz zasiłku w wysokości zasiłku macierzyńskiego po ustaniu zatrudnienia."
      />

      <div className="grid gap-8 lg:grid-cols-12">
        <form
          onSubmit={handleCalculate}
          className="space-y-4 rounded-xl border border-slate-200 dark:border-emerald-950 bg-white dark:bg-[#111c17] p-6 shadow-xs lg:col-span-5"
        >
          <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
            Twoja sytuacja ubezpieczeniowa
          </h2>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
              <InfoTooltip
                label="Tytuł ubezpieczenia"
                tooltip="Na umowie o pracę ubezpieczenie chorobowe jest obowiązkowe (okres wyczekiwania 30 dni). Na zleceniu i JDG jest dobrowolne (okres wyczekiwania 90 dni)."
              />
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
                <InfoTooltip
                  label="Okres ubezpieczenia (dni)"
                  tooltip="Liczba dni nieprzerwanego ubezpieczenia chorobowego (wlicza się poprzednie okresy, jeśli przerwa nie przekroczyła 30 dni — art. 4 ust. 2 ustawy zasiłkowej)."
                />
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
                <InfoTooltip
                  label="Wynagrodzenie / podstawa brutto (zł)"
                  tooltip="Przeciętne miesięczne wynagrodzenie lub zadeklarowana podstawa składek brutto z 12 miesięcy przed niezdolnością do pracy."
                />
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

          <label className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300">
            <input
              type="checkbox"
              checked={waitingExempt}
              onChange={(e) => setWaitingExempt(e.target.checked)}
              className="h-4 w-4 accent-[#007834]"
            />
            <InfoTooltip
              label="Zwolnienie z okresu wyczekiwania (art. 4 ust. 3 ustawy zasiłkowej)"
              tooltip="Prawo do zasiłku od 1. dnia ubezpieczenia przysługuje m.in. osobom obowiązkowo ubezpieczonym z co najmniej 10-letnim wcześniejszym okresem obowiązkowego ubezpieczenia chorobowego oraz absolwentom szkół/uczelni w ciągu 90 dni od ukończenia nauki."
            />
          </label>

          {insuranceTitle === "uop" && (
            <label className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                checked={ageOver50}
                onChange={(e) => setAgeOver50(e.target.checked)}
                className="h-4 w-4 accent-[#007834]"
              />
              <InfoTooltip
                label="Ukończony 50. rok życia (14 dni wynagrodzenia chorobowego zamiast 33 dni)"
                tooltip="Zgodnie z art. 92 § 1 pkt 1 Kodeksu pracy pracodawca finansuje wynagrodzenie chorobowe przez 33 dni w roku kalendarzowym, a dla pracownika po ukończeniu 50. roku życia — przez 14 dni (od 15. dnia zasiłek finansuje FUS)."
              />
            </label>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
              <InfoTooltip
                label="Indywidualna podstawa wymiaru zasiłku (opcjonalnie, zł po -13,71% — pkt f)"
                tooltip="Jeśli znasz swoją dokładną indywidualną podstawę wymiaru zasiłku (np. z formularza Z-3/Z-3a lub poświadczenia ZUS), wpisz ją tutaj."
              />
            </label>
            <input
              type="number"
              min={0}
              step={0.01}
              placeholder="Pozostaw puste, aby wyliczyć automatycznie z kwoty brutto"
              value={customBase}
              onChange={(e) => setCustomBase(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm"
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
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

            {insuranceTitle === "jdg" && (
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  <InfoTooltip
                    label="Zaległość składkowa ZUS (zł)"
                    tooltip="Art. 2a ustawy zasiłkowej: zadłużenie przekraczające 1% minimalnego wynagrodzenia (48,06 zł w 2026 r.) wstrzymuje wypłatę zasiłku na JDG do czasu spłaty."
                  />
                </label>
                <input
                  type="number"
                  min={0}
                  step={10}
                  value={contributionDebt}
                  onChange={(e) => setContributionDebt(Number(e.target.value))}
                  className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm"
                />
              </div>
            )}
          </div>

          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
            <input
              type="checkbox"
              checked={hasCodeB}
              onChange={(e) => setHasCodeB(e.target.checked)}
              className="h-4 w-4 accent-[#007834]"
            />
            Zaświadczenie lekarskie e-ZLA zawiera kod literowy „B” (ciąża = 100%)
          </label>

          <div className="rounded-lg border border-slate-200 dark:border-emerald-950 bg-slate-50 dark:bg-[#16241d] p-3">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-800 dark:text-slate-200">
              <input
                type="checkbox"
                checked={specialTermination}
                onChange={(e) => setSpecialTermination(e.target.checked)}
                className="h-4 w-4 accent-[#007834]"
              />
              <InfoTooltip
                label="Szczególna sytuacja: utrata zatrudnienia w ciąży (zasiłek w wys. macierzyńskiego)"
                tooltip="Art. 30 ust. 3 ustawy zasiłkowej: w razie upadłości, likwidacji, śmierci pracodawcy albo rozwiązania umowy z naruszeniem przepisów prawa (stwierdzonym wyrokiem sądu) przysługuje do dnia porodu zasiłek w wysokości zasiłku macierzyńskiego (100%)."
              />
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
                <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                  Wynik analizy
                </h2>
                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${
                    result.eligible_sickness_benefit || result.eligible_maternity_equivalent
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-red-100 text-red-800 dark:text-red-200"
                  }`}
                >
                  {result.eligible_maternity_equivalent
                    ? "Zasiłek w wys. macierzyńskiego (100%)"
                    : result.eligible_sickness_benefit
                    ? "Uprawnienie potwierdzone"
                    : "Brak uprawnień"}
                </span>
              </div>

              <p className="mt-3 text-sm text-slate-700 dark:text-slate-300">{result.summary}</p>

              <div className="mt-5 grid gap-4 sm:grid-cols-3">
                <div className="rounded-lg bg-slate-50 dark:bg-[#16241d] p-4">
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Podstawa wymiaru (mies.)
                  </p>
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

              {result.benefit_base_explanation && (
                <p className="mt-3 rounded bg-slate-50 dark:bg-[#16241d] p-2.5 text-xs text-slate-600 dark:text-slate-300">
                  <strong>Ustalenie podstawy wymiaru:</strong> {result.benefit_base_explanation}
                </p>
              )}

              <dl className="mt-5 grid gap-2 text-xs text-slate-700 dark:text-slate-300 sm:grid-cols-2">
                <div className="rounded border border-slate-100 dark:border-slate-800 p-2.5">
                  <dt className="text-slate-500 dark:text-slate-400">Kto wypłaca zasiłek</dt>
                  <dd className="font-semibold text-slate-900 dark:text-slate-100">
                    {result.payer}
                  </dd>
                </div>
                <div className="rounded border border-slate-100 dark:border-slate-800 p-2.5">
                  <dt className="text-slate-500 dark:text-slate-400">
                    Okres zasiłkowy / finansowanie
                  </dt>
                  <dd className="font-semibold text-slate-900 dark:text-slate-100">
                    {result.max_benefit_days === 0
                      ? "Brak okresu zasiłkowego"
                      : result.employer_pay_days > 0
                      ? `Maks. ${result.max_benefit_days} dni (pierwsze ${result.employer_pay_days} dni wynagrodzenie chorobowe pracodawcy, od ${result.employer_pay_days + 1}. dnia zasiłek z FUS)`
                      : `Maks. ${result.max_benefit_days} dni (zasiłek z FUS od 1. dnia niezdolności do pracy)`}
                  </dd>
                </div>
              </dl>

              {result.warnings.length > 0 && (
                <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-800/60 dark:bg-amber-950/40 p-4">
                  <p className="text-xs font-bold text-amber-900 dark:text-amber-200">
                    Ważne uwagi prawne
                  </p>
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
              zasiłku chorobowego, świadczenia rehabilitacyjnego oraz zasiłku w wysokości zasiłku
              macierzyńskiego.
            </div>
          )}

          <div className="rounded-xl border border-slate-200 dark:border-emerald-950 bg-white dark:bg-[#111c17] p-5 text-xs text-slate-600 dark:text-slate-400">
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              Świadczenie rehabilitacyjne w okresie ciąży (art. 18–19 ustawy zasiłkowej)
            </h3>
            <p className="mt-1 leading-relaxed">
              Jeśli po wyczerpaniu 270 dni okresu zasiłkowego kobieta nadal jest niezdolna do pracy,
              a dalsze leczenie lub rehabilitacja rokują odzyskanie zdolności do pracy, przysługuje
              jej świadczenie rehabilitacyjne przez okres do 12 miesięcy (360 dni). W okresie ciąży
              wynosi ono <strong>100% zwaloryzowanej podstawy wymiaru zasiłku chorobowego</strong>.
            </p>
            {result && (result.eligible_sickness_benefit || result.eligible_maternity_equivalent) && (
              <div className="mt-3 grid gap-2 rounded-lg bg-slate-50 dark:bg-[#16241d] p-3 sm:grid-cols-2">
                <div>
                  <span className="text-slate-500 dark:text-slate-400">
                    Szacowane świadczenie rehabilitacyjne (100% mies.):
                  </span>
                  <p className="text-sm font-bold text-[#005a27] dark:text-emerald-300">
                    {(result.rehabilitation_monthly_gross ?? result.benefit_base_monthly).toFixed(2)} zł
                  </p>
                </div>
                <div>
                  <span className="text-slate-500 dark:text-slate-400">
                    Stawka dzienna (maks. {result.rehabilitation_max_days ?? 360} dni):
                  </span>
                  <p className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    {(result.rehabilitation_daily_gross ?? result.daily_benefit_gross).toFixed(2)} zł / dzień
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
