"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { InfoTooltip } from "@/components/InfoTooltip";
import { useUser } from "@/components/UserContext";
import { api } from "@/lib/api";
import type {
  InsuranceTitle,
  PregnancyBenefitResponse,
  WaitingPeriodExemptionReason,
} from "@/lib/types";

export default function PregnancyPage() {
  const { user } = useUser();

  const [insuranceTitle, setInsuranceTitle] = useState<InsuranceTitle>(
    user?.insurance_title || "uop"
  );
  const [hasVoluntary, setHasVoluntary] = useState(user ? user.has_sickness_insurance : true);
  const [insuranceDays, setInsuranceDays] = useState(user?.insurance_days ?? 180);
  const [waitingExemptionReason, setWaitingExemptionReason] =
    useState<WaitingPeriodExemptionReason>("none");
  const [fteFraction, setFteFraction] = useState(1.0);
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
        waiting_period_exempt: waitingExemptionReason !== "none",
        waiting_period_exemption_reason: waitingExemptionReason,
        fte_fraction: insuranceTitle === "uop" ? Math.max(0.05, Math.min(1.0, Number(fteFraction) || 1.0)) : 1.0,
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

  const getBadgeStyleAndLabel = (r: PregnancyBenefitResponse) => {
    if (r.payout_suspended_due_to_debt) {
      return {
        cls: "border border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-600/40 dark:bg-amber-950/50 dark:text-amber-200",
        label: "Wypłata wstrzymana — zadłużenie ZUS (art. 2a)",
      };
    }
    if (r.eligible_maternity_equivalent) {
      return {
        cls: "border border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/15 dark:text-emerald-300",
        label: "Zasiłek w wys. macierzyńskiego (100% do porodu)",
      };
    }
    if (r.eligible_post_birth_maternity_art30 && !r.eligible_maternity_equivalent) {
      return {
        cls: "border border-sky-300 bg-sky-50 text-sky-900 dark:border-sky-600/40 dark:bg-sky-950/50 dark:text-sky-200",
        label: "Brak zasiłku przed porodem — macierzyński PO porodzie (art. 30 ust. 1 pkt 2)",
      };
    }
    if (r.eligible_sickness_benefit) {
      return {
        cls: "border border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/15 dark:text-emerald-300",
        label: "Uprawnienie potwierdzone",
      };
    }
    return {
      cls: "border border-red-200 bg-red-50 text-red-800 dark:border-red-500/30 dark:bg-red-500/15 dark:text-red-300",
      label: "Brak uprawnień",
    };
  };

  return (
    <div>
      <PageHeader
        badge="Okres ciąży"
        title="Świadczenia w czasie ciąży"
        description="Sprawdź uprawnienia do zasiłku chorobowego (kod literowy B = 100% do 270 dni), świadczenia rehabilitacyjnego (100% do 12 miesięcy) oraz świadczeń po ustaniu zatrudnienia w ciąży (art. 7, art. 30 i art. 46 ustawy zasiłkowej)."
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
                className="h-4 w-4 shrink-0 accent-[#007834]"
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
                step="any"
                value={grossSalary}
                onChange={(e) => setGrossSalary(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
              <InfoTooltip
                label="Zwolnienie z okresu wyczekiwania (art. 4 ust. 3 ustawy zasiłkowej)"
                tooltip="10-letni staż obowiązkowego ubezpieczenia (pkt 3) zwalnia wyłącznie na umowie o pracę. Absolwenci w ciągu 90 dni (pkt 1) i wypadek w drodze do/z pracy (pkt 2) dają prawo od 1. dnia także przy JDG i zleceniu."
              />
            </label>
            <select
              value={waitingExemptionReason}
              onChange={(e) =>
                setWaitingExemptionReason(e.target.value as WaitingPeriodExemptionReason)
              }
              className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-xs"
            >
              <option value="none">Brak zwolnienia (standardowo 30 dni UoP / 90 dni dobrowolne)</option>
              <option value="mandatory_10_years">
                Min. 10 lat obowiązkowego ubezpieczenia chorobowego (art. 4 ust. 3 pkt 3 — tylko UoP)
              </option>
              <option value="graduate_90_days">
                Absolwent szkoły/uczelni/szkoły doktorskiej w ciągu 90 dni (art. 4 ust. 3 pkt 1 — UoP/JDG/zlecenie)
              </option>
              <option value="commute_accident">
                Wypadek w drodze do pracy lub z pracy (art. 4 ust. 3 pkt 2 — UoP/JDG/zlecenie)
              </option>
            </select>
          </div>

          {insuranceTitle === "uop" && (
            <div className="grid gap-3 sm:grid-cols-2 items-center">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  <InfoTooltip
                    label="Wymiar etatu (art. 45)"
                    tooltip="Minimalna podstawa wymiaru zasiłku pracownika (4 147,10 zł dla pełnego etatu w 2026 r.) ulega proporcjonalnemu zmniejszeniu przy niepełnym etacie (np. 0.5 etatu = 2 073,55 zł)."
                  />
                </label>
                <input
                  type="number"
                  min={0.1}
                  max={1.0}
                  step="any"
                  value={fteFraction}
                  onChange={(e) => setFteFraction(Number(e.target.value))}
                  className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm"
                />
              </div>
              <label className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300 pt-4">
                <input
                  type="checkbox"
                  checked={ageOver50}
                  onChange={(e) => setAgeOver50(e.target.checked)}
                  className="h-4 w-4 shrink-0 accent-[#007834]"
                />
                <InfoTooltip
                  label="Po roku ukończenia 50. r.ż. (14 dni zamiast 33)"
                  tooltip="Zgodnie z art. 92 § 1 pkt 1 i § 5 KP skrócony 14-dniowy okres wynagrodzenia chorobowego od pracodawcy obowiązuje począwszy od roku kalendarzowego następującego po roku, w którym pracownik ukończył 50 lat."
                />
              </label>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
              <InfoTooltip
                label="Indywidualna podstawa wymiaru zasiłku (opcjonalnie, zł po -13,71%)"
                tooltip="Jeśli znasz swoją dokładną indywidualną podstawę wymiaru zasiłku (np. z formularza Z-3/Z-3a lub Kreatora podstawy wg art. 48a dla JDG), wpisz ją tutaj."
              />
            </label>
            <input
              type="number"
              min={0}
              step="any"
              placeholder="Pozostaw puste, aby wyliczyć automatycznie z kwoty brutto"
              value={customBase}
              onChange={(e) => setCustomBase(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm"
            />
          </div>

          {(insuranceTitle === "uop" || insuranceTitle === "zlecenie" || insuranceTitle === "jdg") && (
            <div className="grid gap-4 sm:grid-cols-2">
              {(insuranceTitle === "uop" || insuranceTitle === "zlecenie") && (
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
              )}

              {insuranceTitle === "jdg" && (
                <div className="sm:col-span-2">
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                    <InfoTooltip
                      label="Zaległość składkowa ZUS (zł)"
                      tooltip="Art. 2a ustawy zasiłkowej: zadłużenie przekraczające 1% minimalnego wynagrodzenia (48,06 zł w 2026 r.) wstrzymuje wypłatę zasiłku na JDG do czasu spłaty (przedawnienie po 6 miesiącach)."
                    />
                  </label>
                  <input
                    type="number"
                    min={0}
                    step="any"
                    value={contributionDebt}
                    onChange={(e) => setContributionDebt(Number(e.target.value))}
                    className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm"
                  />
                </div>
              )}
            </div>
          )}

          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
            <input
              type="checkbox"
              checked={hasCodeB}
              onChange={(e) => setHasCodeB(e.target.checked)}
              className="h-4 w-4 shrink-0 accent-[#007834]"
            />
            Zaświadczenie lekarskie e-ZLA zawiera kod literowy „B” (ciąża = 100%)
          </label>

          <div className="rounded-lg border border-slate-200 dark:border-emerald-950 bg-slate-50 dark:bg-[#16241d] p-3">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-800 dark:text-slate-200">
              <input
                type="checkbox"
                checked={specialTermination}
                onChange={(e) => setSpecialTermination(e.target.checked)}
                className="h-4 w-4 shrink-0 accent-[#007834]"
              />
              <InfoTooltip
                label="Szczególna sytuacja: utrata zatrudnienia / ustanie ubezpieczenia w ciąży"
                tooltip="Art. 30 ust. 3 (upadłość, likwidacja lub śmierć pracodawcy — zasiłek w wys. macierzyńskiego do porodu), art. 30 ust. 1 pkt 2 (wyrok sądu — zasiłek macierzyński po porodzie) oraz art. 7 i 46 (chorobowy po ustaniu ubezpieczenia)."
              />
            </label>
            {specialTermination && (
              <select
                value={terminationReason}
                onChange={(e) => setTerminationReason(e.target.value)}
                className="mt-2 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-[#111c17] px-3 py-2 text-xs"
              >
                <option value="bankruptcy_liquidation">
                  Upadłość lub likwidacja pracodawcy (art. 30 ust. 3 — do dnia porodu)
                </option>
                <option value="employer_death">
                  Śmierć pracodawcy (art. 30 ust. 3 — do dnia porodu)
                </option>
                <option value="unlawful_termination_court_ruling">
                  Rozwiązanie umowy z naruszeniem prawa — wyrok sądu (art. 30 ust. 1 pkt 2 — macierzyński po porodzie)
                </option>
                <option value="post_employment_art7">
                  Zasiłek chorobowy po ustaniu ubezpieczenia w ciąży — do 14 dni od ustania (art. 7 i 46)
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
                {(() => {
                  const badge = getBadgeStyleAndLabel(result);
                  return (
                    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${badge.cls}`}>
                      {badge.label}
                    </span>
                  );
                })()}
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
                    {result.eligible_post_birth_maternity_art30 && !result.eligible_maternity_equivalent
                      ? `Prognoza PO porodzie (${result.benefit_rate_percent}%)`
                      : !result.waiting_period_met && result.benefit_base_monthly > 0
                      ? `Prognoza po wyczekiwaniu (${result.benefit_rate_percent}%)`
                      : result.payout_suspended_due_to_debt
                      ? `Po spłacie zadłużenia (${result.benefit_rate_percent}%)`
                      : `Zasiłek miesięczny (${result.benefit_rate_percent}%)`}
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
                    Okres świadczenia / finansowanie
                  </dt>
                  <dd className="font-semibold text-slate-900 dark:text-slate-100">
                    {result.benefit_duration_label
                      ? result.benefit_duration_label
                      : result.max_benefit_days === 0
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
              zasiłku chorobowego, świadczenia rehabilitacyjnego oraz świadczeń po ustaniu
              zatrudnienia w ciąży.
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
            {result && result.eligible_sickness_benefit && result.rehabilitation_max_days > 0 && (
              <div className="mt-3 grid gap-2 rounded-lg bg-slate-50 dark:bg-[#16241d] p-3 sm:grid-cols-2">
                <div>
                  <span className="text-slate-500 dark:text-slate-400">
                    Szacowane świadczenie rehabilitacyjne (100% mies., przed waloryzacją):
                  </span>
                  <p className="text-sm font-bold text-[#005a27] dark:text-emerald-300">
                    {result.rehabilitation_monthly_gross.toFixed(2)} zł
                  </p>
                </div>
                <div>
                  <span className="text-slate-500 dark:text-slate-400">
                    Stawka dzienna (maks. {result.rehabilitation_max_days} dni):
                  </span>
                  <p className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    {result.rehabilitation_daily_gross.toFixed(2)} zł / dzień
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
