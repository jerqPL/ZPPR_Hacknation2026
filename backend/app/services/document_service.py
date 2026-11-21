from datetime import date, datetime, timedelta, timezone
import uuid
from app.models.calculator import InsuranceTitle, PaymentVariant
from app.models.guidance import DocumentGuidanceResponse, DocumentRequirement
from app.models.parameters import LegalParameters
from app.models.simulation import (
    ApplicationSubmissionRequest,
    ApplicationSubmissionResponse,
    ApplicationType,
)


def get_document_guidance(
    insurance_title: InsuranceTitle,
    employer_insured_count: int,
    params: LegalParameters,
) -> DocumentGuidanceResponse:
    employer_pays = (
        insurance_title in (InsuranceTitle.UOP, InsuranceTitle.ZLECENIE)
        and employer_insured_count > params.payer_employee_threshold
    )

    if employer_pays:
        payer = "Płatnik składek (pracodawca / zleceniodawca)"
        payer_explanation = (
            f"Płatnik zgłasza do ubezpieczenia chorobowego powyżej {params.payer_employee_threshold} osób "
            "(stan na 30 listopada poprzedniego roku), dlatego to on ustala prawo i wypłaca zasiłek."
        )
    else:
        payer = "Zakład Ubezpieczeń Społecznych (ZUS)"
        payer_explanation = (
            f"Dla osób na JDG, po ustaniu zatrudnienia lub u płatników zgłaszających do {params.payer_employee_threshold} osób "
            "prawo do zasiłku ustala i wypłaca go bezpośrednio ZUS."
        )

    docs: list[DocumentRequirement] = []

    if insurance_title == InsuranceTitle.UOP:
        docs.append(
            DocumentRequirement(
                form_code="Wniosek o urlop (KP)",
                title="Wniosek o udzielenie urlopu macierzyńskiego i rodzicielskiego (lub pisemna deklaracja 81,5%)",
                submitted_by="Pracownik (matka/ojciec)",
                submitted_to="Pracodawca",
                deadline=f"Do {params.combined_application_deadline_days} dni po porodzie (dla stawki {params.combined_21_days_rate*100:.1f}%)",
                notes="Alternatywnie można złożyć sam wniosek/deklarację o wypłatę 81,5% za pełny wymiar (art. 30a ustawy zasiłkowej).",
            )
        )
        if not employer_pays:
            docs.append(
                DocumentRequirement(
                    form_code="Z-3",
                    title="Zaświadczenie płatnika składek (dla pracownika)",
                    submitted_by="Pracodawca",
                    submitted_to="ZUS (PUE/eZUS)",
                    deadline="Niezwłocznie po otrzymaniu wniosku pracownika",
                    notes="Na dalszy okres zasiłku chorobowego pracodawca może złożyć ZAS-12.",
                )
            )
    elif insurance_title == InsuranceTitle.ZLECENIE:
        docs.append(
            DocumentRequirement(
                form_code="ZAM",
                title="Wniosek o zasiłek macierzyński",
                submitted_by="Ubezpieczony (zleceniobiorca)",
                submitted_to="Płatnik składek lub ZUS",
                deadline=f"Do {params.combined_application_deadline_days} dni po porodzie (dla stawki {params.combined_21_days_rate*100:.1f}%)",
                notes="Zleceniobiorca nie ma urlopu z Kodeksu pracy, ale ma prawo do zasiłku za okres odpowiadający urlopowi.",
            )
        )
        if not employer_pays:
            docs.append(
                DocumentRequirement(
                    form_code="Z-3a",
                    title="Zaświadczenie płatnika składek (dla zleceniobiorcy)",
                    submitted_by="Zleceniodawca",
                    submitted_to="ZUS (PUE/eZUS)",
                    deadline="Niezwłocznie po zgłoszeniu niezdolności / wniosku",
                    notes="Zawiera okresy ubezpieczenia i podstawę wymiaru składek.",
                )
            )
    else:
        docs.append(
            DocumentRequirement(
                form_code="ZAM",
                title="Wniosek o zasiłek macierzyński",
                submitted_by="Osoba prowadząca JDG / ubezpieczony",
                submitted_to="ZUS (PUE/eZUS)",
                deadline=f"Do {params.combined_application_deadline_days} dni po porodzie (dla stawki {params.combined_21_days_rate*100:.1f}%)",
                notes="Rozpoczęcie zasiłku macierzyńskiego na JDG powoduje automatyczne ustanie dobrowolnego ubezpieczenia chorobowego — po zakończeniu zasiłku wymagane jest ponowne zgłoszenie ZUS ZUA.",
            )
        )
        docs.append(
            DocumentRequirement(
                form_code="ZAS-53",
                title="Wniosek o zasiłek chorobowy (okres ciąży)",
                submitted_by="Osoba prowadząca JDG",
                submitted_to="ZUS (PUE/eZUS)",
                deadline="Po wystawieniu e-ZLA przez lekarza",
                notes="Samo e-ZLA nie uruchamia wypłaty na JDG — potrzebny jest wniosek ZAS-53.",
            )
        )

    docs.append(
        DocumentRequirement(
            form_code="Akt urodzenia (USC)",
            title="Odpis skrócony aktu urodzenia dziecka",
            submitted_by="Rodzic",
            submitted_to="Pracodawca lub ZUS (załącznik do wniosku)",
            deadline="Po rejestracji urodzenia w Urzędzie Stanu Cywilnego",
            notes="Można uzyskać online przez ePUAP / gov.pl (Rejestr Stanu Cywilnego).",
        )
    )

    notes_2026 = [
        "Od 24 października 2026 r. formularze ZUR (rodzicielski) oraz ZAO (ojcowski) zostały połączone z formularzem ZAM i zlikwidowane; zlikwidowano również Z-3b.",
        f"Roszczenie o wypłatę zasiłku przedawnia się po upływie {params.claim_limitation_months} miesięcy od ostatniego dnia okresu, za który zasiłek przysługuje (art. 67 ustawy zasiłkowej).",
        f"W przypadku urodzenia martwego dziecka rodzinie przysługuje również zasiłek pogrzebowy w wysokości {params.funeral_grant_pln:,.0f} zł (wniosek Z-12).".replace(",", " "),
        "Dla stawki 81,5% można złożyć jeden wniosek o oba urlopy albo odrębną pisemną deklarację w terminie 21 dni od porodu (art. 30a ustawy zasiłkowej).",
        "Wzory aktualnych formularzy ZUS dostępne są na stronie www.zus.pl (zakładka Wzory formularzy -> Zasiłki).",
    ]

    return DocumentGuidanceResponse(
        payer=payer,
        payer_explanation=payer_explanation,
        documents=docs,
        important_notes_2026=notes_2026,
    )


