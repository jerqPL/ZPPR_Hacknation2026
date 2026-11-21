"use client";

import { useEffect, useMemo, useState } from "react";
import { Download, Printer } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { useUser } from "@/components/UserContext";
import { api } from "@/lib/api";
import type {
  ApplicationSubmissionResponse,
  DocumentGuidanceResponse,
  InsuranceTitle,
  PaymentVariant,
} from "@/lib/types";

export default function DocumentsPage() {
  const { user } = useUser();

  const [insuranceTitle, setInsuranceTitle] = useState<InsuranceTitle>(
    user?.insurance_title || "uop"
  );
  const [employerCount, setEmployerCount] = useState(user?.employer_insured_count ?? 25);
  const [guidance, setGuidance] = useState<DocumentGuidanceResponse | null>(null);

  // Rozbudowany kreator wniosków
  const [appType, setAppType] = useState("leave_employer");
  const [applicantName, setApplicantName] = useState(user?.full_name || "Anna Kowalska");
  const [childBirthDate, setChildBirthDate] = useState("2026-11-20");
  const [leaveStartDate, setLeaveStartDate] = useState("2026-11-20");
  const [leaveEndDate, setLeaveEndDate] = useState("2027-11-18");
  const [leaveParts, setLeaveParts] = useState(1);
  const [paymentVariant, setPaymentVariant] = useState<PaymentVariant>("81_5");
  const [workFte, setWorkFte] = useState(0.5);
  const [hospFrom, setHospFrom] = useState("");
  const [hospTo, setHospTo] = useState("");
  const [resignationDate, setResignationDate] = useState("");
  const [notes, setNotes] = useState("");

  const [submission, setSubmission] = useState<ApplicationSubmissionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api
      .getDocumentGuidance(insuranceTitle, employerCount)
      .then(setGuidance)
      .catch(() => setGuidance(null));
  }, [insuranceTitle, employerCount]);

  // Automatyczne wyliczenie nieprzekraczalnego terminu 21 dni po porodzie
  const deadline21Preview = useMemo(() => {
    if (!childBirthDate) return null;
    const d = new Date(`${childBirthDate}T00:00:00`);
    if (Number.isNaN(d.getTime())) return null;
    d.setDate(d.getDate() + 21);
    return d.toISOString().slice(0, 10);
  }, [childBirthDate]);

  const handleSimulateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const recipient =
        appType === "zam_zus"
          ? "Zakład Ubezpieczeń Społecznych (PUE/eZUS)"
          : appType === "usc_birth_certificate"
          ? "Urząd Stanu Cywilnego (Rejestr Stanu Cywilnego)"
          : "Pracodawca";

      const res = await api.submitApplication({
        application_type: appType,
        applicant_name: applicantName,
        pesel_masked: user?.pesel_masked || "920514*****",
        child_birth_date: childBirthDate || null,
        leave_start_date: leaveStartDate || null,
        leave_end_date: leaveEndDate || null,
        leave_parts_count: Number(leaveParts),
        work_fte_fraction: appType === "leave_work_combination" ? Number(workFte) : null,
        hospitalization_from: appType === "leave_supplementary" ? hospFrom || null : null,
        hospitalization_to: appType === "leave_supplementary" ? hospTo || null : null,
        resignation_date: appType === "leave_resignation" ? resignationDate || null : null,
        payment_variant: paymentVariant,
        recipient,
        notes: notes || null,
      });
      setSubmission(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nie udało się wygenerować wniosku");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDownloadTxt = () => {
    if (!submission) return;
    const blob = new Blob([submission.generated_document_text], {
      type: "text/plain;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${submission.reference_number}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <PageHeader
        badge="Dokumenty i wnioski"
        title="Dokumenty, terminy i kreator wniosków"
        description="Sprawdź, czy Twoje dokumenty trafiają do pracodawcy czy bezpośrednio do ZUS, oblicz termin 21 dni na stawkę 81,5% i wygeneruj gotowy podgląd wniosku do druku lub pobrania."
      />

      <div className="grid gap-8 lg:grid-cols-12">
        {/* Lista dokumentów */}
        <section className="space-y-4 lg:col-span-6">
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs dark:border-emerald-950 dark:bg-[#111c17]">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
              Kto wypłaca zasiłek i jakie dokumenty złożyć?
            </h2>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Forma zatrudnienia / ubezpieczenia
                </label>
                <select
                  value={insuranceTitle}
                  onChange={(e) => setInsuranceTitle(e.target.value as InsuranceTitle)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
                >
                  <option value="uop">Umowa o pracę</option>
                  <option value="zlecenie">Umowa zlecenie</option>
                  <option value="jdg">Działalność gospodarcza (JDG)</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Liczba ubezpieczonych u płatnika
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

            {guidance && (
              <div className="mt-5 space-y-4">
                <div className="rounded-lg bg-[#e6f4ec] p-4 text-xs text-[#005a27] dark:bg-[#007834]/20 dark:text-emerald-300">
                  <p className="font-bold">Wypłacający zasiłek: {guidance.payer}</p>
                  <p className="mt-1">{guidance.payer_explanation}</p>
                </div>

                <div className="space-y-3">
                  {guidance.documents.map((d, idx) => (
                    <div
                      key={idx}
                      className="rounded-lg border border-slate-200 p-4 text-xs dark:border-emerald-950"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="rounded bg-slate-900 px-2 py-0.5 font-mono text-[11px] font-bold text-white">
                          {d.form_code}
                        </span>
                        <span className="text-slate-500 dark:text-slate-400">
                          Termin: {d.deadline}
                        </span>
                      </div>
                      <p className="mt-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                        {d.title}
                      </p>
                      <p className="mt-1 text-slate-600 dark:text-slate-400">
                        <strong>Składa:</strong> {d.submitted_by} → <strong>Do:</strong>{" "}
                        {d.submitted_to}
                      </p>
                      <p className="mt-1 text-slate-500 dark:text-slate-400">{d.notes}</p>
                    </div>
                  ))}
                </div>

                <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-xs text-amber-900 dark:border-amber-800/60 dark:bg-amber-950/40 dark:text-amber-200">
                  <p className="font-bold">Kluczowe zasady i zmiany (Poradnik ZUS 2026)</p>
                  <ul className="mt-1 list-disc space-y-1 pl-4">
                    {guidance.important_notes_2026.map((n, i) => (
                      <li key={i}>{n}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>
        </section>

        {/* Kreator wniosków + podgląd */}
        <section className="space-y-4 lg:col-span-6">
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs dark:border-emerald-950 dark:bg-[#111c17]">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
              Kreator i symulator złożenia wniosku
            </h2>
            <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
              Wypełnij szczegółowe pola, wygeneruj gotowy dokument do druku/PDF i zasymuluj jego
              złożenie.
            </p>

            <form onSubmit={handleSimulateSubmit} className="mt-4 space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Rodzaj wniosku
                </label>
                <select
                  value={appType}
                  onChange={(e) => setAppType(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
                >
                  <option value="leave_employer">
                    Wniosek do pracodawcy o urlop macierzyński i rodzicielski
                  </option>
                  <option value="leave_supplementary">
                    Wniosek o uzupełniający urlop macierzyński (wcześniak / hospitalizacja)
                  </option>
                  <option value="leave_work_combination">
                    Wniosek o łączenie urlopu rodzicielskiego z pracą (maks. 1/2 etatu)
                  </option>
                  <option value="leave_resignation">
                    Wniosek o rezygnację z części urlopu macierzyńskiego / rodzicielskiego
                  </option>
                  <option value="zam_zus">Wniosek ZAM do ZUS o zasiłek macierzyński</option>
                  <option value="usc_birth_certificate">
                    Wniosek o odpis skrócony/zupełny aktu urodzenia (USC)
                  </option>
                </select>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Imię i nazwisko wnioskodawcy
                  </label>
                  <input
                    type="text"
                    required
                    value={applicantName}
                    onChange={(e) => setApplicantName(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Data urodzenia dziecka
                  </label>
                  <input
                    type="date"
                    value={childBirthDate}
                    onChange={(e) => setChildBirthDate(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
                  />
                </div>
              </div>

              {deadline21Preview && (
                <div className="rounded-lg border border-[#007834]/25 bg-[#e6f4ec]/70 px-3 py-2 text-xs text-[#005a27] dark:border-emerald-700/40 dark:bg-emerald-950/40 dark:text-emerald-200">
                  <strong>Nieprzekraczalny termin 21 dni na stawkę 81,5%:</strong>{" "}
                  <span className="font-mono font-bold">{deadline21Preview}</span>
                </div>
              )}

              {appType !== "usc_birth_certificate" && (
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                      Urlop / zasiłek od
                    </label>
                    <input
                      type="date"
                      value={leaveStartDate}
                      onChange={(e) => setLeaveStartDate(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                      Urlop / zasiłek do
                    </label>
                    <input
                      type="date"
                      value={leaveEndDate}
                      onChange={(e) => setLeaveEndDate(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
                    />
                  </div>
                </div>
              )}

              {(appType === "leave_employer" || appType === "zam_zus") && (
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                      Wariant wypłaty
                    </label>
                    <select
                      value={paymentVariant}
                      onChange={(e) => setPaymentVariant(e.target.value as PaymentVariant)}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
                    >
                      <option value="81_5">81,5% (wniosek/deklaracja w 21 dni)</option>
                      <option value="100_70">100% macierzyński + 70% rodzicielski</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                      Liczba części urlopu rodzicielskiego (1–5)
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={5}
                      value={leaveParts}
                      onChange={(e) => setLeaveParts(Number(e.target.value))}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
                    />
                  </div>
                </div>
              )}

              {appType === "leave_work_combination" && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Wymiar czasu pracy (maks. 0.5 etatu)
                  </label>
                  <input
                    type="number"
                    min={0.1}
                    max={0.5}
                    step={0.05}
                    value={workFte}
                    onChange={(e) => setWorkFte(Number(e.target.value))}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
                  />
                </div>
              )}

              {appType === "leave_supplementary" && (
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                      Hospitalizacja dziecka od
                    </label>
                    <input
                      type="date"
                      value={hospFrom}
                      onChange={(e) => setHospFrom(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                      Hospitalizacja dziecka do
                    </label>
                    <input
                      type="date"
                      value={hospTo}
                      onChange={(e) => setHospTo(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
                    />
                  </div>
                </div>
              )}

              {appType === "leave_resignation" && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Data rezygnacji z dalszej części urlopu
                  </label>
                  <input
                    type="date"
                    value={resignationDate}
                    onChange={(e) => setResignationDate(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Uwagi dodatkowe (opcjonalnie)
                </label>
                <input
                  type="text"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="np. przejęcie pozostałej części przez ojca dziecka"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
                />
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="w-full rounded-lg bg-[#007834] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#005a27] disabled:opacity-50"
              >
                {submitting ? "Generowanie..." : "Wygeneruj podgląd i zasymuluj wysłanie"}
              </button>

              {error && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700 dark:border-red-800/60 dark:bg-red-950/40 dark:text-red-300">
                  {error}
                </div>
              )}
            </form>
          </div>

          {submission && (
            <div className="rounded-xl border border-emerald-200 bg-white p-5 shadow-xs dark:border-emerald-800/60 dark:bg-[#111c17]">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs font-bold text-emerald-800 dark:text-emerald-300">
                  {submission.status} ({submission.reference_number})
                </p>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => window.print()}
                    className="inline-flex items-center gap-1 rounded border border-slate-300 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-[#1e3328]"
                  >
                    <Printer className="h-3.5 w-3.5" />
                    Drukuj / PDF
                  </button>
                  <button
                    type="button"
                    onClick={handleDownloadTxt}
                    className="inline-flex items-center gap-1 rounded bg-[#007834] px-2.5 py-1 text-xs font-semibold text-white hover:bg-[#005a27]"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Pobierz .txt
                  </button>
                </div>
              </div>
              <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-50 p-4 font-mono text-xs text-slate-800 dark:border-slate-700 dark:bg-[#0e1914] dark:text-slate-200">
                {submission.generated_document_text}
              </pre>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
