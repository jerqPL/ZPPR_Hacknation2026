"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { api } from "@/lib/api";
import type { IntegratedCalculatorResponse, PdfAnalysisResult, SampleCase } from "@/lib/types";

export default function SampleCasesPdfPage() {
  const [cases, setCases] = useState<SampleCase[]>([]);
  const [selectedCalc, setSelectedCalc] = useState<{
    caseItem: SampleCase;
    calc: IntegratedCalculatorResponse;
  } | null>(null);
  const [pdfResult, setPdfResult] = useState<PdfAnalysisResult | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getSampleCases().then(setCases).catch((e) => setError(String(e)));
  }, []);

  const runSampleCase = async (c: SampleCase) => {
    setError(null);
    try {
      const calc = await api.calculateIntegrated({
        scenario: "birth",
        insurance_title: c.insurance_title,
        has_sickness_insurance_on_birth_date: c.insured_on_event_date,
        children_count: c.children_count,
        has_za_zyciem_certificate: c.has_za_zyciem,
        gross_monthly_salary: c.gross_monthly_salary,
        payment_variant: c.payment_variant,
        employer_insured_count: c.employer_insured_count,
        father_takes_parental_weeks: 9,
        father_takes_paternity_leave: false,
      });
      setSelectedCalc({ caseItem: c, calc });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Błąd wyliczenia sprawy");
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const res = await api.analyzePdf(file);
      setPdfResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Błąd analizy pliku PDF");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <PageHeader
        badge="Moduł 3 • Walidacja i testy"
        title="Weryfikacja wniosków PDF i przykładowych spraw ZUS"
        description="Prześlij formularz ZUS w formacie PDF (np. ZAM, Z-3, Z-3a, poświadczenie ubezpieczenia) lub przetestuj jedną z wbudowanych przykładowych spraw konkursowych."
      />

      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 dark:border-red-800/60 dark:bg-red-950/40 p-3 text-xs text-red-700">
          {error}
        </div>
      )}

      <div className="grid gap-8 lg:grid-cols-12">
        {/* Upload PDF */}
        <section className="rounded-xl border border-slate-200 dark:border-emerald-950 bg-white dark:bg-[#111c17] p-6 shadow-xs lg:col-span-5">
          <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">Upload wniosku PDF</h2>
          <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
            Parser automatycznie wykrywa kody formularzy ZUS (ZAM, Z-3, Z-3a, ZAS-53, e-ZLA) oraz
            weryfikuje warstwę tekstową dokumentu.
          </p>

          <label className="mt-4 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-[#16241d] p-6 text-center transition hover:border-[#007834]">
            <span className="text-sm font-semibold text-[#007834] dark:text-emerald-400">
              {uploading ? "Analizowanie PDF..." : "Wybierz plik PDF z dysku"}
            </span>
            <span className="mt-1 text-xs text-slate-500 dark:text-slate-400">Maksymalny rozmiar: 10 MB</span>
            <input
              type="file"
              accept="application/pdf"
              onChange={handleUpload}
              className="hidden"
            />
          </label>

          {pdfResult && (
            <div className="mt-5 space-y-2 rounded-lg border border-slate-200 dark:border-emerald-950 bg-slate-50 dark:bg-[#16241d] p-4 text-xs">
              <p className="font-bold text-slate-900 dark:text-slate-100">Wynik analizy: {pdfResult.filename}</p>
              <p>
                <strong>Wykryte formularze:</strong>{" "}
                {pdfResult.detected_forms.length > 0
                  ? pdfResult.detected_forms.join(", ")
                  : "Brak"}
              </p>
              <p>
                <strong>Status ubezpieczenia (heurystyka):</strong>{" "}
                <span
                  className={
                    pdfResult.insurance_verified
                      ? "font-semibold text-emerald-700"
                      : "font-semibold text-red-700"
                  }
                >
                  {pdfResult.insurance_verified ? "Potwierdzono" : "Wymaga weryfikacji / brak"}
                </span>
              </p>
              <p>
                <strong>Sugerowany tytuł:</strong> {pdfResult.suggested_insurance_title.toUpperCase()}
              </p>
              {pdfResult.suggested_gross_salary && (
                <p>
                  <strong>Wykryta kwota:</strong> {pdfResult.suggested_gross_salary.toFixed(2)} zł
                </p>
              )}
              <pre className="mt-2 max-h-40 overflow-auto rounded bg-white dark:bg-[#111c17] p-2 text-[11px] text-slate-600 dark:text-slate-400">
                {pdfResult.extracted_text_preview}
              </pre>
            </div>
          )}
        </section>

        {/* Przykładowe sprawy */}
        <section className="space-y-4 lg:col-span-7">
          <div className="rounded-xl border border-slate-200 dark:border-emerald-950 bg-white dark:bg-[#111c17] p-6 shadow-xs">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
              Przykładowe zestawy testowe (sprawy ZUS)
            </h2>
            <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
              Wybierz sprawę, aby zweryfikować prawo do świadczenia i przeliczyć wysokość zasiłku w
              silniku kalkulatora.
            </p>

            <div className="mt-4 space-y-3">
              {cases.map((c) => (
                <div
                  key={c.case_id}
                  className="flex flex-col justify-between gap-3 rounded-lg border border-slate-200 dark:border-emerald-950 p-4 sm:flex-row sm:items-center"
                >
                  <div>
                    <p className="text-sm font-bold text-slate-900 dark:text-slate-100">{c.title}</p>
                    <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">{c.description}</p>
                    <p className="mt-1 text-[11px] font-medium text-[#005a27] dark:text-emerald-300">
                      Oczekiwana decyzja: {c.expected_decision}
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

          {selectedCalc && (
            <div className="rounded-xl border border-[#007834]/30 bg-[#e6f4ec] dark:bg-[#007834]/20/50 p-5 text-xs">
              <p className="font-bold text-slate-900 dark:text-slate-100">
                Wynik symulacji dla: {selectedCalc.caseItem.title}
              </p>
              {selectedCalc.calc.eligible ? (
                <div className="mt-2 grid gap-2 sm:grid-cols-3">
                  <div className="rounded bg-white dark:bg-[#111c17] p-3">
                    <span className="text-slate-500 dark:text-slate-400">Łączny wymiar</span>
                    <p className="text-base font-bold text-[#005a27] dark:text-emerald-300">
                      {selectedCalc.calc.total_weeks} tyg.
                    </p>
                  </div>
                  <div className="rounded bg-white dark:bg-[#111c17] p-3">
                    <span className="text-slate-500 dark:text-slate-400">Podstawa wymiaru</span>
                    <p className="text-base font-bold text-slate-900 dark:text-slate-100">
                      {selectedCalc.calc.benefit_base_parent1.toFixed(2)} zł
                    </p>
                  </div>
                  <div className="rounded bg-white dark:bg-[#111c17] p-3">
                    <span className="text-slate-500 dark:text-slate-400">Suma brutto</span>
                    <p className="text-base font-bold text-slate-900 dark:text-slate-100">
                      {selectedCalc.calc.total_estimated_gross_pln.toLocaleString("pl-PL")} zł
                    </p>
                  </div>
                </div>
              ) : (
                <p className="mt-2 font-semibold text-red-700">
                  ODMOWA: {selectedCalc.calc.ineligibility_reason}
                </p>
              )}
              <p className="mt-2 text-slate-700 dark:text-slate-300">
                <strong>Płatnik:</strong> {selectedCalc.calc.payer}
              </p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
