"use client";

import { useEffect, useRef, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { InfoTooltip } from "@/components/InfoTooltip";
import { PregnancyCalculatorPanel } from "@/components/PregnancyCalculatorPanel";
import { useUser } from "@/components/UserContext";
import { api } from "@/lib/api";
import type {
  BenefitScenario,
  FosterFamilyType,
  IndividualBaseCalculationResponse,
  InsuranceTitle,
  IntegratedCalculatorResponse,
  LegalParameters,
  PaymentVariant,
  SampleCase,
} from "@/lib/types";

const MATERNITY_WEEKS_BY_CHILDREN: Record<number, number> = {
  1: 20,
  2: 31,
  3: 33,
  4: 35,
  5: 37,
  6: 37,
};

function parsePolishSalaryList(input: string): number[] {
  // Obsługuje formaty: "7 500,50 zł; 8 000,00 zł", "7.500,50; 8.000,00", "7 500,50, 8 000,00", "8 000, 8 500" oraz nowe linie
  const normalized = input
    .replace(/\u00A0/g, " ")
    .replace(/(?:zł|zl|pln)\.?/gi, "")
    .replace(/(\d)\.(\d{3})(?=\D|$)/g, "$1$2")
    .replace(/(\d),(\d{1,2})(?=\s*(?:[,;\n]|$))/g, "$1.$2");
  return normalized
    .split(/[;\n,]+/)
    .map((chunk) => chunk.replace(/\s+/g, "").trim())
    .filter((chunk) => chunk.length > 0)
    .map((s) => Number(s))
    .filter((n) => !Number.isNaN(n) && n > 0);
}

function formatPln(amount: number): string {
  return `${amount.toLocaleString("pl-PL", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}\u00A0zł`;
}

export default function IntegratedCalculatorPage() {
  const { user } = useUser();

  const [calculatorMode, setCalculatorMode] = useState<"maternity" | "pregnancy">("maternity");
  const [pdfPrefillBanner, setPdfPrefillBanner] = useState<{
    sourceLabel: string;
    missingFields: string[];
  } | null>(null);
  const [legalParams, setLegalParams] = useState<LegalParameters | null>(null);
  const prefillAppliedRef = useRef(false);
  const prevUserIdRef = useRef<string | null>(user?.id ?? null);

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
  const [fteFraction, setFteFraction] = useState(1.0);
  const [singleParent, setSingleParent] = useState(false);
  const [secondParentInsuredClaim, setSecondParentInsuredClaim] = useState(false);
  const [secondParentInsuranceTitle, setSecondParentInsuranceTitle] =
    useState<InsuranceTitle>("uop");
  const [secondParentHasSickness, setSecondParentHasSickness] = useState(true);
  const [secondParentFteFraction, setSecondParentFteFraction] = useState(1.0);
  const [secondParentEmployerCount, setSecondParentEmployerCount] = useState(25);
  const [secondParentDebt, setSecondParentDebt] = useState(0);

  const [childrenCount, setChildrenCount] = useState(1);
  const [childAgeYears, setChildAgeYears] = useState(3);
  const [fosterFamilyType, setFosterFamilyType] = useState<FosterFamilyType>("non_professional");
  const [fosterDeferred, setFosterDeferred] = useState(false);
  const [adoptionShort9Weeks, setAdoptionShort9Weeks] = useState(false);
  const [prevFosterMatWeeks, setPrevFosterMatWeeks] = useState(0);
  const [prevFosterParWeeks, setPrevFosterParWeeks] = useState(0);
  const [hasZaZyciem, setHasZaZyciem] = useState(false);
  const [stillbirthOrEarlyDeath, setStillbirthOrEarlyDeath] = useState(false);
  const [motherEarlyTransfer8Weeks, setMotherEarlyTransfer8Weeks] = useState(false);
  const [preBirthWeeks, setPreBirthWeeks] = useState(0);

  const [premature, setPremature] = useState(false);
  const [gestationWeek, setGestationWeek] = useState(32);
  const [birthWeight, setBirthWeight] = useState(1400);
  const [hospWeeks, setHospWeeks] = useState(4);
  const [fullTermHospConditionMet, setFullTermHospConditionMet] = useState(true);

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
  const [creatorJdgPreferential, setCreatorJdgPreferential] = useState(false);
  const [baseCalcResult, setBaseCalcResult] = useState<IndividualBaseCalculationResponse | null>(
    null
  );

  const [paymentVariant, setPaymentVariant] = useState<PaymentVariant>("81_5");
  const [motherMaternityWeeks, setMotherMaternityWeeks] = useState(20);
  const [motherParentalWeeks, setMotherParentalWeeks] = useState<string>("");
  const [fatherParentalWeeks, setFatherParentalWeeks] = useState(9);
  const [fatherPaternity, setFatherPaternity] = useState(true);

  const [combineWork, setCombineWork] = useState(false);
  const [workFte, setWorkFte] = useState(0.5);
  const [workWeeks, setWorkWeeks] = useState(10);
  const [workDuringExtendedPart, setWorkDuringExtendedPart] = useState(true);

  const [fatherCombineWork, setFatherCombineWork] = useState(false);
  const [fatherWorkFte, setFatherWorkFte] = useState(0.5);
  const [fatherWorkWeeks, setFatherWorkWeeks] = useState(6);
  const [fatherWorkDuringExtendedPart, setFatherWorkDuringExtendedPart] = useState(true);

  const [employerCount, setEmployerCount] = useState(user?.employer_insured_count ?? 30);
  const [contributionDebt, setContributionDebt] = useState(user?.debt_amount_pln ?? 0);

  const [result, setResult] = useState<IntegratedCalculatorResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const parsedCreatorSalaries = parsePolishSalaryList(creatorSalariesText);

  const minWage = legalParams?.minimum_wage_gross ?? 4806;
  const debtThresholdStr = (minWage * (legalParams?.debt_threshold_min_wage_fraction ?? 0.01))
    .toFixed(2)
    .replace(".", ",");
  const minMonthlyFloorStr = (legalParams?.parental_benefit_minimum_monthly ?? 1000)
    .toFixed(2)
    .replace(".", ",");
  const jdgPrefMin = legalParams?.jdg_preferential_min_base_gross ?? 1441.8;
  const jdgStdMin = legalParams?.jdg_standard_min_base_gross ?? 5652;
  const deadlineDays = legalParams?.combined_application_deadline_days ?? 21;
  const combinedRate = legalParams?.combined_21_days_rate ?? 0.815;
  const matStdRate = legalParams?.maternity_rate_standard ?? 1.0;
  const combinedRateStr = `${(combinedRate * 100).toFixed(1).replace(".", ",")}%`;
  const eqDiffPpStr = `+${((matStdRate - combinedRate) * 100).toFixed(1).replace(".", ",")} p.p.`;
  const paramsYear = legalParams?.year ?? 2026;

  const getMaternityWeeksForChildren = (count: number) => {
    const key = Math.min(Math.max(1, count), 5);
    return (
      legalParams?.maternity_weeks_by_children?.[String(key)] ??
      MATERNITY_WEEKS_BY_CHILDREN[key] ??
      20
    );
  };
  const minMotherWeeks = legalParams?.maternity_min_mother_weeks ?? 14;
  const adoptionMinMatWeeks = legalParams?.adoption_foster_min_maternity_weeks ?? 9;
  const maxMatWeeks = Math.max(
    37,
    ...Object.values(legalParams?.maternity_weeks_by_children ?? MATERNITY_WEEKS_BY_CHILDREN)
  );
  const maxParentalWeeks = Math.max(
    legalParams?.parental_weeks_single ?? 41,
    legalParams?.parental_weeks_multiple ?? 43,
    legalParams?.parental_weeks_za_zyciem_single ?? 65,
    legalParams?.parental_weeks_za_zyciem_multiple ?? 67
  );
  const maxSingleParentParental = Math.max(
    1,
    maxParentalWeeks - (legalParams?.parental_non_transferable_weeks ?? 9)
  );

  useEffect(() => {
    api.getSampleCases().then(setSampleCases).catch(() => setSampleCases([]));
    api
      .getParameters()
      .then((p) => {
        setLegalParams(p);
        setCreatorJdgDeclared(p.voluntary_sickness_max_monthly_gross);
        setCreatorJdgMin(p.jdg_standard_min_base_gross);
      })
      .catch(() => setLegalParams(null));
  }, []);

  // Automatyczne przełączenie na tryb ciąży/chorobowego z parametru URL lub prefillu PDF
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (
      params.get("mode") === "pregnancy" ||
      sessionStorage.getItem("zppr-prefill-pregnancy")
    ) {
      setCalculatorMode("pregnancy");
    }
  }, []);

  // Automatyczne wczytanie danych przekazanych ze strony /sprawy-pdf
  useEffect(() => {
    const raw = sessionStorage.getItem("zppr-prefill-calculator");
    if (!raw) return;
    sessionStorage.removeItem("zppr-prefill-calculator");
    prefillAppliedRef.current = true;
    try {
      const data = JSON.parse(raw) as Record<string, unknown>;
      const isFromPdf = Boolean(data.fromPdf);
      const missing: string[] = [];

      const rawScenario = data.scenario as BenefitScenario | null | undefined;
      if (isFromPdf && !rawScenario) missing.push("Scenariusz (poród / adopcja / rodzina zastępcza)");
      const sc: BenefitScenario = rawScenario || "birth";

      const rawTitle = data.insurance_title as InsuranceTitle | null | undefined;
      if (isFromPdf && !rawTitle) missing.push("Tytuł ubezpieczenia");
      const insTitle: InsuranceTitle = rawTitle || "uop";

      if (
        isFromPdf &&
        (data.has_sickness_insurance_on_birth_date === null ||
          data.has_sickness_insurance_on_birth_date === undefined)
      ) {
        missing.push("Status ubezpieczenia chorobowego");
      }
      const insured = Boolean(data.has_sickness_insurance_on_birth_date ?? true);

      if (isFromPdf && (data.children_count === null || data.children_count === undefined)) {
        missing.push("Liczba dzieci");
      }
      const kids = Math.min(15, Math.max(1, Number(data.children_count ?? 1)));

      const custom1 = data.custom_benefit_base ? Number(data.custom_benefit_base) : null;
      const custom2 = data.second_parent_custom_base ? Number(data.second_parent_custom_base) : null;
      const secondGross = data.second_parent_gross_salary
        ? Number(data.second_parent_gross_salary)
        : null;

      const hasGross =
        data.gross_monthly_salary !== null &&
        data.gross_monthly_salary !== undefined &&
        data.gross_monthly_salary !== "";
      if (isFromPdf && !hasGross && !custom1 && insTitle !== "none") {
        missing.push("Wynagrodzenie brutto / podstawa wymiaru (zł)");
      }
      const gross = hasGross ? Number(data.gross_monthly_salary) : isFromPdf ? 0 : 7000;

      if (isFromPdf && !data.payment_variant) {
        missing.push("Wariant wypłaty (81,5% lub 100%/70%)");
      }
      const variant = (data.payment_variant as PaymentVariant) || "81_5";

      const hasEmpCount =
        data.employer_insured_count !== null &&
        data.employer_insured_count !== undefined &&
        data.employer_insured_count !== "";
      if (isFromPdf && !hasEmpCount && (insTitle === "uop" || insTitle === "zlecenie")) {
        missing.push("Liczba ubezpieczonych u płatnika");
      }
      const empCount = hasEmpCount ? Number(data.employer_insured_count) : isFromPdf ? 0 : 25;

      const defaultMat = MATERNITY_WEEKS_BY_CHILDREN[Math.min(kids, 5)] || 20;
      const matWeeks =
        data.mother_maternity_weeks !== undefined && data.mother_maternity_weeks !== null
          ? Number(data.mother_maternity_weeks)
          : defaultMat;
      const fatherPar = Number(data.father_takes_parental_weeks ?? 0);
      const fatherPat = Boolean(data.father_takes_paternity_leave ?? false);

      setScenario(sc);
      setInsuranceTitle(insTitle);
      setInsuredOnDate(insured);
      setFteFraction(1.0);
      setCreatorFte(1.0);
      setSingleParent(false);
      setSecondParentInsuredClaim(false);
      setSecondParentInsuranceTitle("uop");
      setSecondParentHasSickness(true);
      setSecondParentFteFraction(1.0);
      setSecondParentEmployerCount(25);
      setSecondParentDebt(0);
      setChildrenCount(kids);
      if (data.child_age_years !== undefined && data.child_age_years !== null) {
        setChildAgeYears(Number(data.child_age_years));
      }
      setFosterFamilyType((data.foster_family_type as FosterFamilyType) || "non_professional");
      setFosterDeferred(Boolean(data.foster_deferred_school));
      setHasZaZyciem(Boolean(data.has_za_zyciem_certificate));
      setStillbirthOrEarlyDeath(Boolean(data.stillbirth_or_early_death));
      setPremature(Boolean(data.premature_or_hospitalized));
      if (data.gestation_week) setGestationWeek(Number(data.gestation_week));
      if (data.birth_weight_grams) setBirthWeight(Number(data.birth_weight_grams));
      setCombineWork(Boolean(data.combine_parental_with_work));
      setGrossSalary(gross);
      if (custom1) {
        setBaseMode("custom");
        setCustomBase1(String(custom1));
      } else {
        setBaseMode("standard");
        setCustomBase1("");
      }
      setSecondParentGross(secondGross ?? gross);
      setCustomBase2(custom2 ? String(custom2) : "");
      setPaymentVariant(variant);
      setEmployerCount(empCount);
      setContributionDebt(Number(data.contribution_debt_pln ?? 0));
      setMotherMaternityWeeks(matWeeks);
      setMotherParentalWeeks("");
      setFatherParentalWeeks(fatherPar);
      setFatherPaternity(fatherPat);
      setFullTermHospConditionMet(true);
      setFatherCombineWork(false);

      if (isFromPdf) {
        setPdfPrefillBanner({
          sourceLabel: String(data.sourceLabel || "Wczytany dokument PDF"),
          missingFields: missing,
        });
      }

      // Uruchom automatyczne wyliczenie tylko gdy zestaw danych jest kompletny (przykłady demo lub pełny PDF)
      if (!isFromPdf || missing.length === 0) {
        setLoading(true);
        api
          .calculateIntegrated({
            scenario: sc,
            insurance_title: insTitle,
            has_sickness_insurance_on_birth_date: insured,
            children_count: kids,
            child_age_years: sc === "birth" ? null : Number(data.child_age_years ?? 3),
            foster_family_type: (data.foster_family_type as FosterFamilyType) || "non_professional",
            foster_deferred_school: Boolean(data.foster_deferred_school),
            has_za_zyciem_certificate: Boolean(data.has_za_zyciem_certificate),
            stillbirth_or_early_death: Boolean(data.stillbirth_or_early_death),
            premature_or_hospitalized: Boolean(data.premature_or_hospitalized),
            gross_monthly_salary: gross,
            custom_benefit_base: custom1,
            second_parent_gross_salary: secondGross,
            second_parent_custom_base: custom2,
            payment_variant: variant,
            mother_maternity_weeks: matWeeks,
            father_takes_parental_weeks: fatherPar,
            father_takes_paternity_leave: fatherPat,
            employer_insured_count: empCount,
            contribution_debt_pln: Number(data.contribution_debt_pln ?? 0),
          })
          .then(setResult)
          .catch((err) => setError(err instanceof Error ? err.message : "Błąd wyliczeń API"))
          .finally(() => setLoading(false));
      }
    } catch {
      // ignore invalid prefill JSON
    }
  }, []);

  useEffect(() => {
    const nextId = user?.id ?? null;
    // Nie nadpisuj danych wczytanych z /sprawy-pdf podczas początkowego montowania dla zalogowanej persony
    if (prefillAppliedRef.current && nextId === prevUserIdRef.current) {
      return;
    }
    prevUserIdRef.current = nextId;
    if (user) {
      prefillAppliedRef.current = false;
      setInsuranceTitle(user.insurance_title);
      setInsuredOnDate(user.has_sickness_insurance);
      setGrossSalary(user.declared_gross_salary);
      setEmployerCount(user.employer_insured_count);
      setContributionDebt(user.debt_amount_pln || 0);
    }
  }, [user]);

  const handleScenarioChange = (nextScenario: BenefitScenario) => {
    setScenario(nextScenario);
    if (nextScenario === "birth") {
      setAdoptionShort9Weeks(false);
      setPrevFosterMatWeeks(0);
      setPrevFosterParWeeks(0);
      setFosterDeferred(false);
      setFosterFamilyType("non_professional");
      setMotherMaternityWeeks(getMaternityWeeksForChildren(childrenCount));
    } else {
      setStillbirthOrEarlyDeath(false);
      setMotherEarlyTransfer8Weeks(false);
      setPreBirthWeeks(0);
      if (nextScenario === "foster") {
        setFatherPaternity(false);
      }
      setMotherMaternityWeeks(
        adoptionShort9Weeks ? adoptionMinMatWeeks : getMaternityWeeksForChildren(childrenCount)
      );
    }
  };

  const handleChildrenCountChange = (newCount: number) => {
    const clamped = Math.max(1, Math.min(15, newCount));
    setChildrenCount(clamped);
    if (scenario !== "birth" && adoptionShort9Weeks) {
      setMotherMaternityWeeks(adoptionMinMatWeeks);
    } else {
      setMotherMaternityWeeks(getMaternityWeeksForChildren(clamped));
    }
  };

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
    setFteFraction(1.0);
    setSingleParent(false);
    setSecondParentInsuredClaim(false);
    setSecondParentInsuranceTitle("uop");
    setSecondParentHasSickness(true);
    setSecondParentFteFraction(1.0);
    setSecondParentEmployerCount(25);
    setSecondParentDebt(0);
    setContributionDebt(0);
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
    setSecondParentGross(found.second_parent_gross_salary ?? found.gross_monthly_salary);
    if (found.second_parent_custom_base) {
      setCustomBase2(String(found.second_parent_custom_base));
    } else {
      setCustomBase2("");
    }
    setPaymentVariant(found.payment_variant);
    setEmployerCount(found.employer_insured_count);
    // Reset wszystkich opcji pomocniczych, aby stan formularza odpowiadał wynikowi przykładu
    setPremature(false);
    setHospWeeks(0);
    setFullTermHospConditionMet(true);
    setCombineWork(false);
    setWorkFte(0.5);
    setWorkWeeks(0);
    setFatherCombineWork(false);
    setFatherWorkFte(0.5);
    setFatherWorkWeeks(0);
    setStillbirthOrEarlyDeath(false);
    setMotherEarlyTransfer8Weeks(false);
    setPreBirthWeeks(0);
    setAdoptionShort9Weeks(false);
    setPrevFosterMatWeeks(0);
    setPrevFosterParWeeks(0);
    setMotherParentalWeeks("");
    if ((found.scenario || "birth") === "birth") {
      setChildAgeYears(3);
    }

    const defaultMat = getMaternityWeeksForChildren(found.children_count);
    if (found.mother_maternity_weeks !== undefined && found.mother_maternity_weeks !== null) {
      setMotherMaternityWeeks(found.mother_maternity_weeks);
    } else {
      setMotherMaternityWeeks(defaultMat);
    }
    setFatherParentalWeeks(found.father_takes_parental_weeks ?? 0);
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
        second_parent_gross_salary: found.second_parent_gross_salary ?? null,
        second_parent_custom_base: found.second_parent_custom_base ?? null,
        payment_variant: found.payment_variant,
        mother_maternity_weeks: found.mother_maternity_weeks ?? defaultMat,
        father_takes_parental_weeks: found.father_takes_parental_weeks ?? 0,
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
      const parsedSalaries = parsePolishSalaryList(creatorSalariesText);

      if (creatorSubMode === "uop_12m" && parsedSalaries.length === 0) {
        setError(
          "Wpisz co najmniej jedno dodatnie miesięczne wynagrodzenie brutto (oddzielaj średnikiem lub przecinkiem, np. 7 500,50; 8 000,00)."
        );
        return;
      }

      const res = await api.calculateIndividualBase({
        insurance_title: insuranceTitle,
        mode: creatorSubMode,
        monthly_gross_salaries: parsedSalaries,
        quarterly_bonuses_total: Number(creatorQuarterlyBonus),
        annual_bonus_total: Number(creatorAnnualBonus),
        uncompleted_months_excluded: Number(creatorExcludedMonths),
        fte_fraction: Number(creatorFte),
        previous_benefit_base: Number(creatorPrevBase),
        jdg_insured_months: Number(creatorJdgMonths),
        jdg_declared_monthly_gross: Number(creatorJdgDeclared),
        jdg_min_monthly_gross: Number(creatorJdgMin),
        jdg_preferential_zus: creatorJdgPreferential,
      });
      setBaseCalcResult(res);
      setCustomBase1(String(res.computed_base_monthly));
      if (insuranceTitle === "uop" && creatorSubMode === "uop_12m") {
        setFteFraction(Math.max(0.1, Math.min(1.0, Number(creatorFte) || 1.0)));
      }
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
        !singleParent &&
        (baseMode === "custom" || baseMode === "creator") &&
        customBase2.trim() !== "" &&
        Number(customBase2) > 0
          ? Number(customBase2)
          : null;

      const parsedMotherPar =
        motherParentalWeeks.trim() === "" ? null : Math.max(0, Number(motherParentalWeeks));

      const isParent1Uninsured = !insuredOnDate || insuranceTitle === "none";
      const useSecondParentClaim = !singleParent && isParent1Uninsured && secondParentInsuredClaim;
      const canFatherCombine =
        !singleParent &&
        secondParentInsuranceTitle === "uop" &&
        secondParentHasSickness &&
        fatherCombineWork &&
        (Number(fatherParentalWeeks) > 0 || useSecondParentClaim);

      const res = await api.calculateIntegrated({
        scenario,
        insurance_title: insuranceTitle,
        has_sickness_insurance_on_birth_date: insuranceTitle === "none" ? false : insuredOnDate,
        single_parent_or_no_second_parent: singleParent,
        second_parent_insured_claim: useSecondParentClaim,
        second_parent_insurance_title: singleParent ? "none" : secondParentInsuranceTitle,
        second_parent_has_sickness_insurance: singleParent
          ? false
          : secondParentInsuranceTitle === "none"
            ? false
            : secondParentHasSickness,
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
        stillbirth_or_early_death: scenario === "birth" ? stillbirthOrEarlyDeath : false,
        mother_early_transfer_8_weeks: scenario === "birth" ? motherEarlyTransfer8Weeks : false,
        pre_birth_maternity_weeks: scenario === "birth" ? Number(preBirthWeeks) : 0,
        premature_or_hospitalized: premature,
        gestation_week: premature ? Number(gestationWeek) : null,
        birth_weight_grams: premature ? Number(birthWeight) : null,
        hospitalization_weeks: premature ? Number(hospWeeks) : 0,
        full_term_hospitalization_condition_met: premature ? fullTermHospConditionMet : true,
        gross_monthly_salary: Number(grossSalary),
        fte_fraction: insuranceTitle === "uop" ? Number(fteFraction) : 1.0,
        custom_benefit_base: useCustom1,
        second_parent_gross_salary: singleParent ? null : Number(secondParentGross),
        second_parent_fte_fraction:
          !singleParent && secondParentInsuranceTitle === "uop"
            ? Number(secondParentFteFraction)
            : 1.0,
        second_parent_custom_base: useCustom2,
        payment_variant: paymentVariant,
        mother_maternity_weeks: Number(motherMaternityWeeks),
        mother_takes_parental_weeks: parsedMotherPar,
        father_takes_parental_weeks: singleParent ? 0 : Number(fatherParentalWeeks),
        father_takes_paternity_leave:
          singleParent || scenario === "foster" ? false : fatherPaternity,
        combine_parental_with_work: combineWork,
        work_fte_fraction: combineWork ? Number(workFte) : 0,
        combined_work_weeks: combineWork ? Number(workWeeks) : 0,
        work_during_extended_part: combineWork ? workDuringExtendedPart : true,
        father_combine_parental_with_work: canFatherCombine,
        father_work_fte_fraction: canFatherCombine ? Number(fatherWorkFte) : 0,
        father_combined_work_weeks: canFatherCombine ? Number(fatherWorkWeeks) : 0,
        father_work_during_extended_part: canFatherCombine ? fatherWorkDuringExtendedPart : true,
        employer_insured_count: Number(employerCount),
        second_parent_employer_insured_count: useSecondParentClaim
          ? Number(secondParentEmployerCount)
          : null,
        contribution_debt_pln: insuranceTitle === "jdg" ? Number(contributionDebt) : 0,
        second_parent_contribution_debt_pln:
          !singleParent && secondParentInsuranceTitle === "jdg" ? Number(secondParentDebt) : 0,
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
        badge="Zintegrowany Kalkulator"
        title="Zintegrowany Kalkulator Świadczeń w Ciąży i po Narodzinach Dziecka"
        description="Jedno narzędzie łączące wszystkie kalkulatory: okres ciąży (zasiłek chorobowy kod B, świadczenie rehabilitacyjne, zasiłek w wys. macierzyńskiego), poród, podział opieki między oboje rodziców, łączenie urlopu rodzicielskiego z pracą, adopcję, rodzinę zastępczą oraz indywidualną podstawę wymiaru zasiłku."
      />

      {/* Przełącznik modułów zintegrowanego kalkulatora (pkt a–f, j) */}
      <div
        role="tablist"
        aria-label="Moduły zintegrowanego kalkulatora"
        className="mb-6 flex flex-wrap gap-2.5"
      >
        <button
          type="button"
          role="tab"
          aria-selected={calculatorMode === "maternity"}
          onClick={() => {
            setCalculatorMode("maternity");
            const url = new URL(window.location.href);
            url.searchParams.delete("mode");
            window.history.replaceState({}, "", url.toString());
          }}
          className={`rounded-xl border px-5 py-3 text-sm font-bold transition ${
            calculatorMode === "maternity"
              ? "border-[#007834] bg-[#007834] text-white shadow-xs"
              : "border-slate-200 bg-white text-slate-700 hover:border-[#007834]/50 dark:border-emerald-950 dark:bg-[#111c17] dark:text-slate-300"
          }`}
        >
          Macierzyński, rodzicielski, ojcowski, adopcja i rodzina zastępcza
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={calculatorMode === "pregnancy"}
          onClick={() => {
            setCalculatorMode("pregnancy");
            const url = new URL(window.location.href);
            url.searchParams.set("mode", "pregnancy");
            window.history.replaceState({}, "", url.toString());
          }}
          className={`rounded-xl border px-5 py-3 text-sm font-bold transition ${
            calculatorMode === "pregnancy"
              ? "border-[#007834] bg-[#007834] text-white shadow-xs"
              : "border-slate-200 bg-white text-slate-700 hover:border-[#007834]/50 dark:border-emerald-950 dark:bg-[#111c17] dark:text-slate-300"
          }`}
        >
          Świadczenia w czasie ciąży (chorobowy, rehabilitacyjny, w wys. macierzyńskiego)
        </button>
      </div>

      {calculatorMode === "pregnancy" ? (
        <PregnancyCalculatorPanel />
      ) : (
        <>
          {pdfPrefillBanner && (
            <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950 dark:border-amber-800/60 dark:bg-amber-950/40 dark:text-amber-200">
              <p className="font-bold">Wczytano dane z dokumentu: {pdfPrefillBanner.sourceLabel}</p>
              {pdfPrefillBanner.missingFields.length > 0 ? (
                <p className="mt-1 leading-relaxed">
                  Następujących pól nie udało się odczytać z dokumentu — sprawdź i uzupełnij je
                  poniżej przed kliknięciem „Oblicz”:{" "}
                  <strong>{pdfPrefillBanner.missingFields.join(", ")}</strong>.
                </p>
              ) : (
                <p className="mt-1 leading-relaxed">
                  Wszystkie wymagane pola zostały odczytane i wstępnie przeliczone.
                </p>
              )}
            </div>
          )}

      {/* Pasek wyboru konkretnej sprawy z zestawów ZUS (pkt f) */}
      <div className="mb-6 rounded-xl border border-[#007834]/30 bg-[#e6f4ec]/60 p-4 shadow-xs dark:border-emerald-800/60 dark:bg-[#007834]/15">
        <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
          <div>
            <p className="text-sm font-bold uppercase tracking-wide text-[#005a27] dark:text-emerald-300">
              Symulacja konkretnej sprawy z zestawów ZUS
            </p>
            <p className="mt-0.5 text-sm text-slate-700 dark:text-slate-300">
              Wybierz gotową sprawę z zestawu testowego ZUS, aby automatycznie wypełnić indywidualną
              podstawę wymiaru zasiłku oraz parametry sprawy:
            </p>
          </div>
          <select
            value={selectedCaseId}
            onChange={(e) => handleLoadSampleCase(e.target.value)}
            className="rounded-lg border border-[#007834] bg-white px-3 py-2 text-sm font-semibold text-slate-900 dark:border-emerald-700 dark:bg-[#111c17] dark:text-slate-100 md:w-96"
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
          <div className="mt-3 rounded-lg border border-[#007834]/20 bg-white p-3.5 text-sm text-slate-700 dark:border-emerald-900 dark:bg-[#111c17] dark:text-slate-300">
            <p className="font-bold text-slate-900 dark:text-slate-100">{activeSampleCase.title}</p>
            <p className="mt-1 leading-relaxed">{activeSampleCase.description}</p>
            {activeSampleCase.benefit_base_details && (
              <p className="mt-1.5 font-medium text-slate-800 dark:text-slate-200">
                <strong>Ustalenie indywidualnej podstawy wymiaru:</strong>{" "}
                {activeSampleCase.benefit_base_details}
              </p>
            )}
            <p className="mt-1.5 font-semibold text-[#005a27] dark:text-emerald-300">
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
            <label className="block text-sm font-bold uppercase tracking-wide text-slate-700 dark:text-slate-300">
              <InfoTooltip
                label="1. Scenariusz rodzicielstwa"
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
                  onClick={() => handleScenarioChange(opt.id)}
                  className={`rounded-lg border px-2.5 py-2.5 text-sm font-semibold transition ${
                    scenario === opt.id
                      ? "border-[#007834] bg-[#e6f4ec] text-[#005a27] dark:bg-[#007834]/20 dark:text-emerald-300"
                      : "border-slate-200 text-slate-600 hover:bg-slate-50 dark:border-emerald-950 dark:text-slate-400 dark:hover:bg-[#16241d]"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Szczegóły dla Adopcji i Rodziny zastępczej (pkt e oraz j) */}
          {scenario !== "birth" && (
            <div className="space-y-3 rounded-lg border border-[#007834]/30 bg-slate-50 p-4 dark:border-emerald-900 dark:bg-[#16241d]">
              <p className="text-sm font-bold text-[#005a27] dark:text-emerald-300">
                {scenario === "adoption"
                  ? "Parametry przysposobienia (adopcji) — art. 183 Kodeksu pracy"
                  : "Parametry rodziny zastępczej — art. 183 Kodeksu pracy"}
              </p>

              {scenario === "foster" && (
                <div>
                  <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300">
                    <InfoTooltip
                      label="Forma rodziny zastępczej (art. 29 ust. 1 pkt 3 ustawy zasiłkowej)"
                      tooltip="Zgodnie z art. 183 § 1 Kodeksu pracy i art. 29 ust. 1 pkt 3 ustawy zasiłkowej prawo do urlopu i zasiłku macierzyńskiego przysługuje rodzinom zastępczym niezawodowym (z wyjątkiem rodzin zastępczych zawodowych)."
                    />
                  </label>
                  <select
                    value={fosterFamilyType}
                    onChange={(e) => setFosterFamilyType(e.target.value as FosterFamilyType)}
                    className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-[#111c17]"
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
                  <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300">
                    <InfoTooltip
                      label="Wiek dziecka (lata, np. 6.9)"
                      tooltip="Urlop na warunkach macierzyńskiego przysługuje do 7. roku życia (rodzina zastępcza), 10. roku życia (przy odroczeniu szkoły) lub 14. roku życia (adopcja). Gdy do granicy wieku zostało mniej niż 9 tygodni, przysługuje gwarantowane 9 tyg. + 38 tyg. rodzicielskiego (art. 183 § 3 KP)."
                    />
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={18}
                    step="any"
                    value={childAgeYears}
                    onChange={(e) => setChildAgeYears(Number(e.target.value))}
                    className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-[#111c17]"
                  />
                </div>
                {scenario === "foster" && (
                  <label className="flex items-center gap-2 self-end text-sm text-slate-700 dark:text-slate-300">
                    <input
                      type="checkbox"
                      checked={fosterDeferred}
                      onChange={(e) => setFosterDeferred(e.target.checked)}
                      className="h-4 w-4 shrink-0 accent-[#007834]"
                    />
                    <InfoTooltip
                      label="Odroczenie obowiązku szkolnego (do 10 lat)"
                      tooltip="Jeśli wobec dziecka podjęto decyzję o odroczeniu obowiązku szkolnego, limit wieku dla rodziny zastępczej wzrasta z 7 do 10 lat."
                    />
                  </label>
                )}
              </div>

              <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={adoptionShort9Weeks}
                  onChange={(e) => {
                    const checked = e.target.checked;
                    setAdoptionShort9Weeks(checked);
                    setMotherMaternityWeeks(
                      checked ? adoptionMinMatWeeks : getMaternityWeeksForChildren(childrenCount)
                    );
                  }}
                  className="h-4 w-4 shrink-0 accent-[#007834]"
                />
                <InfoTooltip
                  label="Tryb minimalny z art. 183 § 3 KP (9 tyg. + 38/62 tyg. rodzicielskiego)"
                  tooltip="Minimalny okres zasiłku za urlop na warunkach macierzyńskiego to 9 tygodni (gdy dziecko kończy 7/10/14 lat przed upływem pełnego wymiaru). Urlop rodzicielski wynosi wówczas 38 tygodni (lub 62 tyg. z zaświadczeniem Za życiem)."
                />
              </label>

              {scenario === "adoption" && (
                <div className="grid grid-cols-2 gap-3 border-t border-slate-200 pt-3 dark:border-slate-700">
                  <div>
                    <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
                      <InfoTooltip
                        label="Wcześniej w rodz. zastępczej — macierzyński (tyg.)"
                        tooltip="Art. 183 § 7 KP: jeśli przed adopcją korzystano z urlopu jako rodzina zastępcza na to samo dziecko, wymiar urlopu adopcyjnego pomniejsza się o wykorzystane tygodnie."
                      />
                    </label>
                    <input
                      type="number"
                      min={0}
                      max={maxMatWeeks}
                      value={prevFosterMatWeeks}
                      onChange={(e) => setPrevFosterMatWeeks(Number(e.target.value))}
                      className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm dark:border-slate-700 dark:bg-[#111c17]"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
                      <InfoTooltip
                        label="Wcześniej w rodz. zastępczej — rodzicielski (tyg.)"
                        tooltip="Art. 183 § 8 KP: wymiar urlopu rodzicielskiego po wystąpieniu o adopcję pomniejsza się o urlop rodzicielski wykorzystany wcześniej jako rodzina zastępcza."
                      />
                    </label>
                    <input
                      type="number"
                      min={0}
                      max={maxParentalWeeks}
                      value={prevFosterParWeeks}
                      onChange={(e) => setPrevFosterParWeeks(Number(e.target.value))}
                      className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm dark:border-slate-700 dark:bg-[#111c17]"
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Ubezpieczenie i dzieci */}
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300">
                <InfoTooltip
                  label="Tytuł ubezpieczenia (Rodzic 1)"
                  tooltip="Forma zatrudnienia decyduje o tym, czy ubezpieczenie chorobowe jest obowiązkowe (umowa o pracę), czy dobrowolne (zlecenie, JDG), oraz jakie formularze trzeba złożyć."
                />
              </label>
              <select
                value={insuranceTitle}
                onChange={(e) => {
                  const next = e.target.value as InsuranceTitle;
                  setInsuranceTitle(next);
                  if (next === "none") {
                    setInsuredOnDate(false);
                  } else if (insuranceTitle === "none" && next === "uop") {
                    setInsuredOnDate(true);
                  }
                }}
                className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
              >
                <option value="uop">Umowa o pracę</option>
                <option value="zlecenie">Umowa zlecenie</option>
                <option value="jdg">Działalność (JDG)</option>
                <option value="none">Brak ubezpieczenia</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300">
                <InfoTooltip
                  label="Liczba dzieci (1 poród/przyjęcie)"
                  tooltip="Im więcej dzieci urodzonych przy jednym porodzie (lub przyjętych jednocześnie), tym dłuższy urlop macierzyński (od 20 do 37 tygodni) i rodzicielski (41 lub 43 tygodnie)."
                />
              </label>
              <input
                type="number"
                min={1}
                max={15}
                value={childrenCount}
                onChange={(e) => handleChildrenCountChange(Number(e.target.value))}
                className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
              />
            </div>
          </div>

          {insuranceTitle === "uop" && (
            <div className="flex items-center justify-between gap-2">
              <label className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                <InfoTooltip
                  label="Wymiar etatu Rodzica 1 (art. 45 ustawy zasiłkowej)"
                  tooltip={`Dla pracownika na część etatu minimalna podstawa wymiaru zasiłku (${minWage.toLocaleString("pl-PL")} zł − 13,71%) ulega proporcjonalnemu zmniejszeniu do wymiaru etatu.`}
                />
              </label>
              <input
                type="number"
                min={0.1}
                max={1.0}
                step="any"
                value={fteFraction}
                onChange={(e) => {
                  const v = Number(e.target.value);
                  setFteFraction(v);
                  setCreatorFte(v);
                }}
                className="w-24 rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm dark:border-slate-700"
              />
            </div>
          )}

          <div className="space-y-2.5">
            <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                checked={insuranceTitle === "none" ? false : insuredOnDate}
                disabled={insuranceTitle === "none"}
                onChange={(e) => setInsuredOnDate(e.target.checked)}
                className="h-4 w-4 shrink-0 accent-[#007834] disabled:opacity-50"
              />
              <InfoTooltip
                label="Podleganie ubezpieczeniu chorobowemu na dzień porodu / przyjęcia dziecka"
                tooltip="Warunek konieczny do uzyskania zasiłku macierzyńskiego przez matkę. Przy umowie o pracę jest automatyczny; na zleceniu i JDG musisz być zgłoszona do dobrowolnego ubezpieczenia chorobowego."
              />
            </label>

            <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                checked={singleParent}
                onChange={(e) => {
                  const checked = e.target.checked;
                  setSingleParent(checked);
                  if (checked) {
                    setSecondParentInsuredClaim(false);
                    setFatherParentalWeeks(0);
                    setFatherPaternity(false);
                    setFatherCombineWork(false);
                  }
                }}
                className="h-4 w-4 shrink-0 accent-[#007834]"
              />
              <InfoTooltip
                label="Samotne rodzicielstwo / brak drugiego rodzica"
                tooltip="Gdy dziecko wychowuje jeden rodzic (lub drugi rodzic nie korzysta z uprawnień), 9-tygodniowa nieprzenoszalna część urlopu rodzicielskiego drugiego rodzica pozostaje niewykorzystana (art. 182¹ᵃ § 4–5 KP)."
              />
            </label>
          </div>

          {!singleParent && (!insuredOnDate || insuranceTitle === "none") && (
            <div className="rounded-lg border border-amber-300 bg-amber-50 p-3.5 text-sm dark:border-amber-800/60 dark:bg-amber-950/40">
              <label className="flex items-center gap-2 font-medium text-amber-900 dark:text-amber-200">
                <input
                  type="checkbox"
                  checked={secondParentInsuredClaim}
                  onChange={(e) => setSecondParentInsuredClaim(e.target.checked)}
                  className="h-4 w-4 shrink-0 accent-[#007834]"
                />
                <InfoTooltip
                  label="Matka nieubezpieczona — oblicz uprawnienia ubezpieczonego ojca (art. 31 ust. 3h)"
                  tooltip="Nawet gdy matka na dzień porodu nie była objęta ubezpieczeniem chorobowym, ubezpieczonemu ojcu dziecka przysługuje zasiłek macierzyński za okres urlopu rodzicielskiego (70%) oraz urlop ojcowski (2 tyg., 100%)."
                />
              </label>
            </div>
          )}

          {/* Status drugiego rodzica (Rodzic 2) */}
          {!singleParent && (
            <div className="space-y-3 rounded-lg border border-slate-200 bg-slate-50/70 p-4 dark:border-emerald-950 dark:bg-[#16241d]/70">
              <p className="text-sm font-bold text-slate-800 dark:text-slate-200">
                <InfoTooltip
                  label="Status ubezpieczenia Rodzica 2"
                  tooltip="Tytuł ubezpieczenia drugiego rodzica decyduje o jego prawie do przejęcia urlopu, stawce minimalnej (art. 45), limicie 250% podstawy dobrowolnej, możliwości łączenia urlopu z pracą (tylko UoP) oraz zawieszeniu wypłaty przy zadłużeniu JDG (art. 2a)."
                />
              </p>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400">
                    Tytuł ubezpieczenia Rodzica 2
                  </label>
                  <select
                    value={secondParentInsuranceTitle}
                    onChange={(e) => {
                      const next = e.target.value as InsuranceTitle;
                      setSecondParentInsuranceTitle(next);
                      if (next === "none") {
                        setSecondParentHasSickness(false);
                        setFatherCombineWork(false);
                      } else {
                        if (secondParentInsuranceTitle === "none" && next === "uop") {
                          setSecondParentHasSickness(true);
                        }
                        if (next !== "uop") {
                          setFatherCombineWork(false);
                        }
                      }
                    }}
                    className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-sm dark:border-slate-700 dark:bg-[#111c17]"
                  >
                    <option value="uop">Umowa o pracę</option>
                    <option value="zlecenie">Umowa zlecenie</option>
                    <option value="jdg">Działalność (JDG)</option>
                    <option value="none">Brak ubezpieczenia</option>
                  </select>
                </div>
                {secondParentInsuranceTitle === "uop" && (
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400">
                      Wymiar etatu Rodzica 2
                    </label>
                    <input
                      type="number"
                      min={0.1}
                      max={1.0}
                      step="any"
                      value={secondParentFteFraction}
                      onChange={(e) => setSecondParentFteFraction(Number(e.target.value))}
                      className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-sm dark:border-slate-700 dark:bg-[#111c17]"
                    />
                  </div>
                )}
                {secondParentInsuranceTitle === "jdg" && (
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400">
                      <InfoTooltip
                        label="Zaległość ZUS Rodzica 2 (zł)"
                        tooltip={`Art. 2a ustawy zasiłkowej: zadłużenie JDG powyżej ${debtThresholdStr} zł (1% płacy minimalnej) wstrzymuje wypłatę zasiłku drugiego rodzica.`}
                      />
                    </label>
                    <input
                      type="number"
                      min={0}
                      step="any"
                      value={secondParentDebt}
                      onChange={(e) => setSecondParentDebt(Number(e.target.value))}
                      className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-sm dark:border-slate-700 dark:bg-[#111c17]"
                    />
                  </div>
                )}
              </div>

              {secondParentInsuranceTitle !== "none" && (
                <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={secondParentHasSickness}
                    onChange={(e) => setSecondParentHasSickness(e.target.checked)}
                    className="h-4 w-4 shrink-0 accent-[#007834]"
                  />
                  Rodzic 2 podlega ubezpieczeniu chorobowemu
                </label>
              )}

              {(!insuredOnDate || insuranceTitle === "none") &&
                secondParentInsuredClaim &&
                (secondParentInsuranceTitle === "uop" ||
                  secondParentInsuranceTitle === "zlecenie") && (
                  <div className="flex items-center justify-between gap-2 border-t border-slate-200 pt-2.5 dark:border-slate-700">
                    <label className="text-xs font-semibold text-slate-600 dark:text-slate-400">
                      <InfoTooltip
                        label="Ubezpieczeni u płatnika Rodzica 2"
                        tooltip="Decyduje o tym, czy w trybie art. 31 ust. 3h zasiłek ojca wypłaca jego pracodawca (> 20 osób), czy ZUS (≤ 20 osób)."
                      />
                    </label>
                    <input
                      type="number"
                      min={0}
                      value={secondParentEmployerCount}
                      onChange={(e) => setSecondParentEmployerCount(Number(e.target.value))}
                      className="w-24 rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm dark:border-slate-700 dark:bg-[#111c17]"
                    />
                  </div>
                )}
            </div>
          )}

          {/* Podstawa wymiaru zasiłku — w tym indywidualna podstawa wymiaru (pkt f) */}
          <div className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-emerald-950 dark:bg-[#16241d]">
            <p className="text-sm font-bold text-slate-800 dark:text-slate-200">
              <InfoTooltip
                label="Podstawa wymiaru zasiłku"
                tooltip="Możesz wyliczyć podstawę automatycznie z kwoty brutto, wpisać indywidualną podstawę wymiaru bezpośrednio z dokumentu (Z-3/Z-3a) lub użyć kreatora (średnia z 12 mies. z premiami, art. 48a/49 dla JDG, art. 43)."
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
                  className={`rounded-lg border px-2.5 py-2 text-xs font-semibold transition ${
                    baseMode === m.id
                      ? "border-[#007834] bg-[#007834] text-white"
                      : "border-slate-300 bg-white text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-[#111c17] dark:text-slate-300 dark:hover:bg-[#16241d]"
                  }`}
                >
                  {m.label}
                </button>
              ))}
            </div>

            <div className={`grid gap-3 ${singleParent ? "" : "sm:grid-cols-2"}`}>
              <div>
                <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300">
                  <InfoTooltip
                    label="Brutto rodzica 1 (zł)"
                    tooltip="Przeciętne miesięczne wynagrodzenie brutto (lub zadeklarowana podstawa składek na JDG) z ostatnich 12 miesięcy przed porodem. ZUS pomniejsza je o 13,71%."
                  />
                </label>
                <input
                  type="number"
                  min={0}
                  step="any"
                  value={grossSalary}
                  onChange={(e) => setGrossSalary(Number(e.target.value))}
                  className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-[#111c17]"
                />
              </div>
              {!singleParent && (
                <div>
                  <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300">
                    <InfoTooltip
                      label="Brutto rodzica 2 (zł)"
                      tooltip="Średnie wynagrodzenie brutto drugiego rodzica (np. ojca) — służy do wyliczenia jego zasiłku za przejęty macierzyński, rodzicielski oraz urlop ojcowski."
                    />
                  </label>
                  <input
                    type="number"
                    min={0}
                    step="any"
                    value={secondParentGross}
                    onChange={(e) => setSecondParentGross(Number(e.target.value))}
                    className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-[#111c17]"
                  />
                </div>
              )}
            </div>

            {(baseMode === "custom" || baseMode === "creator") && (
              <div
                className={`grid gap-3 border-t border-slate-200 pt-3 dark:border-slate-700 ${
                  singleParent ? "" : "sm:grid-cols-2"
                }`}
              >
                <div>
                  <label className="block text-sm font-bold text-[#005a27] dark:text-emerald-300">
                    <InfoTooltip
                      label="Indywidualna podstawa Rodzica 1 (zł)"
                      tooltip="Indywidualna podstawa wymiaru zasiłku po odliczeniu 13,71% (np. wyliczona z formularza Z-3/Z-3a lub poświadczenia ubezpieczenia ZUS)."
                    />
                  </label>
                  <input
                    type="number"
                    min={0}
                    step="any"
                    placeholder="np. 6903.20"
                    value={customBase1}
                    onChange={(e) => setCustomBase1(e.target.value)}
                    className="mt-1.5 w-full rounded-lg border border-[#007834] bg-white px-3 py-2 text-sm font-semibold dark:bg-[#111c17]"
                  />
                </div>
                {!singleParent && (
                  <div>
                    <label className="block text-sm font-bold text-slate-700 dark:text-slate-300">
                      <InfoTooltip
                        label="Indywidualna podstawa Rodzica 2 (zł)"
                        tooltip="Opcjonalna indywidualna podstawa wymiaru zasiłku dla drugiego rodzica (po odliczeniu 13,71%)."
                      />
                    </label>
                    <input
                      type="number"
                      min={0}
                      step="any"
                      placeholder="np. 7075.78"
                      value={customBase2}
                      onChange={(e) => setCustomBase2(e.target.value)}
                      className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-[#111c17]"
                    />
                  </div>
                )}
              </div>
            )}

            {baseMode === "creator" && (
              <div className="space-y-3 rounded-lg border border-[#007834]/30 bg-white p-3.5 text-sm dark:border-emerald-900 dark:bg-[#111c17]">
                <p className="font-bold text-[#005a27] dark:text-emerald-300">
                  Kreator indywidualnej podstawy wymiaru zasiłku (Art. 36–52 ustawy zasiłkowej)
                </p>
                <select
                  value={creatorSubMode}
                  onChange={(e) =>
                    setCreatorSubMode(
                      e.target.value as "uop_12m" | "jdg_art48a" | "previous_benefit"
                    )
                  }
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
                >
                  <option value="uop_12m">
                    Pracownik / Zlecenie: średnia z miesięcy (Z-3/Z-3a) + premie kwartalne/roczne (1/12)
                  </option>
                  <option value="jdg_art48a">
                    Działalność gospodarcza (JDG): proporcjonalna podstawa wg Art. 48a / 49 (0–12 mies.)
                  </option>
                  <option value="previous_benefit">
                    Zachowana podstawa z poprzedniego zasiłku (przerwa &lt; 1 mies. — Art. 43)
                  </option>
                </select>

                {creatorSubMode === "uop_12m" && (
                  <div className="space-y-2.5">
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                        Wynagrodzenia brutto z pełnych miesięcy (średnik lub przecinek, do 12 mies.)
                      </label>
                      <input
                        type="text"
                        placeholder="np. 7 500,50; 8 000,00; 8 000,00"
                        value={creatorSalariesText}
                        onChange={(e) => setCreatorSalariesText(e.target.value)}
                        className="mt-1.5 w-full rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm dark:border-slate-700"
                      />
                      <p
                        className={`mt-1 text-xs ${
                          parsedCreatorSalaries.length === 0 || parsedCreatorSalaries.length > 12
                            ? "font-semibold text-amber-700 dark:text-amber-300"
                            : "text-slate-500 dark:text-slate-400"
                        }`}
                      >
                        Rozpoznano {parsedCreatorSalaries.length} mies. wynagrodzeń
                        {parsedCreatorSalaries.length > 12
                          ? " (API wykorzysta ostatnie 12 miesięcy)"
                          : ""}
                        .
                      </p>
                    </div>
                    <div className="grid grid-cols-2 gap-2.5">
                      <div>
                        <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
                          Suma premii kwartalnych z 4 kw. (1/12 — art. 42 ust. 2)
                        </label>
                        <input
                          type="number"
                          min={0}
                          value={creatorQuarterlyBonus}
                          onChange={(e) => setCreatorQuarterlyBonus(Number(e.target.value))}
                          className="mt-1 w-full rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm dark:border-slate-700"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
                          Nagroda roczna / 13-tka za rok poprz. (1/12 — art. 42 ust. 3)
                        </label>
                        <input
                          type="number"
                          min={0}
                          value={creatorAnnualBonus}
                          onChange={(e) => setCreatorAnnualBonus(Number(e.target.value))}
                          className="mt-1 w-full rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm dark:border-slate-700"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2.5">
                      <div>
                        <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
                          Miesiące wyłączone (&lt;1/2 czasu pracy — art. 38)
                        </label>
                        <input
                          type="number"
                          min={0}
                          max={11}
                          value={creatorExcludedMonths}
                          onChange={(e) => setCreatorExcludedMonths(Number(e.target.value))}
                          className="mt-1 w-full rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm dark:border-slate-700"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
                          Wymiar etatu (dla min. podstawy z art. 45)
                        </label>
                        <input
                          type="number"
                          min={0.1}
                          max={1.0}
                          step="any"
                          value={creatorFte}
                          onChange={(e) => setCreatorFte(Number(e.target.value))}
                          className="mt-1 w-full rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm dark:border-slate-700"
                        />
                      </div>
                    </div>
                  </div>
                )}

                {creatorSubMode === "jdg_art48a" && (
                  <div className="space-y-2.5">
                    <div className="grid grid-cols-3 gap-2.5">
                      <div>
                        <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
                          <InfoTooltip
                            label="Pełne mies. (0–12)"
                            tooltip="0 pełnych miesięcy kalendarzowych = art. 49 ust. 1 pkt 1 (najniższa podstawa składek). 1–11 mies. = art. 48a (najniższa + 1/12 nadwyżki za każdy pełny miesiąc)."
                          />
                        </label>
                        <input
                          type="number"
                          min={0}
                          max={12}
                          value={creatorJdgMonths}
                          onChange={(e) => setCreatorJdgMonths(Number(e.target.value))}
                          className="mt-1 w-full rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm dark:border-slate-700"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
                          Deklarowana podstawa (zł)
                        </label>
                        <input
                          type="number"
                          min={0}
                          step="any"
                          value={creatorJdgDeclared}
                          onChange={(e) => setCreatorJdgDeclared(Number(e.target.value))}
                          className="mt-1 w-full rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm dark:border-slate-700"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
                          Najniższa podstawa JDG (zł)
                        </label>
                        <input
                          type="number"
                          min={0}
                          step="any"
                          value={creatorJdgMin}
                          onChange={(e) => setCreatorJdgMin(Number(e.target.value))}
                          className="mt-1 w-full rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm dark:border-slate-700"
                        />
                      </div>
                    </div>
                    <label className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300">
                      <input
                        type="checkbox"
                        checked={creatorJdgPreferential}
                        onChange={(e) => {
                          const checked = e.target.checked;
                          setCreatorJdgPreferential(checked);
                          setCreatorJdgMin(checked ? jdgPrefMin : jdgStdMin);
                        }}
                        className="h-4 w-4 shrink-0 accent-[#007834]"
                      />
                      Preferencyjny ZUS — 30% płacy minimalnej ({jdgPrefMin.toFixed(2).replace(".", ",")} zł zamiast {jdgStdMin.toFixed(2).replace(".", ",")} zł w {paramsYear} r.)
                    </label>
                  </div>
                )}

                {creatorSubMode === "previous_benefit" && (
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                      Poprzednia podstawa wymiaru zasiłku (np. z zasiłku chorobowego w ciąży, zł)
                    </label>
                    <input
                      type="number"
                      min={0}
                      step="any"
                      value={creatorPrevBase}
                      onChange={(e) => setCreatorPrevBase(Number(e.target.value))}
                      className="mt-1.5 w-full rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm dark:border-slate-700"
                    />
                  </div>
                )}

                <button
                  type="button"
                  onClick={handleComputeIndividualBase}
                  className="w-full rounded-lg bg-[#007834] px-3 py-2 text-sm font-semibold text-white hover:bg-[#005a27]"
                >
                  Wylicz indywidualną podstawę wymiaru i wstaw do kalkulatora
                </button>

                {baseCalcResult && (
                  <div className="rounded-lg bg-[#e6f4ec] p-3 text-xs leading-relaxed text-[#005a27] dark:bg-[#007834]/20 dark:text-emerald-300">
                    <p className="text-sm font-bold">
                      Wyliczona podstawa: {baseCalcResult.computed_base_monthly.toFixed(2)} zł (stawka
                      dzienna 100%: {baseCalcResult.daily_rate_100_percent.toFixed(2)} zł | {combinedRateStr}:{" "}
                      {baseCalcResult.daily_rate_81_5_percent.toFixed(2)} zł | 70%:{" "}
                      {baseCalcResult.daily_rate_70_percent.toFixed(2)} zł)
                    </p>
                    <p className="mt-1 opacity-90">
                      Podstawa prawna: {baseCalcResult.legal_basis}
                    </p>
                    <ul className="mt-1.5 list-disc space-y-0.5 pl-4">
                      {baseCalcResult.explanation_steps.map((s, idx) => (
                        <li key={idx}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>

          <div
            className={`grid gap-3 ${
              insuranceTitle === "uop" || insuranceTitle === "zlecenie" ? "sm:grid-cols-2" : ""
            }`}
          >
            <div>
              <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300">
                <InfoTooltip
                  label="Wariant wypłaty"
                  tooltip={`${combinedRateStr} przez cały okres wymaga złożenia jednego wniosku w ciągu ${deadlineDays} dni od porodu/przyjęcia dziecka. Wariant 100% + 70% oznacza 100% na macierzyńskim i 70% na rodzicielskim.`}
                />
              </label>
              <select
                value={paymentVariant}
                onChange={(e) => setPaymentVariant(e.target.value as PaymentVariant)}
                className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
              >
                <option value="81_5">
                  {combinedRateStr} (wniosek w {deadlineDays} dni)
                </option>
                <option value="100_70">100% macierzyński + 70% rodzicielski</option>
              </select>
            </div>
            {(insuranceTitle === "uop" || insuranceTitle === "zlecenie") && (
              <div>
                <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300">
                  <InfoTooltip
                    label="Ubezpieczeni u płatnika (Rodzic 1)"
                    tooltip={`Liczba osób zgłoszonych do ubezpieczenia chorobowego przez Twojego pracodawcę/zleceniodawcę na dzień 30 listopada poprzedniego roku. Powyżej ${legalParams?.payer_employee_threshold ?? 20} osób zasiłek wypłaca płatnik składek, do ${legalParams?.payer_employee_threshold ?? 20} osób — ZUS.`}
                  />
                </label>
                <input
                  type="number"
                  min={0}
                  value={employerCount}
                  onChange={(e) => setEmployerCount(Number(e.target.value))}
                  className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
                />
              </div>
            )}
          </div>

          {insuranceTitle === "jdg" && (
            <div>
              <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300">
                <InfoTooltip
                  label="Zaległość składkowa ZUS na JDG — Rodzic 1 (zł, art. 2a)"
                  tooltip={`Dla osób prowadzących działalność gospodarczą zadłużenie z tytułu składek przekraczające 1% minimalnego wynagrodzenia (${debtThresholdStr} zł w ${paramsYear} r.) wstrzymuje wypłatę zasiłku do czasu uregulowania zaległości (max ${legalParams?.claim_limitation_months ?? 6} mies. na spłatę).`}
                />
              </label>
              <input
                type="number"
                min={0}
                step="any"
                value={contributionDebt}
                onChange={(e) => setContributionDebt(Number(e.target.value))}
                className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
              />
            </div>
          )}

          {/* Podział między rodziców */}
          <div className="space-y-3 rounded-lg border border-slate-200 p-4 dark:border-emerald-950">
            <p className="text-sm font-bold text-slate-800 dark:text-slate-200">
              <InfoTooltip
                label="2. Podział opieki między rodziców"
                tooltip="Urlopem macierzyńskim (po pierwszych 14 tygodniach przy porodzie, lub po 8 tyg. w sytuacjach szczególnych) lub urlopem na warunkach macierzyńskiego i rodzicielskim możecie się podzielić między oboje rodziców."
              />
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400">
                  <InfoTooltip
                    label={
                      scenario === "birth"
                        ? `Macierzyński matki (min. ${stillbirthOrEarlyDeath || motherEarlyTransfer8Weeks ? 8 : minMotherWeeks} tyg.)`
                        : "Urlop na warunkach macierzyńskiego — Rodzic 1 (tyg.)"
                    }
                    tooltip={
                      scenario === "birth"
                        ? "Pierwsze 14 tygodni po porodzie (lub 8 tygodni w razie hospitalizacji/niezdolności matki bądź urodzenia martwego dziecka) matka wykorzystuje osobiście. Pozostałą część może przejąć ojciec."
                        : "Liczba tygodni urlopu na warunkach urlopu macierzyńskiego wykorzystana przez pierwszego rodzica adopcyjnego/zastępczego."
                    }
                  />
                </label>
                <input
                  type="number"
                  min={
                    scenario === "birth"
                      ? stillbirthOrEarlyDeath || motherEarlyTransfer8Weeks
                        ? 8
                        : minMotherWeeks
                      : 0
                  }
                  max={maxMatWeeks}
                  value={motherMaternityWeeks}
                  onChange={(e) => setMotherMaternityWeeks(Number(e.target.value))}
                  className="mt-1.5 w-full rounded-lg border border-slate-300 px-2.5 py-2 text-sm dark:border-slate-700"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400">
                  <InfoTooltip
                    label="Rodzicielski Rodzica 1 (puste = maks.)"
                    tooltip="Pozostaw puste, aby Rodzic 1 wykorzystał całą dostępną dla siebie pulę urlopu rodzicielskiego. Wpisz 0, aby sprawdzić jednorazowe wyrównanie do 100% za macierzyński (art. 31 ust. 4 ustawy zasiłkowej)."
                  />
                </label>
                <input
                  type="number"
                  min={0}
                  max={maxSingleParentParental}
                  placeholder="maks. dostępna pula"
                  value={motherParentalWeeks}
                  onChange={(e) => setMotherParentalWeeks(e.target.value)}
                  className="mt-1.5 w-full rounded-lg border border-slate-300 px-2.5 py-2 text-sm dark:border-slate-700"
                />
              </div>

              {!singleParent && (
                <div className="sm:col-span-2">
                  <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400">
                    <InfoTooltip
                      label="Rodzicielski dla 2. rodzica (tyg.)"
                      tooltip="Każdemu z rodziców przysługuje 9 tygodni wyłącznego, nieprzenoszalnego urlopu rodzicielskiego (płatne 70%). Drugi rodzic może też przejąć więcej tygodni ze wspólnej puli (wówczas w wariancie 81,5% część wspólna jest płatna 81,5%, a 9 tyg. nieprzenoszalnych — 70%)."
                    />
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={maxParentalWeeks}
                    value={fatherParentalWeeks}
                    onChange={(e) => setFatherParentalWeeks(Number(e.target.value))}
                    className="mt-1.5 w-full rounded-lg border border-slate-300 px-2.5 py-2 text-sm dark:border-slate-700"
                  />
                </div>
              )}
            </div>

            {scenario === "birth" && !singleParent && (
              <div className="space-y-1.5 pt-1">
                <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={motherEarlyTransfer8Weeks}
                    onChange={(e) => {
                      const checked = e.target.checked;
                      setMotherEarlyTransfer8Weeks(checked);
                      if (!checked && motherMaternityWeeks < minMotherWeeks) {
                        setMotherMaternityWeeks(minMotherWeeks);
                      }
                    }}
                    className="h-4 w-4 shrink-0 accent-[#007834]"
                  />
                  <InfoTooltip
                    label="Szczególna sytuacja matki: przekazanie macierzyńskiego ojcu już po 8 tyg. (art. 180 § 6/10 KP)"
                    tooltip="W razie pobytu matki w szpitalu lub orzeczenia o niezdolności do samodzielnej egzystencji ojciec może przejąć urlop macierzyński po wykorzystaniu przez matkę min. 8 tygodni."
                  />
                </label>
              </div>
            )}

            {!singleParent && scenario !== "foster" && (
              <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={fatherPaternity}
                  onChange={(e) => setFatherPaternity(e.target.checked)}
                  className="h-4 w-4 shrink-0 accent-[#007834]"
                />
                <InfoTooltip
                  label="Uwzględnij urlop ojcowski (2 tygodnie, 100%)"
                  tooltip="Wyłączne prawo ojca biologicznego lub adopcyjnego (14 dni kalendarzowych jednorazowo lub w 2 częściach po 7 dni)."
                />
              </label>
            )}
          </div>

          {/* Opcje zaawansowane */}
          <div className="space-y-3 rounded-lg border border-slate-200 p-4 dark:border-emerald-950">
            <p className="text-sm font-bold text-slate-800 dark:text-slate-200">
              3. Opcje dodatkowe i sytuacje szczególne
            </p>
            <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                checked={hasZaZyciem}
                onChange={(e) => setHasZaZyciem(e.target.checked)}
                className="h-4 w-4 shrink-0 accent-[#007834]"
              />
              <InfoTooltip
                label="Zaświadczenie „Za życiem” (65/67 tyg.)"
                tooltip="Wydawane przez lekarza specjalistę przy ciężkim i nieodwracalnym upośledzeniu lub nieuleczalnej chorobie zagrażającej życiu. Wydłuża urlop rodzicielski o 24 tygodnie."
              />
            </label>

            <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                checked={premature}
                onChange={(e) => setPremature(e.target.checked)}
                className="h-4 w-4 shrink-0 accent-[#007834]"
              />
              <InfoTooltip
                label="Wcześniak / hospitalizacja (uzupełniający urlop)"
                tooltip="Dodatkowy urlop macierzyński (płatny 100%) udzielany jednorazowo po macierzyńskim: 1 tydzień za każdy tydzień pobytu dziecka w szpitalu (do 8 lub 15 tygodni)."
              />
            </label>
            {premature && (
              <div className="space-y-2.5 pt-1">
                <div className="grid grid-cols-3 gap-2.5">
                  <div>
                    <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
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
                      className="mt-1 w-full rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm dark:border-slate-700"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
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
                      className="mt-1 w-full rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm dark:border-slate-700"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
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
                      className="mt-1 w-full rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm dark:border-slate-700"
                    />
                  </div>
                </div>
                {gestationWeek >= 37 && birthWeight > 1000 && (
                  <label className="flex items-center gap-2 rounded-lg bg-slate-50 p-2.5 text-xs text-slate-700 dark:bg-[#16241d] dark:text-slate-300">
                    <input
                      type="checkbox"
                      checked={fullTermHospConditionMet}
                      onChange={(e) => setFullTermHospConditionMet(e.target.checked)}
                      className="h-4 w-4 shrink-0 accent-[#007834]"
                    />
                    <InfoTooltip
                      label="Pobyt trwał ≥ 2 kolejne dni z 1. dniem w przedziale 5.–28. dnia po porodzie (art. 180² § 1 pkt 3 KP)"
                      tooltip="Dla dziecka urodzonego w terminie (≥ 37. tydzień i masa > 1000 g) uzupełniający urlop macierzyński przysługuje wyłącznie, gdy hospitalizacja trwała co najmniej 2 kolejne dni, a pierwszy dzień pobytu przypadł od 5. do 28. dnia po porodzie."
                    />
                  </label>
                )}
              </div>
            )}

            <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                checked={combineWork}
                onChange={(e) => setCombineWork(e.target.checked)}
                className="h-4 w-4 shrink-0 accent-[#007834]"
              />
              <InfoTooltip
                label="Łączenie urlopu rodzicielskiego z pracą — Rodzic 1 (maks. 1/2 etatu, UoP)"
                tooltip="Pracownik na umowie o pracę może pracować u swojego pracodawcy maks. na pół etatu podczas urlopu rodzicielskiego — urlop ulega wtedy proporcjonalnemu wydłużeniu (art. 182¹ᵉ i 182¹ᶠ KP)."
              />
            </label>
            {combineWork && (
              <div className="space-y-2.5 rounded-lg border border-slate-200 bg-slate-50/70 p-3 dark:border-slate-800 dark:bg-[#16241d]/70">
                {insuranceTitle !== "uop" && (
                  <p className="text-xs font-medium text-amber-800 dark:text-amber-300">
                    Uwaga: ustawowe wydłużenie urlopu przy łączeniu z pracą z art. 182¹ᵉ–182¹ᶠ KP
                    dotyczy wyłącznie pracowników (umowa o pracę).
                  </p>
                )}
                <div className="grid grid-cols-2 gap-2.5">
                  <div>
                    <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
                      <InfoTooltip
                        label="Wymiar etatu (0.1–0.5)"
                        tooltip="Część pełnego etatu, na jaką wracasz do pracy podczas urlopu rodzicielskiego (np. 0.5 = pół etatu)."
                      />
                    </label>
                    <input
                      type="number"
                      min={0.1}
                      max={0.5}
                      step="any"
                      value={workFte}
                      onChange={(e) => setWorkFte(Number(e.target.value))}
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm dark:border-slate-700 dark:bg-[#111c17]"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
                      <InfoTooltip
                        label="Liczba tyg. pracy"
                        tooltip="Przez ile tygodni urlopu rodzicielskiego planujesz łączyć opiekę nad dzieckiem z pracą na część etatu."
                      />
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={maxSingleParentParental}
                      value={workWeeks}
                      onChange={(e) => setWorkWeeks(Number(e.target.value))}
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm dark:border-slate-700 dark:bg-[#111c17]"
                    />
                  </div>
                </div>
                <label className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={workDuringExtendedPart}
                    onChange={(e) => setWorkDuringExtendedPart(e.target.checked)}
                    className="h-4 w-4 shrink-0 accent-[#007834]"
                  />
                  <InfoTooltip
                    label="Praca na część etatu również podczas części wydłużonej (art. 182¹ᶠ § 7 KP)"
                    tooltip="Zaznaczone (art. 182¹ᶠ § 7 KP): pracujesz również w okresie wydłużenia, więc wydłużenie wynosi T × etat / (1 - etat). Odznaczone (art. 182¹ᶠ § 2 KP): w okresie wydłużenia nie pracujesz, a wydłużenie wynosi T × etat. Część niepełnego dnia ulega pominięciu (art. 182¹ᶠ § 4 KP)."
                  />
                </label>
              </div>
            )}

            {!singleParent &&
              secondParentInsuranceTitle === "uop" &&
              secondParentHasSickness &&
              (fatherParentalWeeks > 0 ||
                ((!insuredOnDate || insuranceTitle === "none") && secondParentInsuredClaim)) && (
                <>
                  <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                    <input
                      type="checkbox"
                      checked={fatherCombineWork}
                      onChange={(e) => setFatherCombineWork(e.target.checked)}
                      className="h-4 w-4 shrink-0 accent-[#007834]"
                    />
                    <InfoTooltip
                      label="Łączenie urlopu rodzicielskiego z pracą — Rodzic 2 (maks. 1/2 etatu, UoP)"
                      tooltip="Drugi rodzic zatrudniony na umowę o pracę może łączyć swoją część urlopu rodzicielskiego (zarówno 9 tyg. nieprzenoszalnych, jak i przejętą część wspólną) z pracą do 1/2 etatu."
                    />
                  </label>
                  {fatherCombineWork && (
                    <div className="space-y-2.5 rounded-lg border border-slate-200 bg-slate-50/70 p-3 dark:border-slate-800 dark:bg-[#16241d]/70">
                      <div className="grid grid-cols-2 gap-2.5">
                        <div>
                          <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
                            Wymiar etatu Rodzica 2 (0.1–0.5)
                          </label>
                          <input
                            type="number"
                            min={0.1}
                            max={0.5}
                            step="any"
                            value={fatherWorkFte}
                            onChange={(e) => setFatherWorkFte(Number(e.target.value))}
                            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm dark:border-slate-700 dark:bg-[#111c17]"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
                            Liczba tyg. pracy Rodzica 2
                          </label>
                          <input
                            type="number"
                            min={1}
                            max={maxSingleParentParental}
                            value={fatherWorkWeeks}
                            onChange={(e) => setFatherWorkWeeks(Number(e.target.value))}
                            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm dark:border-slate-700 dark:bg-[#111c17]"
                          />
                        </div>
                      </div>
                      <label className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300">
                        <input
                          type="checkbox"
                          checked={fatherWorkDuringExtendedPart}
                          onChange={(e) => setFatherWorkDuringExtendedPart(e.target.checked)}
                          className="h-4 w-4 shrink-0 accent-[#007834]"
                        />
                        Praca Rodzica 2 również podczas części wydłużonej (art. 182¹ᶠ § 7 KP)
                      </label>
                    </div>
                  )}
                </>
              )}

            {scenario === "birth" && (
              <div className="space-y-2.5 border-t border-slate-200 pt-2.5 dark:border-slate-800">
                <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={stillbirthOrEarlyDeath}
                    onChange={(e) => setStillbirthOrEarlyDeath(e.target.checked)}
                    className="h-4 w-4 shrink-0 accent-[#007834]"
                  />
                  <InfoTooltip
                    label="Szczególna sytuacja: urodzenie martwego dziecka / zgon w 1–8 tyg. (art. 180¹ § 1 KP)"
                    tooltip="W razie urodzenia martwego dziecka lub zgonu dziecka przed upływem 8 tygodni życia przysługuje zasiłek macierzyński (100%) za okres 8 tygodni urlopu macierzyńskiego po porodzie (nie krócej niż 7 dni od dnia zgonu)."
                  />
                </label>

                <div className="flex items-center justify-between gap-2">
                  <label className="text-xs font-medium text-slate-600 dark:text-slate-400">
                    <InfoTooltip
                      label="Urlop macierzyński przed porodem (0–6 tyg., art. 180 § 2 KP)"
                      tooltip="Kobieta w ciąży może wykorzystać do 6 tygodni urlopu macierzyńskiego jeszcze przed przewidywaną datą porodu — po porodzie musi wykorzystać min. 14 tyg. (lub 8 tyg. w przypadkach szczególnych), aby przekazać resztę ojcu."
                    />
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={6}
                    value={preBirthWeeks}
                    onChange={(e) => setPreBirthWeeks(Number(e.target.value))}
                    className="w-20 rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm dark:border-slate-700"
                  />
                </div>
              </div>
            )}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-[#007834] px-4 py-3 text-base font-semibold text-white transition hover:bg-[#005a27] disabled:opacity-50"
          >
            {loading ? "Obliczanie..." : "Oblicz wymiary i wysokość zasiłku"}
          </button>

          {error && <p className="text-sm font-medium text-red-600">{error}</p>}
        </form>

        {/* Wyniki */}
        <div className="space-y-5 lg:col-span-7">
          {result ? (
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs dark:border-emerald-950 dark:bg-[#111c17]">
              {!result.eligible ? (
                <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-800/60 dark:bg-red-950/40 dark:text-red-200">
                  <p className="text-base font-bold">Brak uprawnień do zasiłku macierzyńskiego</p>
                  <p className="mt-1 leading-relaxed">{result.ineligibility_reason}</p>
                </div>
              ) : (
                <>
                  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                    <div className="flex flex-col justify-between rounded-lg bg-[#e6f4ec] p-4 dark:bg-[#007834]/20">
                      <p className="text-xs font-medium text-[#005a27] dark:text-emerald-300">
                        Łączny czas urlopów
                      </p>
                      <p className="mt-2 whitespace-nowrap text-xl font-bold tabular-nums text-[#005a27] dark:text-emerald-300">
                        {result.total_weeks}&nbsp;tyg.
                      </p>
                    </div>
                    <div className="flex flex-col justify-between rounded-lg bg-slate-50 p-4 dark:bg-[#16241d]">
                      <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
                        Szacowana suma brutto
                      </p>
                      <p className="mt-2 whitespace-nowrap text-lg font-bold tabular-nums text-slate-900 dark:text-slate-100 xl:text-xl">
                        {formatPln(result.total_estimated_gross_pln)}
                      </p>
                    </div>
                    <div className="flex flex-col justify-between rounded-lg bg-slate-50 p-4 dark:bg-[#16241d]">
                      <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
                        Podstawa Rodzica 1
                      </p>
                      <p className="mt-2 whitespace-nowrap text-lg font-bold tabular-nums text-slate-900 dark:text-slate-100 xl:text-xl">
                        {result.benefit_base_parent1 > 0
                          ? formatPln(result.benefit_base_parent1)
                          : "—"}
                      </p>
                    </div>
                    <div className="flex flex-col justify-between rounded-lg bg-slate-50 p-4 dark:bg-[#16241d]">
                      <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
                        Podstawa Rodzica 2
                      </p>
                      <p className="mt-2 whitespace-nowrap text-lg font-bold tabular-nums text-slate-900 dark:text-slate-100 xl:text-xl">
                        {result.benefit_base_parent2 > 0
                          ? formatPln(result.benefit_base_parent2)
                          : "—"}
                      </p>
                    </div>
                  </div>

                  {result.payout_suspended_due_to_debt && (
                    <div className="mt-4 rounded-lg border border-amber-300 bg-amber-50 p-3.5 text-sm leading-relaxed font-medium text-amber-900 dark:border-amber-800/60 dark:bg-amber-950/40 dark:text-amber-200">
                      <strong>Wstrzymanie wypłaty zasiłku (art. 2a ustawy zasiłkowej):</strong>{" "}
                      wykryto zadłużenie składkowe ZUS na JDG przekraczające 1% płacy minimalnej
                      ({debtThresholdStr} zł). Prawo do świadczenia istnieje, jednak wypłata nastąpi
                      dopiero po uregulowaniu zaległości (w ciągu {legalParams?.claim_limitation_months ?? 6} miesięcy od powstania prawa).
                    </div>
                  )}

                  {result.minimum_benefit_top_up_applied && (
                    <div className="mt-4 rounded-lg border border-emerald-300 bg-emerald-50 p-3.5 text-sm leading-relaxed font-medium text-emerald-900 dark:border-emerald-800/60 dark:bg-emerald-950/40 dark:text-emerald-200">
                      Zastosowano ustawowe podwyższenie zasiłku macierzyńskiego do kwoty świadczenia
                      rodzicielskiego (min. {minMonthlyFloorStr} zł miesięcznie — art. 31 ust. 3a ustawy
                      zasiłkowej).
                    </div>
                  )}

                  {result.equalization_to_100_pln > 0 && (
                    <div className="mt-4 rounded-lg border border-emerald-300 bg-emerald-50 p-3.5 text-sm leading-relaxed font-medium text-emerald-900 dark:border-emerald-800/60 dark:bg-emerald-950/40 dark:text-emerald-200">
                      <strong>Jednorazowe wyrównanie do 100% (art. 31 ust. 4 ustawy zasiłkowej):</strong>{" "}
                      +{formatPln(result.equalization_to_100_pln)} brutto za okres urlopu
                      macierzyńskiego (niewykorzystanie ani jednego dnia zasiłku za urlop
                      rodzicielski w wariancie {combinedRateStr}). Kwota została doliczona do łącznej sumy.
                    </div>
                  )}

                  {/* Szczegółowe wyjaśnienie podstawy wymiaru zasiłku (pkt f) */}
                  {result.benefit_base_explanation && (
                    <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3.5 text-sm leading-relaxed text-slate-700 dark:border-emerald-950 dark:bg-[#16241d] dark:text-slate-300">
                      <p className="font-bold text-slate-900 dark:text-slate-100">
                        Sposób ustalenia podstawy wymiaru zasiłku:
                      </p>
                      <p className="mt-1">
                        <strong>Rodzic 1:</strong> {result.benefit_base_explanation}
                      </p>
                      {result.benefit_base_parent2_explanation && (
                        <p className="mt-1">
                          <strong>Rodzic 2:</strong> {result.benefit_base_parent2_explanation}
                        </p>
                      )}
                    </div>
                  )}

                  <p className="mt-4 text-sm text-slate-700 dark:text-slate-300">
                    <strong>Płatnik świadczenia:</strong> {result.payer}
                  </p>

                  {/* Tabela harmonogramu */}
                  <div className="mt-5 overflow-x-auto">
                    <table className="w-full border-collapse text-left text-sm">
                      <thead>
                        <tr className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-600 dark:border-emerald-950 dark:bg-[#16241d] dark:text-slate-400">
                          <th className="p-3">Rodzaj urlopu / zasiłku</th>
                          <th className="whitespace-nowrap p-3">Rodzic</th>
                          <th className="whitespace-nowrap p-3 text-right">Tyg.</th>
                          <th className="whitespace-nowrap p-3 text-right">Stawka</th>
                          <th className="whitespace-nowrap p-3 text-right">Miesięcznie</th>
                          <th className="whitespace-nowrap p-3 text-right">Łącznie brutto</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.breakdown.map((row, idx) => (
                          <tr
                            key={idx}
                            className="border-b border-slate-100 dark:border-slate-800"
                          >
                            <td className="p-3 font-medium text-slate-900 dark:text-slate-100">
                              {row.label}
                              {row.notes && (
                                <p className="mt-1 text-xs font-normal leading-relaxed text-slate-500 dark:text-slate-400">
                                  {row.notes}
                                </p>
                              )}
                            </td>
                            <td className="whitespace-nowrap p-3 text-slate-700 dark:text-slate-300">
                              {row.parent}
                            </td>
                            <td className="whitespace-nowrap p-3 text-right font-semibold tabular-nums">
                              {row.weeks}
                              {row.days != null && row.days % 7 !== 0 && (
                                <span className="block text-xs font-normal text-slate-500 dark:text-slate-400">
                                  ({row.days}&nbsp;dni)
                                </span>
                              )}
                            </td>
                            <td className="whitespace-nowrap p-3 text-right tabular-nums">
                              {row.rate_percent}%
                            </td>
                            <td className="whitespace-nowrap p-3 text-right tabular-nums">
                              {formatPln(row.monthly_gross_pln)}
                            </td>
                            <td className="whitespace-nowrap p-3 text-right font-semibold tabular-nums text-[#005a27] dark:text-emerald-300">
                              {formatPln(row.total_gross_pln)}
                            </td>
                          </tr>
                        ))}
                        {result.equalization_to_100_pln > 0 && (
                          <tr className="border-b border-emerald-200 bg-emerald-50/70 dark:border-emerald-900 dark:bg-emerald-950/30">
                            <td className="p-3 font-semibold text-[#005a27] dark:text-emerald-300">
                              Jednorazowe wyrównanie do 100% za urlop macierzyński (art. 31 ust. 4)
                            </td>
                            <td className="whitespace-nowrap p-3 text-slate-700 dark:text-slate-300">
                              Rodzic 1 / Rodzic 2
                            </td>
                            <td className="whitespace-nowrap p-3 text-right font-semibold">—</td>
                            <td className="whitespace-nowrap p-3 text-right tabular-nums">
                              {eqDiffPpStr}
                            </td>
                            <td className="whitespace-nowrap p-3 text-right">—</td>
                            <td className="whitespace-nowrap p-3 text-right font-bold tabular-nums text-[#005a27] dark:text-emerald-300">
                              +{formatPln(result.equalization_to_100_pln)}
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>

                  {result.required_documents.length > 0 && (
                    <div className="mt-5 rounded-lg bg-slate-50 p-4 dark:bg-[#16241d]">
                      <p className="text-sm font-bold text-slate-800 dark:text-slate-200">
                        Wymagane dokumenty
                      </p>
                      <ul className="mt-1.5 list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-slate-700 dark:text-slate-300">
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
                  <p className="text-sm font-bold text-amber-900 dark:text-amber-200">
                    Uwagi i zasady prawne
                  </p>
                  <ul className="mt-1.5 list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-amber-900 dark:text-amber-200">
                    {result.warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm leading-relaxed text-slate-500 dark:border-slate-700 dark:bg-[#111c17] dark:text-slate-400">
              Skonfiguruj parametry po lewej stronie (lub wybierz gotową sprawę z zestawu ZUS u góry)
              i kliknij „Oblicz wymiary i wysokość zasiłku”, aby wygenerować symulację dla obojga
              rodziców.
            </div>
          )}
        </div>
      </div>
        </>
      )}
    </div>
  );
}