def simulate_application_submission(
    req: ApplicationSubmissionRequest,
    params: LegalParameters | None = None,
) -> ApplicationSubmissionResponse:
    from app.services.parameter_store import parameter_store

    p = params or parameter_store.get()
    today_str = date.today().isoformat()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    prefix_map = {
        ApplicationType.LEAVE_EMPLOYER: "URLOP",
        ApplicationType.LEAVE_SUPPLEMENTARY: "URLOP-UZUP",
        ApplicationType.LEAVE_RESIGNATION: "REZYGNACJA",
        ApplicationType.LEAVE_WORK_COMBINATION: "LACZENIE-PRACY",
        ApplicationType.ZAM_ZUS: "ZUS-ZAM",
        ApplicationType.USC_BIRTH_CERTIFICATE: "USC-AKT",
    }
    ref = f"{prefix_map.get(req.application_type, 'WNIOSEK')}-{uuid.uuid4().hex[:8].upper()}"

    deadline_21: str | None = None
    if req.child_birth_date:
        try:
            birth = date.fromisoformat(req.child_birth_date)
            deadline_21 = (birth + timedelta(days=p.combined_application_deadline_days)).isoformat()
        except ValueError:
            deadline_21 = None

    variant_desc = (
        f"{p.combined_21_days_rate*100:.1f}% podstawy wymiaru przez cały okres (art. 30a i art. 31 ust. 3 ustawy zasiłkowej)"
        if req.payment_variant == PaymentVariant.COMBINED_81_5
        else f"{p.maternity_rate_standard*100:.0f}% za urlop macierzyński oraz {p.parental_rate_standard*100:.0f}% za urlop rodzicielski (art. 31 ust. 1–2 ustawy zasiłkowej)"
    )

    period_txt = f"od dnia {req.leave_start_date or '............'} do dnia {req.leave_end_date or '............'}"
    birth_txt = req.child_birth_date or "............"

    if req.application_type == ApplicationType.LEAVE_EMPLOYER:
        title = "WNIOSEK O UDZIELENIE URLOPU MACIERZYŃSKIEGO I URLOPU RODZICIELSKIEGO"
        legal_basis = "art. 180 § 1, art. 182¹ᵃ oraz art. 182¹ᵈ Kodeksu pracy; Rozporządzenie MRPiPS z dnia 11 marca 2025 r. (Dz.U. z 2025 r. poz. 322)"
        body = (
            f"Na podstawie {legal_basis} zwracam się z wnioskiem o udzielenie mi urlopu macierzyńskiego oraz bezpośrednio po nim urlopu rodzicielskiego "
            f"z tytułu urodzenia dziecka w dniu {birth_txt}, w okresie {period_txt} "
            f"(planowana liczba części urlopu rodzicielskiego: {req.leave_parts_count or 1}, maksymalnie {p.parental_max_parts}).\n\n"
            f"Jednocześnie wnioskuję o wypłacanie zasiłku macierzyńskiego w wariancie: {variant_desc}."
        )
        attachments = [
            "1. Odpis skrócony aktu urodzenia dziecka (kopia).",
            "2. Oświadczenie o braku zamiaru korzystania przez drugiego z rodziców z urlopu rodzicielskiego w tym samym okresie (jeśli dotyczy).",
        ]
    elif req.application_type == ApplicationType.LEAVE_SUPPLEMENTARY:
        title = "WNIOSEK O UDZIELENIE UZUPEŁNIAJĄCEGO URLOPU MACIERZYŃSKIEGO"
        legal_basis = "art. 180² Kodeksu pracy; Rozporządzenie MRPiPS z dnia 11 marca 2025 r. (Dz.U. z 2025 r. poz. 322)"
        body = (
            f"Na podstawie {legal_basis} wnoszę o udzielenie uzupełniającego urlopu macierzyńskiego bezpośrednio po zakończeniu urlopu macierzyńskiego, "
            f"w okresie {period_txt}, w związku z pobytem dziecka (ur. {birth_txt}) w szpitalu "
            f"w okresie od {req.hospitalization_from or '............'} do {req.hospitalization_to or '............'}.\n\n"
            "Urlop jest udzielany jednorazowo i płatny w wysokości 100% podstawy wymiaru zasiłku."
        )
        attachments = [
            "1. Zaświadczenie wydane przez szpital zawierające informacje o tygodniu ciąży, masie urodzeniowej oraz okresie pobytu dziecka w szpitalu.",
            "2. Oświadczenie o braku zamiaru korzystania z uzupełniającego urlopu macierzyńskiego przez drugiego rodzica.",
        ]
    elif req.application_type == ApplicationType.LEAVE_WORK_COMBINATION:
        title = "WNIOSEK O ŁĄCZENIE URLOPU RODZICIELSKIEGO Z WYKONYWANIEM PRACY"
        legal_basis = "art. 182¹ᵉ oraz art. 182¹ᶠ Kodeksu pracy; § 19 Rozporządzenia MRPiPS z dnia 11 marca 2025 r. (Dz.U. z 2025 r. poz. 322)"
        body = (
            f"Na podstawie {legal_basis} wnoszę o umożliwienie łączenia korzystania z urlopu rodzicielskiego (na dziecko ur. {birth_txt}) "
            f"z wykonywaniem pracy u pracodawcy udzielającego urlopu w wymiarze {req.work_fte_fraction or 0.5} etatu (nie wyższym niż 1/2 pełnego wymiaru czasu pracy), "
            f"w okresie {period_txt}.\n\n"
            "Wnoszę o proporcjonalne wydłużenie wymiaru urlopu rodzicielskiego zgodnie z art. 182¹ᶠ Kodeksu pracy oraz odpowiednie ustalenie wysokości zasiłku macierzyńskiego."
        )
        attachments = [
            "1. Propozycja harmonogramu czasu pracy w okresie łączenia urlopu z pracą (opcjonalnie).",
        ]
    elif req.application_type == ApplicationType.LEAVE_RESIGNATION:
        title = "WNIOSEK W SPRAWIE REZYGNACJI Z POZOSTAŁEJ CZĘŚCI URLOPU MACIERZYŃSKIEGO"
        legal_basis = "art. 180 § 4 Kodeksu pracy; § 3 Rozporządzenia MRPiPS z dnia 11 marca 2025 r. (Dz.U. z 2025 r. poz. 322)"
        body = (
            f"Na podstawie {legal_basis} informuję o rezygnacji z pozostałej części urlopu macierzyńskiego (po wykorzystaniu po porodzie co najmniej 14 tygodni) "
            f"i deklaruję powrót do pracy z dniem {req.resignation_date or '............'}.\n\n"
            "Pozostałą część urlopu macierzyńskiego przejmie ojciec wychowujący dziecko bezpośrednio po zakończeniu mojego urlopu."
        )
        attachments = [
            "1. Kopia wniosku pracownika – ojca wychowującego dziecko o udzielenie pozostałej części urlopu macierzyńskiego (albo kopia oświadczenia ubezpieczonego ojca o przerwaniu działalności zarobkowej).",
        ]
    elif req.application_type == ApplicationType.ZAM_ZUS:
        title = "WNIOSEK O ZASIŁEK MACIERZYŃSKI — FORMULARZ ZUS ZAM"
        legal_basis = "art. 29–31 ustawy z dnia 25 czerwca 1999 r. o świadczeniach pieniężnych z ubezpieczenia społecznego w razie choroby i macierzyństwa (Dz.U. z 2026 r. poz. 854)"
        body = (
            f"Na podstawie {legal_basis} wnoszę o ustalenie prawa i wypłatę zasiłku macierzyńskiego za okres {period_txt} "
            f"z tytułu urodzenia dziecka w dniu {birth_txt}.\n\n"
            f"Wybrany wariant wypłaty: {variant_desc}.\n"
            "Uwaga: Od 24 października 2026 r. formularz ZAM zastępuje dotychczasowe formularze ZUR i ZAO i jest składany elektronicznie przez PUE/eZUS lub w placówce ZUS."
        )
        attachments = [
            "1. Odpis skrócony aktu urodzenia dziecka.",
            "2. Zaświadczenie płatnika składek Z-3 (pracownik) lub Z-3a (zleceniobiorca) — jeśli płatnik nie jest uprawniony do wypłaty zasiłków.",
            "3. Zaświadczenie 'Za życiem' lub zaświadczenie szpitalne — jeśli dotyczy.",
        ]
    else:
        title = "WNIOSEK O WYDANIE ODPISU AKTU URODZENIA (REJESTR STANU CYWILNEGO)"
        legal_basis = "art. 44–45 ustawy z dnia 28 listopada 2014 r. – Prawo o aktach stanu cywilnego"
        body = (
            f"Na podstawie {legal_basis} wnoszę o wydanie odpisu skróconego aktu urodzenia dziecka urodzonego w dniu {birth_txt}, "
            "niezbędnego do przedłożenia pracodawcy / Zakładowi Ubezpieczeń Społecznych w celu ustalenia prawa do urlopu i zasiłku macierzyńskiego.\n\n"
            "Wniosek o odpis w sprawach ubezpieczeń społecznych jest zwolniony z opłaty skarbowej (art. 2 ust. 1 pkt 1 lit. b ustawy o opłacie skarbowej)."
        )
        attachments = [
            "1. Dokument tożsamości (lub podpis Profilem Zaufanym / e-Dowodem przez gov.pl).",
        ]

    lines = [
        f"                                                  Miejscowość, dnia {today_str}",
        "",
        "WNIOSKODAWCA:",
        f"  {req.applicant_name}",
        f"  PESEL: {req.pesel_masked}",
        "",
        "ADRESAT:",
        f"  {req.recipient}",
        "",
        title,
        "",
        body,
    ]
    if deadline_21 and req.application_type in (ApplicationType.LEAVE_EMPLOYER, ApplicationType.ZAM_ZUS):
        lines.extend(["", f"Termin 21 dni po porodzie na wniosek/deklarację o 81,5%: {deadline_21}."])
    if req.notes:
        lines.extend(["", f"Informacje dodatkowe: {req.notes}"])
    lines.extend(
        [
            "",
            "ZAŁĄCZNIKI:",
            *[f"  {a}" for a in attachments],
            "",
            f"Nr roboczy dokumentu: {ref}",
            "",
            "                                                  ................................................",
            "                                                     (czytelny podpis wnioskodawcy)",
        ]
    )

    return ApplicationSubmissionResponse(
        reference_number=ref,
        application_type=req.application_type,
        recipient=req.recipient,
        submitted_at=now_iso,
        deadline_21_days=deadline_21,
        status="Wygenerowano wzór dokumentu zgodny z przepisami 2025/2026",
        summary=f"Przygotowano {title} dla {req.applicant_name} (adresat: {req.recipient}).",
        generated_document_text="\n".join(lines),
    )


