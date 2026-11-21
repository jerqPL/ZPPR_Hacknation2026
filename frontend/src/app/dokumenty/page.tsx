"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { CheckCircle2, Download, ExternalLink, FileText, Printer, Send } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { useUser } from "@/components/UserContext";
import { api } from "@/lib/api";
import type {
  ApplicationSubmissionResponse,
  DocumentGuidanceResponse,
  InsuranceTitle,
  LegalParameters,
  PaymentVariant,
} from "@/lib/types";

const OFFICIAL_FORM_LINKS = [
  {
    code: "ZAM",
    name: "Wniosek o zasiłek macierzyński (aktualizacja 24.10.2026 — zastępuje ZUR i ZAO)",
    url: "https://www.zus.pl/-/wniosek-zas-54",
  },
  {
    code: "Z-3",
    name: "Zaświadczenie płatnika składek — dla pracownika (UoP)",
    url: "https://www.zus.pl/wzory-formularzy/zasilki/zasilek-chorobowy/-/asset_publisher/TS3WYPoYHIaG/content/zaswiadczenie-zus-z-3",
  },
  {
    code: "Z-3a",
    name: "Zaświadczenie płatnika składek — dla zleceniobiorcy",
    url: "https://www.zus.pl/wzory-formularzy/zasilki/zasilek-macierzynski/-/asset_publisher/m5Npg4icZlfP/content/zaswiadczenie-zus-z-3a",
  },
  {
    code: "ZAS-53",
    name: "Wniosek o zasiłek chorobowy (np. ciąża na JDG, aktualizacja 24.10.2026)",
    url: "https://www.zus.pl/-/zaswiadczenie-zas-53",
  },
  {
    code: "USC (gov.pl)",
    name: "Uzyskaj odpis aktu stanu cywilnego (skrócony / zupełny, e-Doręczenia)",
    url: "https://www.gov.pl/web/gov/uzyskaj-odpis-aktu-stanu-cywilnego-urodzenia-malzenstwa-zgonu",
  },
];

