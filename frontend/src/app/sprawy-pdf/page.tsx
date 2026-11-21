"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/PageHeader";
import { PREGNANCY_PREFILL_STORAGE_KEY } from "@/components/PregnancyCalculatorPanel";
import { api } from "@/lib/api";
import type {
  BenefitScenario,
  CaseDocumentsAnalysisResult,
  InsuranceTitle,
  PaymentVariant,
  PdfAnalysisResult,
  SampleCase,
  SicknessInsuranceStatus,
} from "@/lib/types";

const PREFILL_STORAGE_KEY = "zppr-prefill-calculator";

type TargetMode = "pregnancy_sickness" | "maternity_parental";
type TriBool = "unknown" | "yes" | "no";

const DOMAIN_LABELS: Record<PdfAnalysisResult["document_domain"], string> = {
  sickness_pregnancy: "Zasiłek chorobowy / świadczenia w ciąży",
  sickness_general: "Zwolnienie / zasiłek chorobowy (bez adnotacji o ciąży)",
  maternity_parental: "Zasiłek macierzyński / rodzicielski / ojcowski",
  payer_or_insurance_certificate: "Zaświadczenie płatnika / dokument ubezpieczenia ZUS",
  care_benefit: "Zasiłek opiekuńczy",
  other_benefit: "Inne świadczenie pozachorobowe",
  unknown: "Dokument do klasyfikacji ręcznej",
};

