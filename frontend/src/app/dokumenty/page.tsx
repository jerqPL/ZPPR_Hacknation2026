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
          <div className="rounded-xl border border-[#CCC5B9] bg-[#FFFCF2] p-6 shadow-xs">
            <h2 className="text-base font-bold text-[#000000]">Kto wypłaca zasiłek i jakie dokumenty złożyć?</h2>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-semibold text-[#262522]">
                  Forma zatrudnienia / ubezpieczenia
                </label>
                <select
                  value={insuranceTitle}
                  onChange={(e) => setInsuranceTitle(e.target.value as InsuranceTitle)}
                  className="mt-1 w-full rounded-lg border border-[#CCC5B9] px-3 py-2 text-sm"
                >
                  <option value="uop">Umowa o pracę</option>
                  <option value="zlecenie">Umowa zlecenie</option>
                  <option value="jdg">Działalność gospodarcza (JDG)</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-[#262522]">
                  Liczba ubezpieczonych u płatnika
                </label>
                <input
                  type="number"
                  min={0}
                  value={employerCount}
                  onChange={(e) => setEmployerCount(Number(e.target.value))}
                  className="mt-1 w-full rounded-lg border border-[#CCC5B9] px-3 py-2 text-sm"
                />
              </div>
            </div>

            {guidance && (
              <div className="mt-5 space-y-4">
                <div className="rounded-lg bg-[#F5F1E6] p-4 text-xs text-[#000000]">
                  <p className="font-bold">Wypłacający zasiłek: {guidance.payer}</p>
                  <p className="mt-1">{guidance.payer_explanation}</p>
                </div>

                <div className="space-y-3">
                  {guidance.documents.map((d, idx) => (
                    <div key={idx} className="rounded-lg border border-[#CCC5B9] p-4 text-xs">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="rounded bg-[#000000] px-2 py-0.5 font-mono text-[11px] font-bold text-[#FFFCF2]">
                          {d.form_code}
                        </span>
                        <span className="text-[#403D39]/80">Termin: {d.deadline}</span>
                      </div>
                      <p className="mt-2 text-sm font-bold text-[#000000]">{d.title}</p>
                      <p className="mt-1 text-[#403D39]">
                        <strong>Składa:</strong> {d.submitted_by} → <strong>Do:</strong>{" "}
                        {d.submitted_to}
                      </p>
                      <p className="mt-1 text-[#403D39]/80">{d.notes}</p>
                    </div>
                  ))}
                </div>

                <div className="rounded-lg border border-[#CCC5B9] bg-[#F5F1E6] p-4 text-xs text-[#000000]">
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
        <section className="rounded-xl border border-[#CCC5B9] bg-[#FFFCF2] p-6 shadow-xs lg:col-span-5">
          <h2 className="text-base font-bold text-[#000000]">
            Symulator złożenia wniosku (Urlop / ZAM / Akt urodzenia USC)
          </h2>
          <p className="mt-1 text-xs text-[#403D39]">
            Wypróbuj elektroniczne wypełnienie i wysłanie dokumentu w trybie symulacji.
          </p>

          <form onSubmit={handleSimulateSubmit} className="mt-4 space-y-4">
            <div>
              <label className="block text-xs font-semibold text-[#262522]">Rodzaj wniosku</label>
              <select
                value={appType}
                onChange={(e) => setAppType(e.target.value)}
                className="mt-1 w-full rounded-lg border border-[#CCC5B9] px-3 py-2 text-sm"
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
              <label className="block text-xs font-semibold text-[#262522]">
                Imię i nazwisko wnioskodawcy
              </label>
              <input
                type="text"
                required
                value={applicantName}
                onChange={(e) => setApplicantName(e.target.value)}
                className="mt-1 w-full rounded-lg border border-[#CCC5B9] px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#262522]">
                Data porodu / urodzenia dziecka
              </label>
              <input
                type="date"
                value={childBirthDate}
                onChange={(e) => setChildBirthDate(e.target.value)}
                className="mt-1 w-full rounded-lg border border-[#CCC5B9] px-3 py-2 text-sm"
              />
            </div>

            <button
              type="submit"
              className="w-full rounded-lg bg-[#000000] px-4 py-2.5 text-sm font-semibold text-[#FFFCF2] transition hover:bg-[#262522]"
            >
              Zasymuluj wysłanie wniosku
            </button>

            {submissionMsg && (
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs font-medium text-emerald-900">
                {submissionMsg}
              </div>
            )}
          </form>
        </section>
      </div>
    </div>
  );
}