export default function DocumentsPage() {
  const { user } = useUser();

  const [legalParams, setLegalParams] = useState<LegalParameters | null>(null);
  const [insuranceTitle, setInsuranceTitle] = useState<InsuranceTitle>(
    user?.insurance_title || "uop"
  );
  const [employerCount, setEmployerCount] = useState(user?.employer_insured_count ?? 25);
  const [guidance, setGuidance] = useState<DocumentGuidanceResponse | null>(null);

  // Kreator formalnych wniosków (Dz.U. 2025 poz. 322 & Dz.U. 2026 poz. 1316)
  const [appType, setAppType] = useState("leave_employer");
  const [applicantName, setApplicantName] = useState(user?.full_name || "Anna Kowalska");
  const [recipientName, setRecipientName] = useState(
    user?.employer_name || "TechPol Sp. z o.o. (Dział Kadr)"
  );
  const [childBirthDate, setChildBirthDate] = useState("2026-11-20");
  const [leaveStartDate, setLeaveStartDate] = useState("2026-11-20");
  const [leaveEndDate, setLeaveEndDate] = useState("2027-11-18");
  const [leaveParts, setLeaveParts] = useState(1);
  const [paymentVariant, setPaymentVariant] = useState<PaymentVariant>("81_5");
  const [workFte, setWorkFte] = useState(0.5);
  const [workDuringExtendedPart, setWorkDuringExtendedPart] = useState(true);
  const [maternityEndDate, setMaternityEndDate] = useState("");
  const [hospFrom, setHospFrom] = useState("");
  const [hospTo, setHospTo] = useState("");
  const [resignationDate, setResignationDate] = useState("");
  const [uscCopyType, setUscCopyType] = useState<"skrocony" | "zupelny">("skrocony");
  const [notes, setNotes] = useState("");

  const [submission, setSubmission] = useState<ApplicationSubmissionResponse | null>(null);
  const [simulatedSent, setSimulatedSent] = useState<{
    channel: string;
    upoNumber: string;
    sentAt: string;
  } | null>(null);
  const [pdfPreviewUrl, setPdfPreviewUrl] = useState<string | null>(null);
  const pdfFrameRef = useRef<HTMLIFrameElement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    return () => {
      if (pdfPreviewUrl) {
        URL.revokeObjectURL(pdfPreviewUrl);
      }
    };
  }, [pdfPreviewUrl]);

  useEffect(() => {
    api.getParameters().then(setLegalParams).catch(() => setLegalParams(null));
  }, []);

  // Synchronizacja danych po zalogowaniu lub zmianie persony mObywatel
  useEffect(() => {
    if (user) {
      setApplicantName(user.full_name);
      setInsuranceTitle(user.insurance_title);
      setEmployerCount(user.employer_insured_count);
    }
  }, [user]);

  useEffect(() => {
    api
      .getDocumentGuidance(insuranceTitle, employerCount)
      .then(setGuidance)
      .catch(() => setGuidance(null));
  }, [insuranceTitle, employerCount]);

  useEffect(() => {
    if (appType === "zam_zus") {
      setRecipientName("Zakład Ubezpieczeń Społecznych (PUE/eZUS)");
    } else if (appType === "usc_birth_certificate") {
      setRecipientName("Urząd Stanu Cywilnego (Rejestr Stanu Cywilnego)");
    } else {
      setRecipientName(user?.employer_name || "Pracodawca (Dział Kadr)");
    }
  }, [appType, user]);

  const deadlineDays = legalParams?.combined_application_deadline_days ?? 21;
  const combinedRateLabel = `${((legalParams?.combined_21_days_rate ?? 0.815) * 100)
    .toFixed(1)
    .replace(".", ",")}%`;

  const deadline21Preview = useMemo(() => {
    if (!childBirthDate) return null;
    const d = new Date(`${childBirthDate}T00:00:00Z`);
    if (Number.isNaN(d.getTime())) return null;
    d.setUTCDate(d.getUTCDate() + deadlineDays);
    return d.toISOString().slice(0, 10);
  }, [childBirthDate, deadlineDays]);

  const buildPayload = (referenceNumber?: string) => ({
    application_type: appType,
    applicant_name: applicantName,
    pesel_masked: user?.pesel_masked || "920514*****",
    child_birth_date: childBirthDate || null,
    leave_start_date:
      appType !== "usc_birth_certificate" && appType !== "leave_resignation"
        ? leaveStartDate || null
        : null,
    leave_end_date:
      appType !== "usc_birth_certificate" && appType !== "leave_resignation"
        ? leaveEndDate || null
        : null,
    leave_parts_count: Number(leaveParts),
    work_fte_fraction: appType === "leave_work_combination" ? Number(workFte) : null,
    work_during_extended_part:
      appType === "leave_work_combination" ? workDuringExtendedPart : null,
    maternity_end_date: appType === "leave_supplementary" ? maternityEndDate || null : null,
    hospitalization_from: appType === "leave_supplementary" ? hospFrom || null : null,
    hospitalization_to: appType === "leave_supplementary" ? hospTo || null : null,
    resignation_date: appType === "leave_resignation" ? resignationDate || null : null,
    usc_copy_type: uscCopyType,
    payment_variant: paymentVariant,
    recipient: recipientName,
    notes: notes || null,
    reference_number: referenceNumber ?? null,
  });

  const handleSimulateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setSimulatedSent(null);
    try {
      const res = await api.submitApplication(buildPayload());
      setSubmission(res);
      // Od razu generujemy ten sam plik PDF do podglądu 1:1, drukowania i pobierania
      const pdfBlob = await api.downloadApplicationPdf(buildPayload(res.reference_number));
      const nextUrl = URL.createObjectURL(pdfBlob);
      setPdfPreviewUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return nextUrl;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nie udało się wygenerować wniosku");
    } finally {
      setSubmitting(false);
    }
  };

  const handleSimulateElectronicSend = () => {
    if (!submission) return;
    const channel =
      appType === "zam_zus"
        ? "PUE/eZUS (elektroniczna skrzynka ZUS — symulacja)"
        : appType === "usc_birth_certificate"
        ? "gov.pl / e-Doręczenia — Urząd Stanu Cywilnego (symulacja)"
        : `Dział Kadr — ${recipientName} (symulacja)`;
    setSimulatedSent({
      channel,
      upoNumber: `UPO-${submission.reference_number}`,
      sentAt: new Date().toLocaleString("pl-PL"),
    });
  };

  const handlePrintPdf = () => {
    if (pdfFrameRef.current?.contentWindow) {
      pdfFrameRef.current.contentWindow.focus();
      pdfFrameRef.current.contentWindow.print();
      return;
    }
    if (pdfPreviewUrl) {
      window.open(pdfPreviewUrl, "_blank", "noopener,noreferrer");
      return;
    }
    window.print();
  };

  const handleDownloadPdf = async () => {
    if (!submission) return;
    setError(null);
    try {
      if (pdfPreviewUrl) {
        const a = document.createElement("a");
        a.href = pdfPreviewUrl;
        a.download = `${submission.reference_number}.pdf`;
        a.click();
        return;
      }
      const pdfBlob = await api.downloadApplicationPdf(buildPayload(submission.reference_number));
      const url = URL.createObjectURL(pdfBlob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${submission.reference_number}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nie udało się pobrać pliku PDF");
    }
  };

  const showVariantAndParts =
    appType === "leave_employer" || appType === "leave_adoption_foster" || appType === "zam_zus";

  return (
    <div>
      <PageHeader
        badge="Dokumenty i wnioski"
        title="Dokumenty, oficjalne wzory ZUS i generator wniosków"
        description="Sprawdź wymagane dokumenty i terminy, pobierz oficjalne formularze ze strony ZUS / gov.pl lub wygeneruj gotowe pismo urlopowe zgodne z Rozporządzeniem MRPiPS z 11 marca 2025 r. (Dz.U. poz. 322) oraz z 27 września 2026 r. (Dz.U. poz. 1316)."
      />

      <div className="grid gap-8 lg:grid-cols-12">
        {/* Lewa kolumna: Wymagane dokumenty + Oficjalne wzory z internetu */}
        <section className="space-y-6 lg:col-span-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs dark:border-emerald-950 dark:bg-[#111c17]">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
              Oficjalne wzory formularzy ZUS i e-Usługi (gov.pl)
            </h2>
            <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
              Bezpośrednie przekierowania do aktualnych oficjalnych druków PDF ZUS oraz wniosku USC.
            </p>
            <div className="mt-4 grid gap-2.5 sm:grid-cols-2">
              {OFFICIAL_FORM_LINKS.map((f) => (
                <a
                  key={f.code}
                  href={f.url}
                  target="_blank"
                  rel="noreferrer"
                  className="group flex flex-col justify-between rounded-xl border border-slate-200 bg-slate-50/80 p-3.5 transition hover:border-[#007834] hover:bg-[#e6f4ec]/50 dark:border-emerald-950 dark:bg-[#16241d] dark:hover:border-emerald-600"
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="rounded bg-[#007834] px-2 py-0.5 font-mono text-[11px] font-bold text-white">
                        {f.code}
                      </span>
                      <ExternalLink className="h-3.5 w-3.5 text-slate-400 group-hover:text-[#007834] dark:group-hover:text-emerald-400" />
                    </div>
                    <p className="mt-2 text-xs font-semibold leading-snug text-slate-800 dark:text-slate-200">
                      {f.name}
                    </p>
                  </div>
                </a>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs dark:border-emerald-950 dark:bg-[#111c17]">
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
                  <option value="none">Brak ubezpieczenia chorobowego</option>
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
                  disabled={insuranceTitle === "jdg" || insuranceTitle === "none"}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:opacity-50 dark:border-slate-700"
                />
              </div>
            </div>

            {guidance && (
              <div className="mt-5 space-y-4">
                <div className="rounded-xl bg-[#e6f4ec] p-4 text-xs text-[#005a27] dark:bg-[#007834]/20 dark:text-emerald-300">
                  <p className="font-bold">Wypłacający świadczenie: {guidance.payer}</p>
                  <p className="mt-1">{guidance.payer_explanation}</p>
                </div>

                <div className="space-y-3">
                  {guidance.documents.map((d, idx) => (
                    <div
                      key={idx}
                      className="rounded-xl border border-slate-200 p-4 text-xs dark:border-emerald-950"
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

                <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs text-amber-900 dark:border-amber-800/60 dark:bg-amber-950/40 dark:text-amber-200">
                  <p className="font-bold">Kluczowe zasady (Poradnik ZUS 2026)</p>
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

        {/* Prawa kolumna: Generator formalnego pisma A4 */}
        <section className="space-y-5 lg:col-span-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs dark:border-emerald-950 dark:bg-[#111c17]">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-[#007834] dark:text-emerald-400" />
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Generator wniosku (wzór zgodny z Dz.U. 2025 poz. 322)
              </h2>
            </div>

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
                    Wniosek do pracodawcy o urlop macierzyński i rodzicielski (§ 15)
                  </option>
                  <option value="leave_pre_birth">
                    Wniosek o urlop macierzyński przed przewidywaną datą porodu (§ 2)
                  </option>
                  <option value="leave_supplementary">
                    Wniosek o uzupełniający urlop macierzyński — wcześniak / hospitalizacja (§ 14)
                  </option>
                  <option value="leave_work_combination">
                    Wniosek o łączenie urlopu rodzicielskiego z pracą — maks. 1/2 etatu (§ 16)
                  </option>
                  <option value="leave_paternity">
                    Wniosek o urlop ojcowski — 2 tygodnie (§ 17)
                  </option>
                  <option value="leave_adoption_foster">
                    Wniosek o urlop na warunkach macierzyńskiego — adopcja / rodzina zastępcza (§ 18)
                  </option>
                  <option value="leave_resignation">
                    Wniosek matki o rezygnację z części urlopu macierzyńskiego (§ 3)
                  </option>
                  <option value="leave_father_takeover">
                    Wniosek ojca o przejęcie pozostałej części urlopu macierzyńskiego (§ 5)
                  </option>
                  <option value="zam_zus">Wniosek ZUS ZAM o zasiłek macierzyński</option>
                  <option value="usc_birth_certificate">
                    Wniosek o odpis aktu urodzenia — skrócony lub zupełny (USC)
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
                    Adresat (pracodawca / ZUS / USC)
                  </label>
                  <input
                    type="text"
                    required
                    value={recipientName}
                    onChange={(e) => setRecipientName(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
                  />
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                    {appType === "leave_pre_birth"
                      ? "Przewidywana data porodu"
                      : "Data urodzenia dziecka"}
                  </label>
                  <input
                    type="date"
                    value={childBirthDate}
                    onChange={(e) => setChildBirthDate(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
                  />
                </div>
                {deadline21Preview && (
                  <div className="flex flex-col justify-center rounded-lg border border-[#007834]/25 bg-[#e6f4ec]/70 px-3 py-2 text-xs text-[#005a27] dark:border-emerald-700/40 dark:bg-emerald-950/40 dark:text-emerald-200">
                    <span className="text-[11px]">
                      Termin {deadlineDays} dni (stawka {combinedRateLabel})
                    </span>
                    <span className="font-mono text-sm font-bold">{deadline21Preview}</span>
                  </div>
                )}
              </div>

              {appType === "usc_birth_certificate" && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Rodzaj odpisu aktu urodzenia (USC)
                  </label>
                  <select
                    value={uscCopyType}
                    onChange={(e) => setUscCopyType(e.target.value as "skrocony" | "zupelny")}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
                  >
                    <option value="skrocony">Odpis skrócony aktu urodzenia</option>
                    <option value="zupelny">Odpis zupełny aktu urodzenia</option>
                  </select>
                </div>
              )}

              {appType !== "usc_birth_certificate" && appType !== "leave_resignation" && (
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

              {showVariantAndParts && (
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
                      <option value="81_5">
                        {combinedRateLabel} (wniosek/deklaracja w {deadlineDays} dni)
                      </option>
                      <option value="100_70">100% macierzyński + 70% rodzicielski</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                      Liczba części rodzicielskiego (1–{legalParams?.parental_max_parts ?? 5})
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={legalParams?.parental_max_parts ?? 5}
                      value={leaveParts}
                      onChange={(e) => setLeaveParts(Number(e.target.value))}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
                    />
                  </div>
                </div>
              )}

              {appType === "leave_work_combination" && (
                <div className="space-y-2.5">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                      Wymiar czasu pracy (maks. {legalParams?.parental_work_max_fte ?? 0.5} etatu)
                    </label>
                    <input
                      type="number"
                      min={0.1}
                      max={legalParams?.parental_work_max_fte ?? 0.5}
                      step="any"
                      value={workFte}
                      onChange={(e) => setWorkFte(Number(e.target.value))}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
                    />
                  </div>
                  <label className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300">
                    <input
                      type="checkbox"
                      checked={workDuringExtendedPart}
                      onChange={(e) => setWorkDuringExtendedPart(e.target.checked)}
                      className="h-4 w-4 shrink-0 accent-[#007834]"
                    />
                    Zamierzam łączyć również wydłużoną część urlopu z pracą (§ 16 pkt 4 Dz.U. 2025 poz. 322)
                  </label>
                </div>
              )}

              {appType === "leave_supplementary" && (
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                      Termin zakończenia urlopu macierzyńskiego (§ 14 ust. 1 pkt 2)
                    </label>
                    <input
                      type="date"
                      value={maternityEndDate}
                      onChange={(e) => setMaternityEndDate(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
                    />
                  </div>
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
                </div>
              )}

              {appType === "leave_resignation" && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Data powrotu do pracy (rezygnacji)
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
                  Dodatkowe informacje (opcjonalnie, maks. 2000 znaków)
                </label>
                <input
                  type="text"
                  maxLength={2000}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="np. przejęcie pozostałej części urlopu przez ojca dziecka"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
                />
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="w-full rounded-lg bg-[#007834] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#005a27] disabled:opacity-50"
              >
                {submitting ? "Generowanie..." : "Wygeneruj gotowy dokument do druku / PDF"}
              </button>

              {error && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700 dark:border-red-800/60 dark:bg-red-950/40 dark:text-red-300">
                  {error}
                </div>
              )}
            </form>
          </div>

          {/* Podgląd dokumentu w stylu oficjalnego arkusza A4 */}
          {submission && (
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-emerald-950 dark:bg-[#111c17]">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-3 dark:border-slate-800">
                <div>
                  <p className="text-xs font-bold text-[#007834] dark:text-emerald-400">
                    {submission.status}
                  </p>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">
                    Nr roboczy: {submission.reference_number}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={handleSimulateElectronicSend}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-[#007834]/40 bg-[#e6f4ec] px-3 py-1.5 text-xs font-semibold text-[#005a27] hover:bg-[#d5ecdf] dark:border-emerald-700/50 dark:bg-[#007834]/25 dark:text-emerald-300 dark:hover:bg-[#007834]/40"
                  >
                    <Send className="h-3.5 w-3.5" />
                    Zasymuluj wysłanie
                  </button>
                  <button
                    type="button"
                    onClick={handlePrintPdf}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-[#1e3328]"
                  >
                    <Printer className="h-3.5 w-3.5" />
                    Drukuj (tylko dokument)
                  </button>
                  <button
                    type="button"
                    onClick={handleDownloadPdf}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-[#007834] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#005a27]"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Pobierz PDF
                  </button>
                </div>
              </div>

              {simulatedSent && (
                <div className="mt-3 flex items-start gap-2.5 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-900 dark:border-emerald-800/60 dark:bg-emerald-950/40 dark:text-emerald-200">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#007834] dark:text-emerald-400" />
                  <div>
                    <p className="font-bold">
                      Wniosek przesłany pomyślnie (symulacja) — {simulatedSent.upoNumber}
                    </p>
                    <p className="mt-0.5">
                      Kanał: <strong>{simulatedSent.channel}</strong> • Czas nadania:{" "}
                      {simulatedSent.sentAt}
                    </p>
                  </div>
                </div>
              )}

              {pdfPreviewUrl ? (
                <div className="mt-4 overflow-hidden rounded-xl border border-slate-300 bg-white shadow-inner">
                  <iframe
                    ref={pdfFrameRef}
                    src={`${pdfPreviewUrl}#toolbar=0&navpanes=0`}
                    title="Podgląd wygenerowanego dokumentu PDF"
                    className="h-[680px] w-full bg-white"
                  />
                </div>
              ) : (
                <div className="printable-document mt-4 rounded-xl border border-slate-300 bg-white p-6 font-serif text-[13px] leading-relaxed text-slate-900 shadow-inner">
                  <pre className="whitespace-pre-wrap font-serif">
                    {submission.generated_document_text}
                  </pre>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
