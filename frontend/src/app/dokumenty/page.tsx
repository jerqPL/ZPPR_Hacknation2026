"use client";

import { useEffect, useState } from "react";
import { ExternalLink } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { useUser } from "@/components/UserContext";
import { api } from "@/lib/api";
import type { DocumentGuidanceResponse, InsuranceTitle } from "@/lib/types";

export default function DocumentsPage() {
  const { user } = useUser();

  const [insuranceTitle, setInsuranceTitle] = useState<InsuranceTitle>(
    user?.insurance_title && user.insurance_title !== "none" ? user.insurance_title : "uop"
  );
  const [employerCount, setEmployerCount] = useState(user?.employer_insured_count ?? 25);
  const [guidance, setGuidance] = useState<DocumentGuidanceResponse | null>(null);

  // Symulacja składania wniosku (Urlop / ZAM / Akt urodzenia USC)
  const [appType, setAppType] = useState("leave_employer");
  const [applicantName, setApplicantName] = useState(user?.full_name || "Anna Kowalska");
  const [childName, setChildName] = useState("Jan Kowalski");
  const [childBirthDate, setChildBirthDate] = useState("2026-11-20");
  const [leaveStartDate, setLeaveStartDate] = useState("2026-11-20");
  const [leaveSubtype, setLeaveSubtype] = useState(
    "Łączny wniosek o urlop macierzyński i rodzicielski (pełny wymiar — 81,5%)"
  );
  const [zamScope, setZamScope] = useState(
    "Zasiłek macierzyński za okres urlopu macierzyńskiego i rodzicielskiego (81,5%)"
  );
  const [uscCopyType, setUscCopyType] = useState("Odpis skrócony aktu urodzenia");
  const [paymentVariant, setPaymentVariant] = useState("81_5");
  const [submissionMsg, setSubmissionMsg] = useState<{
    status: string;
    ref: string;
    summary: string;
  } | null>(null);

  useEffect(() => {
    if (user) {
      if (user.insurance_title !== "none") {
        setInsuranceTitle(user.insurance_title);
      }
      setEmployerCount(user.employer_insured_count);
      setApplicantName(user.full_name);
    }
  }, [user]);

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
        ? "Pracodawca (dział kadr i płac)"
        : appType === "zam_zus"
        ? "Zakład Ubezpieczeń Społecznych (PUE/eZUS)"
        : "Urząd Stanu Cywilnego (Rejestr Stanu Cywilnego — gov.pl)";
    const detailNotes =
      appType === "leave_employer"
        ? `${leaveSubtype}; dziecko: ${childName}`
        : appType === "zam_zus"
        ? `${zamScope}; dziecko: ${childName}`
        : `${uscCopyType}; dziecko: ${childName}`;

    const res = await api.submitApplication({
      application_type: appType,
      applicant_name: applicantName,
      pesel_masked: user?.pesel_masked || "920514*****",
      child_birth_date: childBirthDate,
      leave_start_date: leaveStartDate,
      payment_variant: paymentVariant,
      recipient,
      notes: detailNotes,
    });
    setSubmissionMsg({
      status: res.status,
      ref: res.reference_number,
      summary: `${res.summary} Szczegóły: ${detailNotes}.`,
    });
  };

  return (
    <div>
      <PageHeader
        badge="Dokumenty i wnioski"
        title="Dokumenty, terminy i kreator składania wniosków"
        description="Sprawdź, czy Twoje dokumenty trafiają do płatnika składek (pracodawcy >20 ubezpieczonych) czy bezpośrednio do ZUS, poznaj aktualne formularze (ZAM po likwidacji ZUR i ZAO od 24.10.2026, Z-3, Z-3a, ZAS-53) i zasymuluj złożenie wniosku o urlop, zasiłek lub akt urodzenia."
      />

      <div className="grid gap-8 lg:grid-cols-12">
        {/* Lista dokumentów */}
        <section className="space-y-4 lg:col-span-7">
          <div className="rounded-xl border border-slate-200 dark:border-emerald-950 bg-white dark:bg-[#111c17] p-6 shadow-xs">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
              Kto wypłaca zasiłek i gdzie złożyć dokumenty?
            </h2>
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
            </div>

            {guidance && (
              <div className="mt-5 space-y-4">
                <div className="rounded-lg bg-[#e6f4ec] dark:bg-[#007834]/20 p-4 text-xs text-[#005a27] dark:text-emerald-300">
                  <p className="font-bold">Podmiot ustalający prawo i wypłacający zasiłek: {guidance.payer}</p>
                  <p className="mt-1">{guidance.payer_explanation}</p>
                </div>

                <div className="space-y-3">
                  {guidance.documents.map((d, idx) => (
                    <div
                      key={idx}
                      className="rounded-lg border border-slate-200 dark:border-emerald-950 p-4 text-xs"
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

                <div className="rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-800/60 dark:bg-amber-950/40 p-4 text-xs text-amber-900 dark:text-amber-200">
                  <p className="font-bold">Zmiany formularzy ZUS (od 24 października 2026 r.)</p>
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
            Symulator wypełnienia i złożenia wniosku (Urlop / ZAM / Akt urodzenia USC)
          </h2>
          <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
            Zaprojektowany kreator wniosków o urlopy związane z rodzicielstwem (wg rozporządzenia
            MRPiPS), wniosku ZAM do ZUS oraz wniosku o wydanie odpisu aktu urodzenia dziecka.
          </p>

          <form onSubmit={handleSimulateSubmit} className="mt-4 space-y-3.5">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                1. Kategoria dokumentu
              </label>
              <select
                value={appType}
                onChange={(e) => {
                  setAppType(e.target.value);
                  setSubmissionMsg(null);
                }}
                className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm"
              >
                <option value="leave_employer">
                  Wniosek do pracodawcy o urlop związany z rodzicielstwem (Kodeks pracy)
                </option>
                <option value="zam_zus">
                  Wniosek ZAM do ZUS o zasiłek macierzyński (zastępuje też dawne ZUR i ZAO)
                </option>
                <option value="usc_birth_certificate">
                  Wniosek o wydanie odpisu aktu urodzenia dziecka (USC / Rejestr Stanu Cywilnego)
                </option>
              </select>
            </div>

            {appType === "leave_employer" && (
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Rodzaj wnioskowanego urlopu (zaprojektowany wzór wniosku pracowniczego)
                </label>
                <select
                  value={leaveSubtype}
                  onChange={(e) => setLeaveSubtype(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-xs"
                >
                  <option value="Łączny wniosek o urlop macierzyński i rodzicielski (pełny wymiar — 81,5%)">
                    Łączny wniosek o urlop macierzyński i rodzicielski w pełnym wymiarze (w 21 dni — 81,5%)
                  </option>
                  <option value="Wniosek o urlop macierzyński / na warunkach urlopu macierzyńskiego (100%)">
                    Wniosek o urlop macierzyński / na warunkach urlopu macierzyńskiego (100%)
                  </option>
                  <option value="Wniosek o uzupełniający urlop macierzyński (wcześniak / hospitalizacja — 100%)">
                    Wniosek o uzupełniający urlop macierzyński (wcześniak / hospitalizacja — 100%)
                  </option>
                  <option value="Wniosek o urlop rodzicielski (w tym 9 tyg. nieprzenoszalnych — 70%)">
                    Wniosek o urlop rodzicielski (w tym 9 tyg. części nieprzenoszalnej — 70%)
                  </option>
                  <option value="Wniosek o łączenie urlopu rodzicielskiego z pracą (do 1/2 etatu — art. 182¹ᵉ KP)">
                    Wniosek o łączenie korzystania z urlopu rodzicielskiego z pracą (do 1/2 etatu)
                  </option>
                  <option value="Wniosek o urlop ojcowski (14 dni — 100%, art. 182³ KP)">
                    Wniosek o urlop ojcowski (14 dni kalendarzowych — 100%)
                  </option>
                </select>
              </div>
            )}

            {appType === "zam_zus" && (
              <div className="space-y-2">
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Zakres wniosku ZAM (ujednolicony formularz od 24.10.2026 r.)
                </label>
                <select
                  value={zamScope}
                  onChange={(e) => setZamScope(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-xs"
                >
                  <option value="Zasiłek macierzyński za okres urlopu macierzyńskiego i rodzicielskiego (81,5%)">
                    Zasiłek macierzyński za okres urlopu macierzyńskiego i rodzicielskiego (81,5% — w 21 dni)
                  </option>
                  <option value="Zasiłek macierzyński za okres urlopu macierzyńskiego / na warunkach macierzyńskiego (100%)">
                    Zasiłek macierzyński za okres urlopu macierzyńskiego / na warunkach macierzyńskiego (100%)
                  </option>
                  <option value="Zasiłek macierzyński za okres uzupełniającego urlopu macierzyńskiego (100%)">
                    Zasiłek macierzyński za okres uzupełniającego urlopu macierzyńskiego (100%)
                  </option>
                  <option value="Zasiłek macierzyński za okres urlopu rodzicielskiego (dawny ZUR — połączony z ZAM)">
                    Zasiłek macierzyński za okres urlopu rodzicielskiego (dawny ZUR — połączony z ZAM)
                  </option>
                  <option value="Zasiłek macierzyński za okres urlopu ojcowskiego (dawny ZAO — połączony z ZAM)">
                    Zasiłek macierzyński za okres urlopu ojcowskiego (dawny ZAO — połączony z ZAM)
                  </option>
                </select>
                <a
                  href="https://www.zus.pl"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#007834] dark:text-emerald-400 hover:underline"
                >
                  Oficjalne wzory formularzy o świadczenia na www.zus.pl
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            )}

            {appType === "usc_birth_certificate" && (
              <div className="space-y-2">
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Rodzaj odpisu aktu stanu cywilnego (urodzenia dziecka)
                </label>
                <select
                  value={uscCopyType}
                  onChange={(e) => setUscCopyType(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-xs"
                >
                  <option value="Odpis skrócony aktu urodzenia (wymagany do zasiłku macierzyńskiego)">
                    Odpis skrócony aktu urodzenia dziecka
                  </option>
                  <option value="Odpis zupełny aktu urodzenia">
                    Odpis zupełny aktu urodzenia dziecka
                  </option>
                </select>
                <a
                  href="https://www.gov.pl/web/cyfryzacja/rejestr-stanu-cywilnego"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#007834] dark:text-emerald-400 hover:underline"
                >
                  Informacje o Rejestrze Stanu Cywilnego na gov.pl
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            )}

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
                  className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Imię i nazwisko dziecka
                </label>
                <input
                  type="text"
                  required
                  value={childName}
                  onChange={(e) => setChildName(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm"
                />
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
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
              {appType !== "usc_birth_certificate" && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Data rozpoczęcia urlopu / zasiłku
                  </label>
                  <input
                    type="date"
                    value={leaveStartDate}
                    onChange={(e) => setLeaveStartDate(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm"
                  />
                </div>
              )}
            </div>

            {appType !== "usc_birth_certificate" && (
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Deklarowany wariant wypłaty zasiłku
                </label>
                <select
                  value={paymentVariant}
                  onChange={(e) => setPaymentVariant(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-xs"
                >
                  <option value="81_5">81,5% za cały okres (wniosek w ciągu 21 dni)</option>
                  <option value="100_70">100% urlop macierzyński / 70% urlop rodzicielski</option>
                </select>
              </div>
            )}

            <button
              type="submit"
              className="w-full rounded-lg bg-[#007834] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#005a27]"
            >
              Zasymuluj elektroniczne wysłanie wniosku
            </button>

            {submissionMsg && (
              <div className="space-y-1 rounded-lg border border-emerald-200 bg-emerald-50 dark:border-emerald-800/60 dark:bg-emerald-950/40 p-3 text-xs text-emerald-900 dark:text-emerald-200">
                <p className="font-bold">
                  {submissionMsg.status} — nr referencyjny: {submissionMsg.ref}
                </p>
                <p>{submissionMsg.summary}</p>
              </div>
            )}
          </form>
        </section>
      </div>
    </div>
  );
}