def generate_application_pdf(
    req: ApplicationSubmissionRequest,
    params: LegalParameters | None = None,
) -> tuple[str, bytes]:
    """Generuje gotowy do druku plik PDF (A4) z pełną obsługą polskich znaków (DejaVuSans)."""
    from pathlib import Path
    from fpdf import FPDF

    doc_data = simulate_application_submission(req, params)
    pdf = FPDF(format="A4")
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    regular_font = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    bold_font = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    if regular_font.exists() and bold_font.exists():
        pdf.add_font("DejaVu", "", str(regular_font))
        pdf.add_font("DejaVu", "B", str(bold_font))
        font_family = "DejaVu"
    else:
        font_family = "Helvetica"

    text_lines = doc_data.generated_document_text.splitlines()
    for line in text_lines:
        stripped = line.strip()
        pdf.set_x(pdf.l_margin)
        if stripped.startswith("WNIOSEK "):
            pdf.ln(3)
            pdf.set_font(font_family, "B", 12)
            pdf.multi_cell(pdf.epw, 7, stripped, align="C", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)
        elif stripped in ("WNIOSKODAWCA:", "ADRESAT:", "ZAŁĄCZNIKI:"):
            pdf.set_font(font_family, "B", 10)
            pdf.multi_cell(pdf.epw, 6, stripped, new_x="LMARGIN", new_y="NEXT")
        elif stripped.startswith("Miejscowość, dnia"):
            pdf.set_font(font_family, "", 10)
            pdf.multi_cell(pdf.epw, 6, stripped, align="R", new_x="LMARGIN", new_y="NEXT")
        elif stripped.startswith("....") or stripped.startswith("(czytelny podpis"):
            pdf.set_font(font_family, "", 9)
            pdf.multi_cell(pdf.epw, 5.5, stripped, align="R", new_x="LMARGIN", new_y="NEXT")
        elif not stripped:
            pdf.ln(3)
        else:
            pdf.set_font(font_family, "", 10)
            pdf.multi_cell(pdf.epw, 5.8, stripped, new_x="LMARGIN", new_y="NEXT")

    return doc_data.reference_number, bytes(pdf.output())

