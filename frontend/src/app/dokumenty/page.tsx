"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { useUser } from "@/components/UserContext";
import { api } from "@/lib/api";
import type { DocumentGuidanceResponse, InsuranceTitle } from "@/lib/types";

export default function DocumentsPage() {
  const { user } = useUser();

  const [insuranceTitle, setInsuranceTitle] = useState<InsuranceTitle>(
    user?.insurance_title || "uop"
  );
  const [employerCount, setEmployerCount] = useState(user?.employer_insured_count ?? 25);
  const [guidance, setGuidance] = useState<DocumentGuidanceResponse | null>(null);

  // Symulacja składania wniosku
  const [appType, setAppType] = useState("leave_employer");
  const [applicantName, setApplicantName] = useState(user?.full_name || "Anna Kowalska");
  const [childBirthDate, setChildBirthDate] = useState("2026-11-20");
  const [submissionMsg, setSubmissionMsg] = useState<string | null>(null);

  useEffect(() => {
    api
      .getDocumentGuidance(insuranceTitle, employerCount)
      .then(setGuidance)
      .catch(() => setGuidance(null));
  }, [insuranceTitle, employerCount]);

  const handleSimulateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const recipient =
      appType === "leave_employer"
        ? "Pracodawca"
        : appType === "zam_zus"
        ? "ZUS (PUE/eZUS)"
        : "Urząd Stanu Cywilnego (Rejestr Stanu Cywilnego)";
    const res = await api.submitApplication({
      application_type: appType,
      applicant_name: applicantName,
      pesel_masked: user?.pesel_masked || "920514*****",
      child_birth_date: childBirthDate,
      recipient,
    });
    setSubmissionMsg(`${res.status} — nr referencyjny: ${res.reference_number}`);
  };

  return (
    <div>
      <PageHeader
        badge="Moduł 4 • Procedury i wnioski"
        title="Dokumenty, terminy i symulator składania wniosków"
        description="Sprawdź, czy Twoje dokumenty trafiają do pracodawcy czy bezpośrednio do ZUS, poznaj aktualne formularze (ZAM, Z-3, Z-3a, ZAS-53) i zasymuluj złożenie wniosku o urlop, zasiłek lub akt urodzenia."
      />

      <div className="grid gap-8 lg:grid-cols-12">
        {/* Lista dokumentów */}
        <section className="space-y-4 lg:col-span-7">
          <div className="rounded-xl border border-slate-200 dark:border-emerald-950 bg-white dark:bg-[#111c17] p-6 shadow-xs">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">Kto wypłaca zasiłek i jakie dokumenty złożyć?</h2>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Forma zatrudnienia / ubezpieczenia
                </label>
                <select
                  value={insuranceTitle}
                  onChange={(e) => setInsuranceTitle(e.target.value as InsuranceTitle)}
                  className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm"
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
                  className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm"
                />
              </div>
            </div>

            {guidance && (
              <div className="mt-5 space-y-4">
                <div className="rounded-lg bg-[#e6f4ec] dark:bg-[#007834]/20 p-4 text-xs text-[#005a27] dark:text-emerald-300">
                  <p className="font-bold">Wypłacający zasiłek: {guidance.payer}</p>
                  <p className="mt-1">{guidance.payer_explanation}</p>
                </div>

                <div className="space-y-3">
                  {guidance.documents.map((d, idx) => (
                    <div key={idx} className="rounded-lg border border-slate-200 dark:border-emerald-950 p-4 text-xs">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="rounded bg-slate-900 px-2 py-0.5 font-mono text-[11px] font-bold text-white">
                          {d.form_code}
                        </span>
                        <span className="text-slate-500 dark:text-slate-400">Termin: {d.deadline}</span>
                      </div>
                      <p className="mt-2 text-sm font-bold text-slate-900 dark:text-slate-100">{d.title}</p>
                      <p className="mt-1 text-slate-600 dark:text-slate-400">
                        <strong>Składa:</strong> {d.submitted_by} → <strong>Do:</strong>{" "}
                        {d.submitted_to}
                      </p>
                      <p className="mt-1 text-slate-500 dark:text-slate-400">{d.notes}</p>
                    </div>
                  ))}
                </div>

                <div className="rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-800/60 dark:bg-amber-950/40 p-4 text-xs text-amber-900 dark:text-amber-200">
                  <p className="font-bold">Zmiany formularzy ZUS (od 24.10.2026)</p>
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

        {/* Kreator / symulator wniosków */}
        <section className="rounded-xl border border-slate-200 dark:border-emerald-950 bg-white dark:bg-[#111c17] p-6 shadow-xs lg:col-span-5">
          <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
            Symulator złożenia wniosku (Urlop / ZAM / Akt urodzenia USC)
          </h2>
          <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
            Wypróbuj elektroniczne wypełnienie i wysłanie dokumentu w trybie symulacji.
          </p>

          <form onSubmit={handleSimulateSubmit} className="mt-4 space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">Rodzaj wniosku</label>
              <select
                value={appType}
                onChange={(e) => setAppType(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm"
              >
                <option value="leave_employer">
                  Wniosek do pracodawcy o urlop macierzyński i rodzicielski
                </option>
                <option value="zam_zus">Wniosek ZAM do ZUS o zasiłek macierzyński</option>
                <option value="usc_birth_certificate">
                  Wniosek o odpis skrócony/zupełny aktu urodzenia (USC / gov.pl)
                </option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                Imię i nazwisko wnioskodawcy
              </label>
              <input
                type="text"
                required
                value={applicantName}
                onChange={(e) => setApplicantName(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                Data porodu / urodzenia dziecka
              </label>
              <input
                type="date"
                value={childBirthDate}
                onChange={(e) => setChildBirthDate(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm"
              />
            </div>

            <button
              type="submit"
              className="w-full rounded-lg bg-[#007834] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#005a27]"
            >
              Zasymuluj wysłanie wniosku
            </button>

            {submissionMsg && (
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 dark:border-emerald-800/60 dark:bg-emerald-950/40 p-3 text-xs font-medium text-emerald-900 dark:text-emerald-200">
                {submissionMsg}
              </div>
            )}
          </form>
        </section>
      </div>
    </div>
  );
}
