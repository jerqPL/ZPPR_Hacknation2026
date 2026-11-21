"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/PageHeader";
import { api } from "@/lib/api";
import type {
  BenefitScenario,
  InsuranceTitle,
  PaymentVariant,
  PdfAnalysisResult,
  SampleCase,
} from "@/lib/types";

const PREFILL_STORAGE_KEY = "zppr-prefill-calculator";

export default function SampleCasesPdfPage() {
  const router = useRouter();
  const [cases, setCases] = useState<SampleCase[]>([]);
  const [pdfResult, setPdfResult] = useState<PdfAnalysisResult | null>(null);

  // Potwierdzane przez użytkownika pola z PDF (zamiast twardych domyślnych wartości)
  const [confirmTitle, setConfirmTitle] = useState<InsuranceTitle>("uop");
  const [confirmInsured, setConfirmInsured] = useState(false);
  const [confirmScenario, setConfirmScenario] = useState<BenefitScenario>("birth");
  const [confirmChildren, setConfirmChildren] = useState(1);
  const [confirmVariant, setConfirmVariant] = useState<PaymentVariant>("81_5");
  const [confirmEmployerCount, setConfirmEmployerCount] = useState(25);
  const [confirmGross, setConfirmGross] = useState(7000);
  const [confirmCustomBase, setConfirmCustomBase] = useState<string>("");

  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getSampleCases().then(setCases).catch((e) => setError(String(e)));
  }, []);

  const openInCalculator = (prefill: Record<string, unknown>) => {
    sessionStorage.setItem(PREFILL_STORAGE_KEY, JSON.stringify(prefill));
    router.push("/kalkulator");
  };

  const runSampleCase = (c: SampleCase) => {
    openInCalculator({
      sourceLabel: c.title,
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

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const res = await api.analyzePdf(file);
      setPdfResult(res);
      setConfirmTitle(res.suggested_insurance_title);
      setConfirmInsured(res.verification_status === "verified");
      setConfirmChildren(Math.min(15, Math.max(1, res.extracted_fields.children_count || 1)));
      setConfirmEmployerCount(res.extracted_fields.employer_insured_count ?? 25);
      setConfirmGross(res.suggested_gross_salary ?? 7000);
      setConfirmCustomBase(
        res.suggested_custom_benefit_base ? String(res.suggested_custom_benefit_base) : ""
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Błąd analizy pliku PDF");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const runConfirmedPdfSimulation = () => {
    if (!pdfResult) return;
    openInCalculator({
      sourceLabel: `Dane z PDF: ${pdfResult.filename}`,
      scenario: confirmScenario,
      insurance_title: confirmTitle,
      has_sickness_insurance_on_birth_date: confirmInsured,
      children_count: Math.min(15, Math.max(1, Number(confirmChildren) || 1)),
      gross_monthly_salary: Number(confirmGross),
      custom_benefit_base: confirmCustomBase.trim() ? Number(confirmCustomBase) : null,
      payment_variant: confirmVariant,
      employer_insured_count: Number(confirmEmployerCount),
      father_takes_parental_weeks: 0,
      father_takes_paternity_leave: false,
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
    if (status === "verified") return "Ubezpieczenie potwierdzone";
    if (status === "denied") return "Wykryto brak ubezpieczenia / odmowę";
    return "Wymaga weryfikacji użytkownika";
  };

  return (
    <div>
      <PageHeader
        badge="Analiza wniosków PDF"
        title="Weryfikacja wniosków PDF i przykłady demonstracyjne"
        description="Prześlij formularz ZUS w formacie PDF (ZAM, Z-3, Z-3a, poświadczenie ubezpieczenia), zweryfikuj odczytane pola przed symulacją lub przetestuj wbudowane przykłady demonstracyjne."
      />

      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700 dark:border-red-800/60 dark:bg-red-950/40 dark:text-red-300">
          {error}
        </div>
      )}

      <div className="grid gap-8 lg:grid-cols-12">
        {/* Upload PDF + ekran potwierdzenia pól */}
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs dark:border-emerald-950 dark:bg-[#111c17] lg:col-span-5">
          <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
            Upload wniosku PDF i weryfikacja pól
          </h2>
          <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
            Parser rozpoznaje formularze Z-3, Z-3a, ZAM, ZAS-53, e-ZLA oraz poświadczenia
            ubezpieczenia. Jeśli dokument jest skanem lub dane są niejednoznaczne, wymaga
            potwierdzenia przed wyliczeniem.
          </p>

          <label className="mt-4 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 p-6 text-center transition hover:border-[#007834] dark:border-slate-700 dark:bg-[#16241d]">
            <span className="text-sm font-semibold text-[#007834] dark:text-emerald-400">
              {uploading ? "Analizowanie PDF..." : "Wybierz plik PDF z dysku"}
            </span>
            <span className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Maksymalny rozmiar: 10 MB
            </span>
            <input
              type="file"
              accept="application/pdf"
              onChange={handleUpload}
              className="hidden"
            />
          </label>

          {pdfResult && (
            <div className="mt-5 space-y-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs dark:border-emerald-950 dark:bg-[#16241d]">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-bold text-slate-900 dark:text-slate-100">{pdfResult.filename}</p>
                <span
                  className={`rounded-full border px-2.5 py-0.5 text-[11px] font-bold ${statusBadge(
                    pdfResult.verification_status
                  )}`}
                >
                  {statusLabel(pdfResult.verification_status)}
                </span>
              </div>

              <div className="space-y-1.5 text-slate-700 dark:text-slate-300">
                <p>
                  <strong>Rozpoznane formularze:</strong>{" "}
                  {pdfResult.detected_forms.length > 0 ? pdfResult.detected_forms.join(", ") : "Brak"}
                </p>
                {pdfResult.extracted_fields.form_description && (
                  <p className="text-[11px] font-medium text-[#005a27] dark:text-emerald-300">
                    {pdfResult.extracted_fields.form_description}
                  </p>
                )}
                {pdfResult.extracted_fields.filled_form_fields_count > 0 && (
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">
                    Odczytano <strong>{pdfResult.extracted_fields.filled_form_fields_count}</strong>{" "}
                    wypełnionych pól formularza PDF (AcroForm/XFA).
                  </p>
                )}
                {Object.keys(pdfResult.extracted_fields.key_extracted_fields || {}).length > 0 && (
                  <div className="mt-2 rounded-lg border border-slate-200 bg-white p-2.5 dark:border-slate-700 dark:bg-[#111c17]">
                    <p className="mb-1 text-[11px] font-bold text-slate-800 dark:text-slate-200">
                      Kluczowe dane odczytane z dokumentu:
                    </p>
                    <dl className="grid gap-1 text-[11px]">
                      {Object.entries(pdfResult.extracted_fields.key_extracted_fields).map(
                        ([k, v]) => (
                          <div key={k} className="flex justify-between gap-2 border-b border-slate-100 py-0.5 last:border-0 dark:border-slate-800">
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
                {pdfResult.extracted_fields.insurance_periods.length > 0 && (
                  <p>
                    <strong>Wykryte daty:</strong>{" "}
                    {pdfResult.extracted_fields.insurance_periods.join(", ")}
                  </p>
                )}
                {pdfResult.notes.map((n, i) => (
                  <p key={i} className="text-[11px] text-slate-500 dark:text-slate-400">
                    • {n}
                  </p>
                ))}
              </div>

              {/* Potwierdzenie i korekta pól przed symulacją */}
              <div className="space-y-2.5 border-t border-slate-200 pt-3 dark:border-slate-700">
                <p className="font-bold text-slate-900 dark:text-slate-100">
                  Potwierdź lub skoryguj dane z dokumentu:
                </p>
                <div className="grid gap-2 sm:grid-cols-2">
                  <div>
                    <label className="block text-[11px] font-semibold">Tytuł ubezpieczenia</label>
                    <select
                      value={confirmTitle}
                      onChange={(e) => setConfirmTitle(e.target.value as InsuranceTitle)}
                      className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                    >
                      <option value="uop">Umowa o pracę</option>
                      <option value="zlecenie">Umowa zlecenie</option>
                      <option value="jdg">JDG</option>
                      <option value="none">Brak ubezpieczenia</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold">Scenariusz</label>
                    <select
                      value={confirmScenario}
                      onChange={(e) => setConfirmScenario(e.target.value as BenefitScenario)}
                      className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                    >
                      <option value="birth">Poród</option>
                      <option value="adoption">Adopcja</option>
                      <option value="foster">Rodzina zastępcza</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold">Brutto (zł)</label>
                    <input
                      type="number"
                      min={0}
                      step="any"
                      value={confirmGross}
                      onChange={(e) => {
                        setConfirmGross(Number(e.target.value));
                        setConfirmCustomBase("");
                      }}
                      className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold">
                      Podstawa netto (opcjonalnie)
                    </label>
                    <input
                      type="number"
                      min={0}
                      step="any"
                      value={confirmCustomBase}
                      onChange={(e) => setConfirmCustomBase(e.target.value)}
                      className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold">Liczba dzieci</label>
                    <input
                      type="number"
                      min={1}
                      max={15}
                      value={confirmChildren}
                      onChange={(e) => setConfirmChildren(Number(e.target.value))}
                      className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold">Ubezpieczeni u płatnika</label>
                    <input
                      type="number"
                      min={0}
                      value={confirmEmployerCount}
                      onChange={(e) => setConfirmEmployerCount(Number(e.target.value))}
                      className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-xs dark:border-slate-700"
                    />
                  </div>
                </div>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <label className="flex items-center gap-1.5 text-[11px] font-semibold">
                    <input
                      type="checkbox"
                      checked={confirmInsured}
                      onChange={(e) => setConfirmInsured(e.target.checked)}
                      className="h-4 w-4 shrink-0 accent-[#007834]"
                    />
                    Potwierdzam podleganie ubezpieczeniu chorobowemu
                  </label>
                  <select
                    value={confirmVariant}
                    onChange={(e) => setConfirmVariant(e.target.value as PaymentVariant)}
                    className="rounded border border-slate-300 px-2 py-1 text-[11px] dark:border-slate-700"
                  >
                    <option value="81_5">Wariant 81,5%</option>
                    <option value="100_70">Wariant 100% / 70%</option>
                  </select>
                </div>

                <button
                  type="button"
                  onClick={runConfirmedPdfSimulation}
                  className="w-full rounded-lg bg-[#007834] px-3 py-2 text-xs font-semibold text-white transition hover:bg-[#005a27]"
                >
                  Przelicz potwierdzone dane w kalkulatorze
                </button>
              </div>

              <pre className="max-h-32 overflow-auto rounded bg-white p-2 text-[11px] text-slate-600 dark:bg-[#111c17] dark:text-slate-400">
                {pdfResult.extracted_text_preview}
              </pre>
            </div>
          )}
        </section>

        {/* Przykłady demonstracyjne */}
        <section className="space-y-4 lg:col-span-7">
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
