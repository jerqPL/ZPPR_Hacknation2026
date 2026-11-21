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
        scenario: c.scenario || "birth",
        insurance_title: c.insurance_title,
        has_sickness_insurance_on_birth_date: c.insured_on_event_date,
        children_count: c.children_count,
        child_age_years: (c.scenario || "birth") === "birth" ? null : (c.child_age_years ?? 3),
        foster_family_type: c.foster_family_type || "non_professional",
        foster_deferred_school: Boolean(c.foster_deferred_school),
        has_za_zyciem_certificate: c.has_za_zyciem,
        gross_monthly_salary: c.gross_monthly_salary,
        custom_benefit_base: c.custom_benefit_base ?? null,
        second_parent_gross_salary: c.second_parent_gross_salary ?? c.gross_monthly_salary,
        second_parent_custom_base: c.second_parent_custom_base ?? null,
        payment_variant: c.payment_variant,
        employer_insured_count: c.employer_insured_count,
        mother_maternity_weeks: c.mother_maternity_weeks ?? null,
        father_takes_parental_weeks: c.father_takes_parental_weeks ?? 9,
        father_takes_paternity_leave: Boolean(c.father_takes_paternity_leave),
      });
      setSelectedCalc({ caseItem: c, calc });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Błąd wyliczenia sprawy");
    }
  };

  const runPdfSimulation = async (pdf: PdfAnalysisResult) => {
    setError(null);
    try {
      const gross = pdf.suggested_gross_salary || 7000;
      const customBase = pdf.suggested_custom_benefit_base || null;
      const calc = await api.calculateIntegrated({
        scenario: "birth",
        insurance_title: pdf.suggested_insurance_title,
        has_sickness_insurance_on_birth_date: pdf.insurance_verified,
        children_count: 1,
        gross_monthly_salary: gross,
        custom_benefit_base: customBase,
        payment_variant: "81_5",
        employer_insured_count: 25,
        father_takes_parental_weeks: 9,
        father_takes_paternity_leave: true,
      });
      setSelectedCalc({
        caseItem: {
          case_id: "pdf_upload",
          title: `Sprawa z pliku PDF: ${pdf.filename}`,
          description: `Wykryte formularze: ${pdf.detected_forms.join(", ") || "brak"}`,
          scenario: "birth",
          insurance_title: pdf.suggested_insurance_title,
          insured_on_event_date: pdf.insurance_verified,
          expected_decision: pdf.insurance_verified
            ? "PRZYZNANO (na podstawie danych z dokumentu PDF)"
            : "ODMOWA (brak potwierdzenia ubezpieczenia chorobowego w PDF)",
          gross_monthly_salary: gross,
          custom_benefit_base: customBase,
          children_count: 1,
          payment_variant: "81_5",
          has_za_zyciem: false,
          employer_insured_count: 25,
          notes: pdf.notes.join(" "),
        },
        calc,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Błąd symulacji z pliku PDF");
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
        badge="Analiza wniosków PDF"
        title="Weryfikacja wniosków PDF i symulacja spraw z zestawów ZUS"
        description="Prześlij formularz ZUS w formacie PDF (np. ZAM, Z-3, Z-3a, poświadczenie ubezpieczenia) lub przetestuj jedną z wbudowanych spraw konkursowych z indywidualną podstawą wymiaru zasiłku."
      />

      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 dark:border-red-800/60 dark:bg-red-950/40 p-3 text-xs text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      <div className="grid gap-8 lg:grid-cols-12">
        {/* Upload PDF */}
        <section className="rounded-xl border border-slate-200 dark:border-emerald-950 bg-white dark:bg-[#111c17] p-6 shadow-xs lg:col-span-5">
          <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">Upload wniosku PDF</h2>
          <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
            Parser automatycznie wykrywa kody formularzy ZUS (ZAM, Z-3, Z-3a, ZAS-53, e-ZLA),
            weryfikuje ubezpieczenie oraz wylicza indywidualną podstawę wymiaru zasiłku z wykrytych
            kwot.
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
                      ? "font-semibold text-emerald-700 dark:text-emerald-400"
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
                  <strong>Wykryty przeciętny przychód brutto:</strong>{" "}
                  {pdfResult.suggested_gross_salary.toFixed(2)} zł
                </p>
              )}
              {pdfResult.suggested_custom_benefit_base && (
                <p className="font-semibold text-[#005a27] dark:text-emerald-300">
                  <strong>Wyliczona indywidualna podstawa wymiaru (-13,71%):</strong>{" "}
                  {pdfResult.suggested_custom_benefit_base.toFixed(2)} zł
                </p>
              )}
              <button
                type="button"
                onClick={() => runPdfSimulation(pdfResult)}
                className="mt-2 w-full rounded-lg bg-[#007834] px-3 py-2 text-xs font-semibold text-white hover:bg-[#005a27]"
              >
                Symuluj zasiłek na podstawie tego pliku PDF
              </button>
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
              Zestawy testowe spraw ZUS (w tym indywidualna podstawa wymiaru, adopcja i rodzina zastępcza)
            </h2>
            <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
              Wybierz sprawę z zestawu, aby zweryfikować prawo do świadczenia, indywidualną podstawę
              wymiaru zasiłku oraz harmonogram wypłat w silniku kalkulatora.
            </p>

            <div className="mt-4 space-y-3">
              {cases.map((c) => (
                <div
                  key={c.case_id}
                  className="flex flex-col justify-between gap-3 rounded-lg border border-slate-200 dark:border-emerald-950 p-4 sm:flex-row sm:items-center"
                >
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded bg-slate-100 dark:bg-[#16241d] px-2 py-0.5 text-[10px] font-bold uppercase text-slate-700 dark:text-slate-300">
                        {c.scenario === "adoption"
                          ? "Adopcja"
                          : c.scenario === "foster"
                          ? "Rodzina zastępcza"
                          : "Poród"}
                      </span>
                      {c.custom_benefit_base && (
                        <span className="rounded bg-[#e6f4ec] dark:bg-[#007834]/20 px-2 py-0.5 text-[10px] font-bold text-[#005a27] dark:text-emerald-300">
                          Indywidualna podstawa: {c.custom_benefit_base.toFixed(2)} zł
                        </span>
                      )}
                    </div>
                    <p className="mt-1.5 text-sm font-bold text-slate-900 dark:text-slate-100">{c.title}</p>
                    <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">{c.description}</p>
                    {c.benefit_base_details && (
                      <p className="mt-1 text-[11px] text-slate-700 dark:text-slate-300">
                        <strong>Podstawa wymiaru:</strong> {c.benefit_base_details}
                      </p>
                    )}
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
            <div className="rounded-xl border border-[#007834]/30 bg-[#e6f4ec]/50 dark:bg-[#007834]/20 p-5 text-xs">
              <p className="font-bold text-slate-900 dark:text-slate-100">
                Wynik symulacji dla: {selectedCalc.caseItem.title}
              </p>
              {selectedCalc.calc.eligible ? (
                <>
                  <div className="mt-2 grid gap-2 sm:grid-cols-3">
                    <div className="rounded bg-white dark:bg-[#111c17] p-3">
                      <span className="text-slate-500 dark:text-slate-400">Łączny wymiar</span>
                      <p className="text-base font-bold text-[#005a27] dark:text-emerald-300">
                        {selectedCalc.calc.total_weeks} tyg.
                      </p>
                    </div>
                    <div className="rounded bg-white dark:bg-[#111c17] p-3">
                      <span className="text-slate-500 dark:text-slate-400">Indywidualna podstawa wymiaru</span>
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
                  {selectedCalc.calc.benefit_base_explanation && (
                    <p className="mt-2 rounded bg-white dark:bg-[#111c17] p-2.5 text-slate-700 dark:text-slate-300">
                      <strong>Wyjaśnienie podstawy wymiaru:</strong>{" "}
                      {selectedCalc.calc.benefit_base_explanation}
                    </p>
                  )}
                  <div className="mt-3 overflow-x-auto rounded bg-white dark:bg-[#111c17] p-2">
                    <table className="w-full border-collapse text-left text-[11px]">
                      <thead>
                        <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400">
                          <th className="p-1.5">Świadczenie / urlop</th>
                          <th className="p-1.5">Rodzic</th>
                          <th className="p-1.5 text-right">Tyg.</th>
                          <th className="p-1.5 text-right">Stawka</th>
                          <th className="p-1.5 text-right">Miesięcznie</th>
                          <th className="p-1.5 text-right">Razem brutto</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedCalc.calc.breakdown.map((b, i) => (
                          <tr key={i} className="border-b border-slate-100 dark:border-slate-800">
                            <td className="p-1.5 font-medium text-slate-900 dark:text-slate-100">{b.label}</td>
                            <td className="p-1.5">{b.parent}</td>
                            <td className="p-1.5 text-right font-semibold">{b.weeks}</td>
                            <td className="p-1.5 text-right">{b.rate_percent}%</td>
                            <td className="p-1.5 text-right">{b.monthly_gross_pln.toFixed(2)} zł</td>
                            <td className="p-1.5 text-right font-semibold text-[#005a27] dark:text-emerald-300">
                              {b.total_gross_pln.toFixed(2)} zł
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
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