export default function SampleCasesPdfPage() {
  const router = useRouter();
  const [cases, setCases] = useState<SampleCase[]>([]);
  const [caseResult, setCaseResult] = useState<CaseDocumentsAnalysisResult | null>(null);
  const pdfResult = caseResult?.merged ?? null;

  // Kontekst docelowego kalkulatora (wybierany wg domeny dokumentu)
  const [targetMode, setTargetMode] = useState<TargetMode>("maternity_parental");

  // Pola weryfikacyjne — ZERO ZGADYWANIA: każde nieodczytane pole jest PUSTE ("") albo "unknown"
  const [confirmTitle, setConfirmTitle] = useState<InsuranceTitle | "">("");
  const [confirmInsuranceStatus, setConfirmInsuranceStatus] =
    useState<SicknessInsuranceStatus>("unknown");
  const [confirmGross, setConfirmGross] = useState<string>("");
  const [confirmCustomBase, setConfirmCustomBase] = useState<string>("");
  const [confirmEmployerCount, setConfirmEmployerCount] = useState<string>("");
  const [confirmDebt, setConfirmDebt] = useState<string>("");

  // Pola specyficzne dla chorobowego / ciąży
  const [confirmCodeB, setConfirmCodeB] = useState<TriBool>("unknown");
  const [confirmInsuranceDays, setConfirmInsuranceDays] = useState<string>("");
  const [confirmFte, setConfirmFte] = useState<string>("");
  const [confirmSpecialTermination, setConfirmSpecialTermination] = useState(false);
  const [confirmTerminationReason, setConfirmTerminationReason] = useState<string>(
    "bankruptcy_liquidation"
  );

  // Pola specyficzne dla macierzyńskiego / rodzicielskiego
  const [confirmScenario, setConfirmScenario] = useState<BenefitScenario | "">("");
  const [confirmChildren, setConfirmChildren] = useState<string>("");
  const [confirmVariant, setConfirmVariant] = useState<PaymentVariant | "">("");
  const [confirmZaZyciem, setConfirmZaZyciem] = useState(false);
  const [confirmPremature, setConfirmPremature] = useState(false);
  const [confirmStillbirth, setConfirmStillbirth] = useState(false);
  const [confirmCombineWork, setConfirmCombineWork] = useState(false);
  const [confirmFatherPaternity, setConfirmFatherPaternity] = useState(false);

  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getSampleCases().then(setCases).catch((e) => setError(String(e)));
  }, []);

  const openInCalculator = (prefill: Record<string, unknown>) => {
    sessionStorage.setItem(PREFILL_STORAGE_KEY, JSON.stringify(prefill));
    router.push("/kalkulator");
  };

  const openInPregnancyCalculator = (prefill: Record<string, unknown>) => {
    sessionStorage.setItem(PREGNANCY_PREFILL_STORAGE_KEY, JSON.stringify(prefill));
    router.push("/ciaza");
  };

  const runSampleCase = (c: SampleCase) => {
    openInCalculator({
      sourceLabel: c.title,
      fromSampleCase: true,
      scenario: c.scenario,
      insurance_title: c.insurance_title,
      has_sickness_insurance_on_birth_date: c.insured_on_event_date,
      children_count: c.children_count,
      child_age_years: c.child_age_years ?? null,
      foster_family_type: c.foster_family_type,
      foster_deferred_school: c.foster_deferred_school,
      has_za_zyciem_certificate: c.has_za_zyciem,
      gross_monthly_salary: c.gross_monthly_salary,
      custom_benefit_base: c.custom_benefit_base ?? null,
      second_parent_gross_salary: c.second_parent_gross_salary ?? null,
      second_parent_custom_base: c.second_parent_custom_base ?? null,
      payment_variant: c.payment_variant,
      mother_maternity_weeks: c.mother_maternity_weeks ?? null,
      father_takes_parental_weeks: c.father_takes_parental_weeks,
      father_takes_paternity_leave: c.father_takes_paternity_leave,
      employer_insured_count: c.employer_insured_count,
    });
  };

  const populateFormFromResult = (res: PdfAnalysisResult) => {
    const ef = res.extracted_fields;

    if (res.recommended_calculator === "pregnancy_sickness") {
      setTargetMode("pregnancy_sickness");
    } else if (res.recommended_calculator === "maternity_parental") {
      setTargetMode("maternity_parental");
    } else if (res.document_domain === "sickness_general" || res.document_domain === "sickness_pregnancy") {
      setTargetMode("pregnancy_sickness");
    } else {
      setTargetMode("maternity_parental");
    }

    // ZERO ZGADYWANIA: pola nieobecne w dokumencie pozostają PUSTE!
    setConfirmTitle(res.suggested_insurance_title ?? "");
    setConfirmInsuranceStatus(res.sickness_insurance_status ?? "unknown");
    setConfirmGross(
      res.suggested_gross_salary !== undefined && res.suggested_gross_salary !== null
        ? String(res.suggested_gross_salary)
        : ""
    );
    setConfirmCustomBase(
      res.suggested_custom_benefit_base !== undefined && res.suggested_custom_benefit_base !== null
        ? String(res.suggested_custom_benefit_base)
        : ""
    );
    setConfirmEmployerCount(
      ef.employer_insured_count !== undefined && ef.employer_insured_count !== null
        ? String(ef.employer_insured_count)
        : ""
    );
    setConfirmDebt(
      ef.contribution_debt_pln !== undefined && ef.contribution_debt_pln !== null
        ? String(ef.contribution_debt_pln)
        : ""
    );

    // Chorobowy / ciąża
    setConfirmCodeB(ef.has_code_b === true ? "yes" : ef.has_code_b === false ? "no" : "unknown");
    setConfirmInsuranceDays(
      ef.insurance_days !== undefined && ef.insurance_days !== null ? String(ef.insurance_days) : ""
    );
    setConfirmFte(
      ef.fte_fraction !== undefined && ef.fte_fraction !== null ? String(ef.fte_fraction) : ""
    );
    setConfirmSpecialTermination(ef.employment_terminated_special === true);
    setConfirmTerminationReason(ef.termination_reason || "bankruptcy_liquidation");

    // Macierzyński / rodzicielski
    setConfirmScenario((ef.scenario as BenefitScenario | null) ?? "");
    setConfirmChildren(
      ef.children_count !== undefined && ef.children_count !== null ? String(ef.children_count) : ""
    );
    setConfirmVariant((ef.payment_variant as PaymentVariant | null) ?? "");
    setConfirmZaZyciem(ef.has_za_zyciem === true);
    setConfirmPremature(ef.premature_or_hospitalized === true);
    setConfirmStillbirth(ef.stillbirth_or_early_death === true);
    setConfirmCombineWork(ef.combine_parental_with_work === true);
    setConfirmFatherPaternity(ef.father_takes_paternity_leave === true);
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (!fileList || fileList.length === 0) return;
    const files = Array.from(fileList);
    setUploading(true);
    setError(null);
    try {
      if (files.length === 1) {
        const res = await api.analyzePdf(files[0]);
        setCaseResult({ documents: [res], merged: res, conflicts: [] });
        populateFormFromResult(res);
      } else {
        const res = await api.analyzeCase(files);
        setCaseResult(res);
        populateFormFromResult(res.merged);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Błąd analizy dokumentu");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const runConfirmedSimulation = () => {
    if (!pdfResult) return;
    const ef = pdfResult.extracted_fields;

    if (targetMode === "pregnancy_sickness") {
      openInPregnancyCalculator({
        sourceLabel: pdfResult.filename,
        insurance_title: confirmTitle || null,
        has_voluntary_sickness_insurance:
          confirmInsuranceStatus === "denied"
            ? false
            : confirmInsuranceStatus === "confirmed"
            ? true
            : null,
        insurance_days: confirmInsuranceDays.trim() ? Number(confirmInsuranceDays) : null,
        waiting_period_exemption_reason: ef.waiting_period_exemption_reason || "none",
        fte_fraction: confirmFte.trim() ? Number(confirmFte) : null,
        gross_monthly_salary: confirmGross.trim() ? Number(confirmGross) : null,
        custom_benefit_base: confirmCustomBase.trim() ? Number(confirmCustomBase) : null,
        has_code_b: confirmCodeB === "yes" ? true : confirmCodeB === "no" ? false : null,
        employer_insured_count: confirmEmployerCount.trim() ? Number(confirmEmployerCount) : null,
        contribution_debt_pln: confirmDebt.trim() ? Number(confirmDebt) : null,
        employment_terminated_special: confirmSpecialTermination,
        termination_reason: confirmSpecialTermination ? confirmTerminationReason : null,
      });
      return;
    }

    openInCalculator({
      sourceLabel: `Dane z dokumentu: ${pdfResult.filename}`,
      fromPdf: true,
      scenario: confirmScenario || null,
      insurance_title: confirmTitle || null,
      has_sickness_insurance_on_birth_date:
        confirmInsuranceStatus === "confirmed"
          ? true
          : confirmInsuranceStatus === "denied"
          ? false
          : null,
      children_count: confirmChildren.trim()
        ? Math.min(15, Math.max(1, Number(confirmChildren)))
        : null,
      gross_monthly_salary: confirmGross.trim() ? Number(confirmGross) : null,
      custom_benefit_base: confirmCustomBase.trim() ? Number(confirmCustomBase) : null,
      payment_variant: confirmVariant || null,
      employer_insured_count: confirmEmployerCount.trim() ? Number(confirmEmployerCount) : null,
      contribution_debt_pln: confirmDebt.trim() ? Number(confirmDebt) : null,
      has_za_zyciem_certificate: confirmZaZyciem,
      premature_or_hospitalized: confirmPremature,
      gestation_week: ef.gestation_week ?? null,
      birth_weight_grams: ef.birth_weight_grams ?? null,
      stillbirth_or_early_death: confirmStillbirth,
      combine_parental_with_work: confirmCombineWork,
      father_takes_parental_weeks: 0,
      father_takes_paternity_leave: confirmFatherPaternity,
    });
  };

  const statusBadge = (status: PdfAnalysisResult["verification_status"]) => {
    if (status === "verified") {
      return "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/15 dark:text-emerald-300";
    }
    if (status === "denied") {
      return "border-red-200 bg-red-50 text-red-800 dark:border-red-500/30 dark:bg-red-500/15 dark:text-red-300";
    }
    return "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/15 dark:text-amber-300";
  };

  const statusLabel = (status: PdfAnalysisResult["verification_status"]) => {
    if (status === "verified") return "Ubezpieczenie / prawo potwierdzone";
    if (status === "denied") return "Wykryto odmowę / brak ubezpieczenia";
    return "Wymaga weryfikacji użytkownika";
  };

  return (
    <div>
      <PageHeader
        badge="Analiza dokumentów PDF i skanów (OCR)"
        title="Wczytywanie dokumentów ZUS (PDF / skany) i przykłady demonstracyjne"
        description="Prześlij jeden dokument lub cały zestaw sprawy (ZAM, Z-3, Z-3a, ZAS-53, e-ZLA, decyzje i skany ZUS). Parser odczytuje wyłącznie dane faktycznie obecne w pliku — nieodczytane pola pozostają puste do Twojego uzupełnienia."
      />

      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700 dark:border-red-800/60 dark:bg-red-950/40 dark:text-red-300">
          {error}
        </div>
      )}

      <div className="grid gap-8 lg:grid-cols-12">
        {/* Upload 1..N dokumentów + ekran weryfikacji bez zgadywania */}
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs dark:border-emerald-950 dark:bg-[#111c17] lg:col-span-6">
          <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
            Upload dokumentów PDF / skanów (lokalny OCR PL)
          </h2>
          <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
            Obsługiwane są formularze tekstowe, AcroForm, XFA, wielostronicowe skany spraw ZUS
            (lokalny OCR Tesseract PL) oraz obrazy PNG/JPG. Możesz zaznaczyć jeden lub kilka plików
            jednej sprawy jednocześnie.
          </p>

          <label className="mt-4 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 p-6 text-center transition hover:border-[#007834] dark:border-slate-700 dark:bg-[#16241d]">
            <span className="text-sm font-semibold text-[#007834] dark:text-emerald-400">
              {uploading
                ? "Analizowanie dokumentu (dla skanów trwa lokalny OCR)..."
                : "Wybierz plik(i) PDF lub skany PNG/JPG z dysku"}
            </span>
            <span className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Do 10 plików w sprawie • maks. 10 MB / plik
            </span>
            <input
              type="file"
              multiple
              accept="application/pdf,image/png,image/jpeg,image/webp,image/tiff"
              onChange={handleUpload}
              className="hidden"
            />
          </label>

          {pdfResult && (
            <div className="mt-5 space-y-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs dark:border-emerald-950 dark:bg-[#16241d]">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-bold text-slate-900 dark:text-slate-100">{pdfResult.filename}</p>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">
                    {DOMAIN_LABELS[pdfResult.document_domain]}
                    {pdfResult.extracted_fields.ocr_used && (
                      <span className="ml-1.5 rounded bg-sky-100 px-1.5 py-0.5 font-semibold text-sky-800 dark:bg-sky-900/40 dark:text-sky-300">
                        OCR PL ({pdfResult.extracted_fields.ocr_pages_processed}/
                        {pdfResult.extracted_fields.page_count} str.)
                      </span>
                    )}
                  </p>
                </div>
                <span
                  className={`rounded-full border px-2.5 py-0.5 text-[11px] font-bold ${statusBadge(
                    pdfResult.verification_status
                  )}`}
                >
                  {statusLabel(pdfResult.verification_status)}
                </span>
              </div>

              {pdfResult.guidance_banner && (
                <div className="rounded-lg border border-sky-200 bg-sky-50 p-2.5 text-[11px] text-sky-900 dark:border-sky-800/60 dark:bg-sky-950/40 dark:text-sky-200">
                  {pdfResult.guidance_banner}
                </div>
              )}

              {caseResult && caseResult.conflicts.length > 0 && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-2.5 text-[11px] text-red-800 dark:border-red-800/60 dark:bg-red-950/40 dark:text-red-200">
                  <p className="font-bold">Wykryto rozbieżności między dokumentami:</p>
                  <ul className="mt-1 list-disc pl-4">
                    {caseResult.conflicts.map((c, idx) => (
                      <li key={idx}>{c.message}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="space-y-1.5 text-slate-700 dark:text-slate-300">
                <p>
                  <strong>Rozpoznane formularze:</strong>{" "}
                  {pdfResult.detected_forms.length > 0 ? pdfResult.detected_forms.join(", ") : "Brak"}
                </p>

                {Object.keys(pdfResult.extracted_fields.key_extracted_fields || {}).length > 0 && (
                  <div className="mt-2 rounded-lg border border-slate-200 bg-white p-2.5 dark:border-slate-700 dark:bg-[#111c17]">
                    <p className="mb-1 text-[11px] font-bold text-slate-800 dark:text-slate-200">
                      Dane odczytane bezpośrednio z dokumentu:
                    </p>
                    <dl className="grid gap-1 text-[11px]">
                      {Object.entries(pdfResult.extracted_fields.key_extracted_fields).map(
                        ([k, v]) => (
                          <div
                            key={k}
                            className="flex justify-between gap-2 border-b border-slate-100 py-0.5 last:border-0 dark:border-slate-800"
                          >
                            <dt className="text-slate-500 dark:text-slate-400">{k}</dt>
                            <dd className="text-right font-semibold text-slate-900 dark:text-slate-100">
                              {v}
                            </dd>
                          </div>
                        )
                      )}
                    </dl>
                  </div>
                )}

                {pdfResult.missing_fields_for_calculation.length > 0 && (
                  <div className="rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-[11px] text-amber-900 dark:border-amber-800/60 dark:bg-amber-950/40 dark:text-amber-200">
                    <strong>Nie znaleziono w dokumencie (pozostawiono puste):</strong>{" "}
                    {pdfResult.missing_fields_for_calculation.join(", ")}.
                  </div>
                )}

                {pdfResult.notes.map((n, i) => (
                  <p key={i} className="text-[11px] text-slate-500 dark:text-slate-400">
                    • {n}
                  </p>
                ))}
              </div>

              {/* Ekran weryfikacji pól — bez twardych domyślnych wartości */}
              {pdfResult.recommended_calculator !== "info_only" && (
                <div className="space-y-3 border-t border-slate-200 pt-3 dark:border-slate-700">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-bold text-slate-900 dark:text-slate-100">
                      Zweryfikuj odczytane pola i uzupełnij braki:
                    </p>
                    <div className="flex gap-1">
                      <button
                        type="button"
                        onClick={() => setTargetMode("pregnancy_sickness")}
                        className={`rounded px-2 py-1 text-[11px] font-semibold ${
                          targetMode === "pregnancy_sickness"
                            ? "bg-[#007834] text-white"
                            : "border border-slate-300 bg-white text-slate-700 dark:border-slate-700 dark:bg-[#111c17] dark:text-slate-300"
                        }`}
                      >
                        Chorobowy / Ciąża
                      </button>
                      <button
                        type="button"
                        onClick={() => setTargetMode("maternity_parental")}
                        className={`rounded px-2 py-1 text-[11px] font-semibold ${
                          targetMode === "maternity_parental"
                            ? "bg-[#007834] text-white"
                            : "border border-slate-300 bg-white text-slate-700 dark:border-slate-700 dark:bg-[#111c17] dark:text-slate-300"
                        }`}
                      >
                        Macierzyński / Rodzicielski
                      </button>
                    </div>
                  </div>

                  <div className="grid gap-2.5 sm:grid-cols-2">
                    <div>
                      <label className="block text-[11px] font-semibold">
                        Tytuł ubezpieczenia
                        {!confirmTitle && (
                          <span className="ml-1 text-amber-600 dark:text-amber-400">(brak w dok.)</span>
                        )}
                      </label>
                      <select
                        value={confirmTitle}
                        onChange={(e) => setConfirmTitle(e.target.value as InsuranceTitle | "")}
                        className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                      >
                        <option value="">— Nie odczytano (wybierz) —</option>
                        <option value="uop">Umowa o pracę</option>
                        <option value="zlecenie">Umowa zlecenie</option>
                        <option value="jdg">JDG / osoba współpracująca</option>
                        <option value="none">Brak ubezpieczenia</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold">
                        Status ubezpieczenia chorobowego
                      </label>
                      <select
                        value={confirmInsuranceStatus}
                        onChange={(e) =>
                          setConfirmInsuranceStatus(e.target.value as SicknessInsuranceStatus)
                        }
                        className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                      >
                        <option value="unknown">— Nie odczytano —</option>
                        <option value="confirmed">Potwierdzone (podlega)</option>
                        <option value="denied">Brak / odmowa</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold">
                        Wynagrodzenie brutto (zł)
                        {!confirmGross && (
                          <span className="ml-1 text-amber-600 dark:text-amber-400">(puste)</span>
                        )}
                      </label>
                      <input
                        type="number"
                        min={0}
                        step="any"
                        placeholder="Brak w dokumencie — wpisz"
                        value={confirmGross}
                        onChange={(e) => {
                          setConfirmGross(e.target.value);
                          setConfirmCustomBase("");
                        }}
                        className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold">
                        Podstawa wymiaru netto (opcjonalnie)
                      </label>
                      <input
                        type="number"
                        min={0}
                        step="any"
                        placeholder="Pozostaw puste lub wpisz"
                        value={confirmCustomBase}
                        onChange={(e) => setConfirmCustomBase(e.target.value)}
                        className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold">
                        Ubezpieczeni u płatnika
                      </label>
                      <input
                        type="number"
                        min={0}
                        placeholder="Brak w dokumencie"
                        value={confirmEmployerCount}
                        onChange={(e) => setConfirmEmployerCount(e.target.value)}
                        className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                      />
                    </div>

                    {targetMode === "pregnancy_sickness" ? (
                      <>
                        <div>
                          <label className="block text-[11px] font-semibold">
                            Kod literowy „B” (ciąża = 100%)
                          </label>
                          <select
                            value={confirmCodeB}
                            onChange={(e) => setConfirmCodeB(e.target.value as TriBool)}
                            className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                          >
                            <option value="unknown">— Nie odczytano —</option>
                            <option value="no">Nie (zwykłe L4 — 80%)</option>
                            <option value="yes">Tak (ciąża / kod B — 100%)</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-[11px] font-semibold">
                            Okres ubezpieczenia (dni)
                          </label>
                          <input
                            type="number"
                            min={0}
                            placeholder="Brak w dokumencie"
                            value={confirmInsuranceDays}
                            onChange={(e) => setConfirmInsuranceDays(e.target.value)}
                            className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                          />
                        </div>
                        <div>
                          <label className="block text-[11px] font-semibold">
                            Zaległość ZUS (zł, jeśli JDG)
                          </label>
                          <input
                            type="number"
                            min={0}
                            step="any"
                            placeholder="Brak w dokumencie"
                            value={confirmDebt}
                            onChange={(e) => setConfirmDebt(e.target.value)}
                            className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                          />
                        </div>
                      </>
                    ) : (
                      <>
                        <div>
                          <label className="block text-[11px] font-semibold">Scenariusz</label>
                          <select
                            value={confirmScenario}
                            onChange={(e) =>
                              setConfirmScenario(e.target.value as BenefitScenario | "")
                            }
                            className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                          >
                            <option value="">— Nie odczytano —</option>
                            <option value="birth">Poród</option>
                            <option value="adoption">Adopcja</option>
                            <option value="foster">Rodzina zastępcza</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-[11px] font-semibold">Liczba dzieci</label>
                          <input
                            type="number"
                            min={1}
                            max={15}
                            placeholder="Brak w dokumencie"
                            value={confirmChildren}
                            onChange={(e) => setConfirmChildren(e.target.value)}
                            className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                          />
                        </div>
                        <div>
                          <label className="block text-[11px] font-semibold">Wariant wypłaty</label>
                          <select
                            value={confirmVariant}
                            onChange={(e) =>
                              setConfirmVariant(e.target.value as PaymentVariant | "")
                            }
                            className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                          >
                            <option value="">— Nie odczytano —</option>
                            <option value="81_5">Wariant 81,5%</option>
                            <option value="100_70">Wariant 100% / 70%</option>
                          </select>
                        </div>
                      </>
                    )}
                  </div>

                  {targetMode === "maternity_parental" && (
                    <div className="flex flex-wrap gap-3 text-[11px]">
                      <label className="flex items-center gap-1.5">
                        <input
                          type="checkbox"
                          checked={confirmZaZyciem}
                          onChange={(e) => setConfirmZaZyciem(e.target.checked)}
                          className="h-4 w-4 accent-[#007834]"
                        />
                        „Za życiem”
                      </label>
                      <label className="flex items-center gap-1.5">
                        <input
                          type="checkbox"
                          checked={confirmPremature}
                          onChange={(e) => setConfirmPremature(e.target.checked)}
                          className="h-4 w-4 accent-[#007834]"
                        />
                        Wcześniak / szpital
                      </label>
                      <label className="flex items-center gap-1.5">
                        <input
                          type="checkbox"
                          checked={confirmStillbirth}
                          onChange={(e) => setConfirmStillbirth(e.target.checked)}
                          className="h-4 w-4 accent-[#007834]"
                        />
                        Martwe urodzenie
                      </label>
                      <label className="flex items-center gap-1.5">
                        <input
                          type="checkbox"
                          checked={confirmCombineWork}
                          onChange={(e) => setConfirmCombineWork(e.target.checked)}
                          className="h-4 w-4 accent-[#007834]"
                        />
                        Łączenie z pracą
                      </label>
                      <label className="flex items-center gap-1.5">
                        <input
                          type="checkbox"
                          checked={confirmFatherPaternity}
                          onChange={(e) => setConfirmFatherPaternity(e.target.checked)}
                          className="h-4 w-4 accent-[#007834]"
                        />
                        Urlop ojcowski
                      </label>
                    </div>
                  )}

                  <button
                    type="button"
                    onClick={runConfirmedSimulation}
                    className="w-full rounded-lg bg-[#007834] px-3 py-2 text-xs font-semibold text-white transition hover:bg-[#005a27]"
                  >
                    {targetMode === "pregnancy_sickness"
                      ? "Przekaż zweryfikowane dane do kalkulatora chorobowego / ciąży"
                      : "Przekaż zweryfikowane dane do kalkulatora macierzyńskiego"}
                  </button>
                </div>
              )}

              <pre className="max-h-36 overflow-auto rounded bg-white p-2 text-[11px] text-slate-600 dark:bg-[#111c17] dark:text-slate-400">
                {pdfResult.extracted_text_preview}
              </pre>
            </div>
          )}
        </section>

        {/* Przykłady demonstracyjne */}
        <section className="space-y-4 lg:col-span-6">
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs dark:border-emerald-950 dark:bg-[#111c17]">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
              Przykłady demonstracyjne (weryfikowane z silnikiem wyliczeń)
            </h2>
            <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
              Wybierz przykład, aby sprawdzić prawo do świadczenia, indywidualną podstawę wymiaru i
              łączną kwotę zasiłku.
            </p>

            <div className="mt-4 space-y-3">
              {cases.map((c) => (
                <div
                  key={c.case_id}
                  className="flex flex-col justify-between gap-3 rounded-lg border border-slate-200 p-4 dark:border-emerald-950 sm:flex-row sm:items-center"
                >
                  <div>
                    <p className="text-sm font-bold text-slate-900 dark:text-slate-100">{c.title}</p>
                    <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">{c.description}</p>
                    <p className="mt-1 text-[11px] font-medium text-[#005a27] dark:text-emerald-300">
                      Oczekiwany wynik: {c.expected_decision}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => runSampleCase(c)}
                    className="shrink-0 rounded-lg bg-[#007834] px-3 py-2 text-xs font-semibold text-white transition hover:bg-[#005a27]"
                  >
                    Przetestuj w kalkulatorze
                  </button>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
